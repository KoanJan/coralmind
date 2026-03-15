from __future__ import annotations

import json
import logging
from typing import cast

from pydantic import BaseModel, Field

from .exceptions import PlanValidationError
from .llm import (
    LLMConfig,
    LLMResponse,
    TokenCost,
    as_user_messages,
    build_assistant_message,
    build_user_message,
    call_llm,
)
from .model import (
    InputFieldSourceType,
    Language,
    OutputConstraints,
    OutputFormat,
    OutputType,
    Plan,
    PlanAdvice,
    PlanAdviceType,
    Task,
    TaskTemplate,
)
from .output_format import json_schema_to_pydantic
from .prompts import (
    PromptName,
    PromptTemplateName,
    build_prompt,
    build_score_messages,
    build_validation_messages,
    get_prompt,
)
from .storage import PlanStorage
from .strategy.advising import BasePlanStrategy, PlanAdviceAction, PlanRecord

__all__ = ["Plan", "PlanAdvice", "PlanAdviceType", "PlanAdvisor", "Planner",
           "Executor", "Validator", "ValidateResult", "Evaluator", "OutputFormatter"]


class Planner:
    """
    Plan Maker
    """

    logger = logging.getLogger(__name__)

    def __init__(self, llm: LLMConfig, formatter_llm: LLMConfig):
        self.llm = llm
        self.formatter_llm = formatter_llm

    def make_plan(self, task_template: TaskTemplate, advice: PlanAdvice | None) -> LLMResponse[Plan]:
        """
        Generate a plan

        Based on whether there is historical advice, decide how to generate the plan:
        - If advice exists and type is USE, directly use the old plan
        - If advice exists and type is BASE_ON, optimize based on the old plan
        - If no advice, generate plan from scratch

        The generated plan will be structurally validated.

        Args:
            task_template: Task template containing material names and requirements
            advice: Optional plan advice containing historical good plans

        Returns:
            LLMResponse[Plan]: Response containing generated plan and token cost

        Raises:
            PlanValidationError: If the generated plan does not meet structural specifications
        """
        self.logger.debug(f"Making plan: advice={'None' if advice is None else advice.type}")

        if advice:
            response = self._generate_plan_with_advice(task_template, advice)
        else:
            response = self._generate_plan_without_advice(task_template)

        self.logger.debug("Plan generated, validating structure...")
        self._validate_plan_structure(task_template, response.content)
        self.logger.debug("Plan structure validation passed")

        return response

    def _generate_plan_with_advice(self, task_template: TaskTemplate, advice: PlanAdvice) -> LLMResponse[Plan]:
        if advice.type == PlanAdviceType.USE:
            return LLMResponse(
                content=advice.old_plan,
                token_cost=TokenCost(prompt=0, completion=0, total=0),
                model="",
            )

        messages = self._build_messages_for_generating_plan(task_template)
        old_plan = advice.old_plan.model_dump_json(indent=2, ensure_ascii=False)
        old_plan_message = build_prompt(PromptTemplateName.OLD_PLAN_ATTACHMENT, language=task_template.language, old_plan=old_plan)
        messages.append(old_plan_message)

        result = call_llm(self.llm, as_user_messages(messages), Plan, self.formatter_llm)
        return cast(LLMResponse[Plan], result)

    def _generate_plan_without_advice(self, task_template: TaskTemplate) -> LLMResponse[Plan]:
        messages = self._build_messages_for_generating_plan(task_template)
        result = call_llm(self.llm, as_user_messages(messages), Plan, self.formatter_llm)
        return cast(LLMResponse[Plan], result)

    @staticmethod
    def _build_messages_for_generating_plan(task_template: TaskTemplate) -> list[str]:
        materials_names = "\n".join([f"- {name}" for name in task_template.material_names])

        output_format_section = ""
        if task_template.output_format is not None:
            output_format_section = build_prompt(
                PromptTemplateName.PLANNER_OUTPUT_FORMAT_SECTION,
                language=task_template.language,
                json_schema=task_template.output_format.json_schema
            )

        message = build_prompt(
            PromptTemplateName.PLANNER_MESSAGE_TEMPLATE,
            language=task_template.language,
            materials_names=materials_names,
            requirements=task_template.requirements,
            output_format_section=output_format_section,
            plan_standard=get_prompt(PromptName.PLAN_STANDARD, task_template.language),
            return_format_schema=json.dumps(Plan.model_json_schema(), indent=2, ensure_ascii=False)
        )
        return [message]

    @staticmethod
    def _validate_plan_structure(task_template: TaskTemplate, plan: Plan) -> None:
        """Validate plan structure

        Checks include:
        - Plan must contain at least one node
        - Last node must be final node and cannot have output fields
        - Node IDs cannot be duplicated
        - Non-final nodes must have output fields
        - Input dependencies must be valid (referenced materials and node outputs must exist)
        - All materials must be used in the plan

        Args:
            task_template: Task template
            plan: Execution plan to validate

        Raises:
            PlanValidationError: If plan does not meet specifications
        """
        if len(plan.nodes) == 0:
            raise PlanValidationError("Plan must contain at least 1 node")

        final_node = plan.nodes[-1]
        if not final_node.is_final_node:
            raise PlanValidationError("The final node must be marked as final node", node_id=final_node.id)

        node_indices = {node.id: i for i, node in enumerate(plan.nodes)}
        if len(node_indices) != len(plan.nodes):
            duplicate_ids = [node.id for node in plan.nodes if list(node_indices.keys()).count(node.id) > 1]
            raise PlanValidationError(f"Duplicate node_id found: {list(set(duplicate_ids))}")

        output_names_dict: dict[str, list[str]] = {}
        for node in plan.nodes:
            if node.output_constraints.output_type == OutputType.MODEL and node.output_constraints.fields is not None:
                output_names_dict[node.id] = list(node.output_constraints.fields.keys())
            else:
                output_names_dict[node.id] = []
        used_materials: set[str] = set()

        for i, node in enumerate(plan.nodes):
            for input_field in node.input_fields:
                if input_field.source_type == InputFieldSourceType.ORIGINAL_MATERIAL:
                    used_materials.add(input_field.material_name)
                    if input_field.material_name not in task_template.material_names:
                        raise PlanValidationError(
                            f"Material '{input_field.material_name}' not found in task template. "
                            f"Available materials: {task_template.material_names}",
                            node_id=node.id
                        )
                elif input_field.source_type == InputFieldSourceType.OUTPUT_OF_ANOTHER_NODE:
                    dep = input_field.output_of_another_node
                    if dep is None:
                        raise PlanValidationError("output_of_another_node is required", node_id=node.id)
                    dep_node_id = dep.node_id
                    dep_node_idx = node_indices.get(dep_node_id)
                    if dep_node_idx is None:
                        raise PlanValidationError(
                            f"Dependent node '{dep_node_id}' does not exist",
                            node_id=node.id
                        )
                    if dep_node_idx >= i:
                        raise PlanValidationError(
                            f"Dependent node '{dep_node_id}' must be executed before current node",
                            node_id=node.id
                        )
                    dep_output_name = dep.output_field_name
                    if dep_output_name not in output_names_dict[dep_node_id]:
                        raise PlanValidationError(
                            f"Output '{dep_output_name}' not found in dependent node '{dep_node_id}'. "
                            f"Available outputs: {output_names_dict[dep_node_id]}",
                            node_id=node.id
                        )

        missing = set(task_template.material_names) - used_materials
        if missing:
            raise PlanValidationError(f"Plan does not use the following materials: {', '.join(missing)}")


class Executor:
    """
    Step Executor
    """

    logger = logging.getLogger(__name__)

    def __init__(self, llm: LLMConfig, formatter_llm: LLMConfig):
        self.llm = llm
        self.formatter_llm = formatter_llm

    def execute(
            self,
            materials: dict[str, str],
            requirements: str,
            output_constraints: OutputConstraints,
            language: Language | None = None,
            last_output: str | BaseModel | None = None,
            reject_reason: str | None = None,
            relevant_requirements: str | None = None
    ) -> LLMResponse[str] | LLMResponse[BaseModel]:
        """
        Execute task

        Args:
            materials: Input material dictionary, key is material name, value is material content
            requirements: Task requirement description
            output_constraints: Output constraints for validation (format and semantic validation)
            language: Language for prompts
            last_output: Output from last execution (for redo scenario)
            reject_reason: Reason for rejection last time (for redo scenario)
            relevant_requirements: Relevant requirements for context (from requirement tree or global fallback)

        Returns:
            LLMResponse[str]: When output_constraints.output_type is TEXT
            LLMResponse[BaseModel]: When output_constraints.output_type is MODEL
        """
        if language is None:
            language = Language.EN

        output_model = output_constraints.get_model_class()

        self.logger.debug(f"Executing: materials={list(materials.keys())}, output_type={'model' if output_model else 'text'}, is_retry={reject_reason is not None}")

        m_names: list[str] = []
        messages: list[str] = []

        if relevant_requirements:
            relevant_context = build_prompt(
                PromptTemplateName.RELEVANT_REQUIREMENTS_CONTEXT,
                language=language,
                relevant_requirements=relevant_requirements
            )
            messages.append(relevant_context)

        for name, content in materials.items():
            m_names.append(name)
            messages.append(f"# {name}\n\n{content}\n")
        m_names_text = ", ".join(m_names)
        requirements = build_prompt(PromptTemplateName.EXECUTOR_REQUIREMENTS, language=language,
                                    material_names=m_names_text, requirements=requirements)
        messages.append(requirements)
        if output_model and output_constraints.fields is not None:
            output_name_descriptions = [f"`{k}` (definition: {v})" for k, v in output_constraints.fields.items()]
            output_name_descriptions_text = ", ".join(output_name_descriptions)
            output_format_requirement = build_prompt(
                PromptTemplateName.OUTPUT_FORMAT_WITH_NAMES,
                language=language,
                output_name_descriptions=output_name_descriptions_text
            )
            messages.append(output_format_requirement)
        else:
            messages.append(build_prompt(PromptTemplateName.OUTPUT_FORMAT_WITHOUT_NAMES, language=language))

        llm_messages = as_user_messages(messages)

        if reject_reason and last_output:
            if isinstance(last_output, str):
                llm_messages.append(build_assistant_message(last_output))
            else:
                llm_messages.append(build_assistant_message(last_output.model_dump_json()))
            llm_messages.append(build_user_message(reject_reason))

        if output_model:
            result = call_llm(self.llm, llm_messages, output_model, self.formatter_llm)
            return result

        str_result = call_llm(self.llm, llm_messages, str, self.formatter_llm)
        return str_result


class ValidateResult(BaseModel):
    """
    Validation Result
    """
    passed: bool = Field(default=False, description="Whether passed")
    reason: str = Field(default="", description="Reason for failure")


class Validator:
    """
    Execution Result Validator
    """

    def __init__(self, llm: LLMConfig, formatter_llm: LLMConfig):
        self.llm = llm
        self.formatter_llm = formatter_llm

    def validate_execution(
            self,
            materials: dict[str, str],
            requirements: str,
            output_constraints: OutputConstraints,
            output: str | BaseModel,
            language: Language | None = None,
            relevant_requirements: str | None = None
    ) -> LLMResponse[ValidateResult]:
        """
        Validate execution result

        Validation flow:
        1. First perform quick rule validation (check output type)
        2. If quick validation passes, call LLM for deep semantic validation

        Args:
            materials: Input material dictionary
            requirements: Task requirements
            output_constraints: Output constraints for validation
            output: Actual output result
            language: Language for prompts
            relevant_requirements: Relevant requirements for alignment check (from requirement tree or global fallback)

        Returns:
            LLMResponse[ValidateResult]: Response containing validation result and token cost
        """
        if language is None:
            language = Language.EN

        quick_check_result = self._quick_check_output_type(output_constraints, output)
        if quick_check_result:
            return LLMResponse(
                content=quick_check_result,
                token_cost=TokenCost(prompt=0, completion=0, total=0),
                model="",
            )

        is_model_output = output_constraints.output_type == OutputType.MODEL
        output_names = output_constraints.fields if is_model_output else None
        output_what = output_constraints.content_spec

        messages = build_validation_messages(language, materials, requirements, output, output_names, output_what, relevant_requirements)

        result = call_llm(self.llm, as_user_messages(messages), ValidateResult, self.formatter_llm)
        return cast(LLMResponse[ValidateResult], result)

    @staticmethod
    def _quick_check_output_type(
            output_constraints: OutputConstraints,
            output: str | BaseModel
    ) -> ValidateResult | None:
        """Quick validation of output type

        Returns:
            ValidateResult: If validation fails, return error result
            None: If quick validation passes, return None
                  In this case, need to call LLM for deep validation
        """
        is_model_output = output_constraints.output_type == OutputType.MODEL

        if not is_model_output:
            if isinstance(output, str):
                return None
            else:
                return ValidateResult(passed=False, reason="Expected text output, got model")

        if isinstance(output, str):
            return ValidateResult(passed=False, reason="Expected model output, got text")

        return None


class EvaluationScore(BaseModel):
    """
    Evaluation Score

    Scored by LLM on task execution results, range 0-10.
    """
    score: int = Field(description="Integer score from 0-10", ge=0, le=10)
    reason: str = Field(description="Reason for the score")


class Evaluator:
    """
    Evaluator
    """

    def __init__(self, llm: LLMConfig, formatter_llm: LLMConfig):
        self.llm = llm
        self.formatter_llm = formatter_llm

    def score(self, task: Task, output: str) -> LLMResponse[EvaluationScore]:
        """
        Score task output

        Args:
            task: Task information containing materials and requirements
            output: Actual output of task execution

        Returns:
            LLMResponse[EvaluationScore]: Response containing score and token cost
        """
        messages = build_score_messages(task, output)
        result = call_llm(self.llm, as_user_messages(messages), EvaluationScore, self.formatter_llm)
        return cast(LLMResponse[EvaluationScore], result)


class PlanAdvisor:
    """
    Plan Advisor
    """

    @staticmethod
    def make_advice(task_template_id: int, strategy: BasePlanStrategy) -> PlanAdvice | None:
        """
        Generate advice about execution plan

        Args:
            task_template_id: Task template ID
            strategy: Plan selection strategy

        Returns:
            PlanAdvice: If a suitable old plan is found, return advice
            None: If no historical records or no suitable plan, return None
        """

        ro_list = PlanStorage.get_by_task_template_id(task_template_id)
        if len(ro_list) == 0:
            return None

        records = [PlanRecord(id=ro.id, total_score=ro.total_score, exec_times=ro.exec_times) for ro in ro_list]
        strategy_result = strategy.decide(records)

        if not strategy_result:
            return None
        the_ro = next(ro for ro in ro_list if ro.id == strategy_result.old_plan_id)
        old_plan = Plan.model_validate_json(the_ro.plan_json)
        if strategy_result.action == PlanAdviceAction.USE:
            return PlanAdvice(
                type=PlanAdviceType.USE,
                old_plan=old_plan,
            )
        else:
            return PlanAdvice(
                type=PlanAdviceType.BASE_ON,
                old_plan=old_plan,
            )


class OutputFormatter:
    """Final Output Formatter"""

    def __init__(self, llm: LLMConfig):
        self.llm = llm

    def format_output(
        self,
        requirements: str,
        output: str,
        output_format: OutputFormat | None = None,
        language: Language | None = None
    ) -> str:
        """
        Format output according to optional format specification.

        Args:
            requirements: Task output requirements (unused, kept for API compatibility)
            output: Raw output from orchestration
            output_format: Optional format specification (e.g., JSON schema)
            language: Language for prompts

        Returns:
            Formatted output string, or original output if no format specified
        """
        if language is None:
            language = Language.EN

        if output_format is not None:
            return self._format_to_schema(output, output_format, language)
        return output

    def _format_to_schema(self, output: str, output_format: OutputFormat, language: Language) -> str:
        """Format output to match the specified JSON schema"""
        output_msg = f"# Original Output\n\n```\n{output}\n```\n"
        prompt = build_prompt(
            PromptTemplateName.FORMAT_TO_SCHEMA,
            language=language,
            json_schema=output_format.json_schema
        )
        dynamic_model = json_schema_to_pydantic(output_format.json_schema)
        result = call_llm(self.llm, as_user_messages([output_msg, prompt]), dynamic_model)
        return result.content.model_dump_json(exclude_none=True)
