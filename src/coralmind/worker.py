import json
from typing import Any, cast

from pydantic import BaseModel, Field

from .exceptions import PlanValidationError
from .llm import LLMConfig, as_user_messages, build_assistant_message, build_user_message, call_llm
from .model import InputFieldSourceType, Plan, PlanAdvice, PlanAdviceType, Task, TaskTemplate
from .prompts import EVALUATION_STANDARD, PLAN_STANDARD
from .storage import PlanStorage
from .strategy.advising import BasePlanStrategy, PlanAdviceAction, PlanRecord

__all__ = ["Plan", "PlanAdvice", "PlanAdviceType", "PlanAdvisor", "Planner",
           "Executor", "Validator", "ValidateResult", "Evaluator", "OutputFormater"]


class Planner:
    """
    Plan Maker
    """

    def __init__(self, llm: LLMConfig, formatter_llm: LLMConfig):
        self.llm = llm
        self.formatter_llm = formatter_llm

    def make_plan(self, task_template: TaskTemplate, advice: PlanAdvice | None) -> Plan:
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
            Plan: Generated execution plan

        Raises:
            PlanValidationError: If the generated plan does not meet specifications
        """
        if advice:
            plan = self._generate_plan_with_advice(task_template, advice)
        else:
            plan = self._generate_plan_without_advice(task_template)
        self._validate_plan(task_template, plan)
        return plan

    def _generate_plan_with_advice(self, task_template: TaskTemplate, advice: PlanAdvice) -> Plan:
        if advice.type == PlanAdviceType.USE:
            return advice.old_plan

        messages = self._build_messages_for_generating_plan(task_template)
        old_plan = advice.old_plan.model_dump_json(indent=2, ensure_ascii=False)
        old_plan_message = f"# Attachment: Example of a good plan from past similar tasks\n\n```json\n{old_plan}\n```"
        messages.append(old_plan_message)

        result = call_llm(self.llm, as_user_messages(messages), Plan, self.formatter_llm)
        return cast(Plan, result)

    def _generate_plan_without_advice(self, task_template: TaskTemplate) -> Plan:
        messages = self._build_messages_for_generating_plan(task_template)
        result = call_llm(self.llm, as_user_messages(messages), Plan, self.formatter_llm)
        return cast(Plan, result)

    @staticmethod
    def _build_messages_for_generating_plan(task_template: TaskTemplate) -> list[str]:
        meterials_names = "\n".join([f"- {name}" for name in task_template.material_names])

        message = f"""
# Task Description

1. User's Original Requirements
```text
{task_template.requirements}
```

2. List of Material Names Provided by User
{meterials_names}


3. Your Task
Do not directly complete the user's original requirements. Instead, create a detailed execution plan for them.

4. Execution Plan Standard
```text
{PLAN_STANDARD}
```

5. Return Format: JSON (strictly follow the JSONSchema below)
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

        node_indicies = {node.id: i for i, node in enumerate(plan.nodes)}
        if len(node_indicies) != len(plan.nodes):
            duplicate_ids = [node.id for node in plan.nodes if list(node_indicies.keys()).count(node.id) > 1]
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
                    dep_node_idx = node_indicies.get(dep_node_id)
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
    ) -> str | dict[str, str]:
        """
        Execute task

        Args:
            materials: Input material dictionary, key is material name, value is material content
            requirements: Task requirement description
            output_names: Expected output field names and their definitions, None means return string result directly
            last_output: Output from last execution (for redo scenario)
            reject_reason: Reason for rejection last time (for redo scenario)

        Returns:
            str: When output_names is None, return string result
            dict[str, str]: When output_names is not None, return dictionary with specified fields
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
            output_format_requirement = f"Return a JSON dictionary (all keys and values must be string type) containing the following fields: {output_name_descriptions_text}."
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
            return dict(result)

        str_result = call_llm(self.llm, llm_messages, str, self.formatter_llm)
        return str(str_result)


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
    ) -> ValidateResult:
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
            ValidateResult: Validation result, including whether passed and reason for failure
        """

        quick_check_result = self._quick_check_output_type(output_names, output)
        if quick_check_result:
            return quick_check_result

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
        return cast(ValidateResult, result)

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

    def score(self, task_template_id: int, plan: Plan, task: Task, output: str) -> int:
        """
        Score

        Args:
            task_template_id: Task template ID
            plan: Execution plan
            task: Task information
            output: Execution output result

        Returns:
            int: Score result (integer from 0-10)
        """
        plan_json = plan.model_dump_json()

        score_result = self._evaluate(task, output)
        score = score_result.score

        old_plans = PlanStorage.get_by_task_template_id(task_template_id)
        for old_plan in old_plans:
            if old_plan.plan_json == plan_json:
                PlanStorage.update_score(old_plan.id, score)
                return score
        PlanStorage.upsert(task_template_id, plan_json, score)
        return score

    def _evaluate(self, task: Task, output: str) -> EvaluationScore:
        """
        Call LLM to evaluate task results

        Evaluation flow:
        1. Build prompt containing materials, task requirements, actual output and evaluation standard
        2. Call LLM for scoring
        3. Return structured evaluation result

        Args:
            task: Task information containing materials and requirements
            output: Actual output of task execution

        Returns:
            EvaluationScore: Contains score (0-10) and reason for the score
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
        return cast(EvaluationScore, result)


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


class OutputFormater:
    """Final Output Formatter"""

    class FormatResult(BaseModel):
        need_reformat: bool = Field(description="Does the original output need adjustment?")
        new_content: str | None = Field(default=None, description="Adjusted complete output content")

    def __init__(self, llm: LLMConfig):
        self.llm = llm

    def format_output(self, requirements: str, output: str) -> str:
        """Identify the expected output subject from requirements and adjust the output accordingly"""
        req_msg = f"# Original Task Output Requirements\n\n{requirements}"
        output_msg = f"# Original Task Output Result\n\n```text\n{output}\n```\n"
        prompt = f"""
The above are "Original Task Output Requirements" and "Original Task Output Result" respectively.
# Your Task
Identify the expected output format from "Original Task Output Requirements" and ensure "Original Task Output Result" does not contain any non-expected format output or irrelevant content. If it does, adjust it.

# Return Format
Strictly follow the JSONSchema below and return a JSON directly.
```
{self.FormatResult.model_json_schema()}
```
"""
        result = call_llm(self.llm, as_user_messages([req_msg, output_msg, prompt]), self.FormatResult)
        format_result = cast(OutputFormater.FormatResult, result)
        if format_result.need_reformat and format_result.new_content:
            return format_result.new_content
        return output
