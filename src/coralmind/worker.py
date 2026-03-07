import json
import logging
from typing import Any, cast

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
from .model import InputFieldSourceType, OutputFormat, Plan, PlanAdvice, PlanAdviceType, Task, TaskTemplate
from .output_format import json_schema_to_pydantic
from .prompts import EVALUATION_STANDARD, PLAN_STANDARD
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

        The generated plan will be validated.

        Args:
            task_template: Task template containing material names and requirements
            advice: Optional plan advice containing historical good plans

        Returns:
            LLMResponse[Plan]: Response containing generated plan and token cost

        Raises:
            PlanValidationError: If the generated plan does not meet specifications
        """
        if advice:
            response = self._generate_plan_with_advice(task_template, advice)
        else:
            response = self._generate_plan_without_advice(task_template)
        self._validate_plan(task_template, response.content)
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
        old_plan_message = f"# Attachment: Example of a good plan from past similar tasks\n\n```json\n{old_plan}\n```"
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
            output_format_section = f"""
3. Final Output Format (JSON Schema)
The final output will be formatted to match this schema after all nodes complete:
```json
{task_template.output_format.json_schema}
```

**CRITICAL CONSTRAINT**: This schema is for the FINAL output only, NOT for intermediate nodes.
- Each intermediate node must output `dict[str, str]` where values are plain strings
- Do NOT create nodes that output JSON arrays or nested objects
- The final node should output a single string containing all content
- JSON formatting happens AFTER execution, not during
"""

        message = f"""
# Task Input

1. Materials
{materials_names}

2. Requirements
```text
{task_template.requirements}
```
{output_format_section}
# Your Task

Create a detailed execution plan based on the Task Input above. Do not directly complete the user's requirements.

# Execution Plan Standard
```text
{PLAN_STANDARD}
```

# Return Format (JSON Schema)
```json
{json.dumps(Plan.model_json_schema(), indent=2, ensure_ascii=False)}
```
"""
        return [message]

    @staticmethod
    def _validate_plan(task_template: TaskTemplate, plan: Plan) -> None:
        """Validate plan effectiveness

        Checks include:
        - Plan must contain at least one node
        - Last node must be final node and cannot have output fields
        - Node IDs cannot be duplicated
        - Non-final nodes must have output fields
        - Input dependencies must be valid (referenced materials and node outputs must exist)

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
        if final_node.output_names and len(final_node.output_names) > 0:
            raise PlanValidationError("The final node cannot have output_names", node_id=final_node.id)

        node_indices = {node.id: i for i, node in enumerate(plan.nodes)}
        if len(node_indices) != len(plan.nodes):
            duplicate_ids = [node.id for node in plan.nodes if list(node_indices.keys()).count(node.id) > 1]
            raise PlanValidationError(f"Duplicate node_id found: {list(set(duplicate_ids))}")

        output_names_dict: dict[str, list[str]] = {
            node.id: list(node.output_names.keys()) if node.output_names else []
            for node in plan.nodes
        }

        for i, node in enumerate(plan.nodes):

            if i < len(plan.nodes) - 1 and (not node.output_names or len(node.output_names) == 0):
                raise PlanValidationError("Non-final node must have at least 1 output name", node_id=node.id)

            for input_field in node.input_fields:
                if input_field.source_type == InputFieldSourceType.ORIGINAL_MATERIAL:
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
            output_names: dict[str, str] | None,
            last_output: str | dict[str, str] | None = None,
            reject_reason: str | None = None
    ) -> LLMResponse[str] | LLMResponse[dict[str, str]]:
        """
        Execute task

        Args:
            materials: Input material dictionary, key is material name, value is material content
            requirements: Task requirement description
            output_names: Expected output field names and their definitions, None means return string result directly
            last_output: Output from last execution (for redo scenario)
            reject_reason: Reason for rejection last time (for redo scenario)

        Returns:
            LLMResponse[str]: When output_names is None
            LLMResponse[dict[str, str]]: When output_names is not None
        """

        m_names: list[str] = []
        messages: list[str] = []
        for name, content in materials.items():
            m_names.append(name)
            messages.append(content)
        m_names_text = ", ".join(m_names)
        requirements = f"The above are {m_names_text} respectively.\n\n{requirements}"
        messages.append(requirements)
        if output_names:
            output_name_descriptions = [f"`{k}` (definition: {v})" for k, v in output_names.items()]
            output_name_descriptions_text = ", ".join(output_name_descriptions)
            output_format_requirement = f"""Return a JSON dictionary containing the following fields: {output_name_descriptions_text}.

**CRITICAL**: All values in the dictionary MUST be strings (str type), NOT arrays, objects, or nested structures.
- If you need to return multiple items, format them as a single string (e.g., newline-separated or JSON stringified)
- Example of CORRECT format: {{"items": "item1\\nitem2\\nitem3"}}
- Example of WRONG format: {{"items": ["item1", "item2", "item3"]}}"""
            messages.append(output_format_requirement)
        else:
            output_format_requirement = "Return the final result directly. Do not include any content that is not part of the deliverable itself."
            messages.append(output_format_requirement)

        llm_messages = as_user_messages(messages)

        if reject_reason and last_output:
            if isinstance(last_output, str):
                llm_messages.append(build_assistant_message(last_output))
            else:
                llm_messages.append(build_assistant_message(json.dumps(last_output)))
            llm_messages.append(build_user_message(reject_reason))

        if output_names:
            result = call_llm(self.llm, llm_messages, dict, self.formatter_llm)
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

    def validate(
            self,
            materials: dict[str, str],
            requirements: str,
            output_names: dict[str, str],
            output: str | dict[str, str]
    ) -> LLMResponse[ValidateResult]:
        """
        Execute validation

        Validation flow:
        1. First perform quick rule validation (check output type and field completeness)
        2. If quick validation passes, call LLM for deep semantic validation

        Args:
            materials: Input material dictionary
            requirements: Task requirements
            output_names: Expected output field definitions
            output: Actual output result

        Returns:
            LLMResponse[ValidateResult]: Response containing validation result and token cost
        """

        quick_check_result = self._quick_check_output_type(output_names, output)
        if quick_check_result:
            return LLMResponse(
                content=quick_check_result,
                token_cost=TokenCost(prompt=0, completion=0, total=0),
                model="",
            )

        messages: list[str] = []

        for name, content in materials.items():
            messages.append(f"# {name}\n\n{content}")

        if isinstance(output, str):
            output_text = output
            output_names_text = ""
        else:
            output_name_descriptions = [f"- `{k}`: {v}" for k, v in output_names.items()]
            output_names_text = "\n".join(output_name_descriptions)
            output_names_text = f"# Expected Output Fields\n\n{output_names_text}\n"
            output_text = json.dumps(output, indent=2, ensure_ascii=False)

        validation_prompt = f"""# Task Requirements

{requirements}

# Expected Output Fields

{output_names_text}

# Actual Output

{output_text}

# Validation Task

Please validate whether the actual output meets the following conditions:
1. Does it contain all expected output fields?
2. Does each field's content match its definition?
3. Does the overall output meet the task requirements?

Return in JSON format:
{{"passed": true/false, "reason": "reason for failure (empty string if passed)"}}"""

        messages.append(validation_prompt)

        result = call_llm(self.llm, as_user_messages(messages), ValidateResult, self.formatter_llm)
        return cast(LLMResponse[ValidateResult], result)

    @staticmethod
    def _quick_check_output_type(
            output_names: dict[str, str],
            output: str | dict[str, Any]
    ) -> ValidateResult | None:
        """Quick validation of parameters

        Returns:
            ValidateResult: If validation fails, return error result
            None: If quick validation passes (including when output is str type), return None
                  In this case, need to call LLM for deep validation
        """
        if isinstance(output, str):
            return None

        for k, v in output.items():
            if not isinstance(v, str):
                return ValidateResult(passed=False,
                                      reason=f"All values in the returned JSON must be strings, but the value for \"{k}\" is not a string type")
        for output_name in output_names:
            if output_name not in output:
                return ValidateResult(passed=False, reason=f"Missing field \"{output_name}\"")
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
        messages: list[str] = []

        for material in task.materials:
            messages.append(f"# {material.name}\n\n{material.content}")

        messages.append(f"# Task Requirements\n\n{task.requirements}")

        messages.append(f"# Actual Output\n\n{output}")

        messages.append(f"# Evaluation Standard\n\n{EVALUATION_STANDARD}")

        messages.append("""# Return Format

Please return the evaluation result in the following JSON format:
```json
{
  "score": integer from 0-10,
  "reason": "detailed reason for the score"
}
```""")

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

    def format_output(self, requirements: str, output: str, output_format: OutputFormat | None = None) -> str:
        """
        Format output according to optional format specification.

        Args:
            requirements: Task output requirements (unused, kept for API compatibility)
            output: Raw output from orchestration
            output_format: Optional format specification (e.g., JSON schema)

        Returns:
            Formatted output string, or original output if no format specified
        """
        if output_format is not None:
            return self._format_to_schema(output, output_format)
        return output

    def _format_to_schema(self, output: str, output_format: OutputFormat) -> str:
        """Format output to match the specified JSON schema"""
        output_msg = f"# Original Output\n\n```\n{output}\n```\n"
        prompt = f"""
The above is the original output content.

# Your Task
Transform the original output into a valid JSON that strictly follows the JSONSchema below. Preserve all meaningful information from the original output.

# JSONSchema
```json
{output_format.json_schema}
```

# Return Format
Return ONLY the JSON object, without any markdown formatting, code blocks, or additional text.
"""
        dynamic_model = json_schema_to_pydantic(output_format.json_schema)
        result = call_llm(self.llm, as_user_messages([output_msg, prompt]), dynamic_model)
        return result.content.model_dump_json(exclude_none=True)
