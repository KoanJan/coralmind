import logging

from .exceptions import ExecutionError, PlanValidationError
from .llm import LLMConfig
from .model import InputFieldSourceType, Material, Plan, Task, TaskTemplate
from .storage import TaskTemplateStorage, init_storage
from .strategy.advising import BasePlanStrategy, ThresholdStrategy
from .worker import Evaluator, Executor, OutputFormater, PlanAdvisor, Planner, Validator

logger = logging.getLogger(__name__)

__all__ = ["Agent"]

_DEFAULT_STRATEGY = ThresholdStrategy()


class Agent:
    """AI Agent"""

    def __init__(
            self,
            default_llm: LLMConfig,
            planner_llm: LLMConfig | None = None,
            executor_llm: LLMConfig | None = None,
            validator_llm: LLMConfig | None = None,
            advising_strategy: BasePlanStrategy | None = None,
            max_retry_times_per_node: int = 3,
    ):
        init_storage()

        self.advising_strategy = advising_strategy if advising_strategy else _DEFAULT_STRATEGY

        self.plan_advisor = PlanAdvisor()
        self.planner = Planner(
            llm=planner_llm if planner_llm else default_llm,
            formatter_llm=default_llm
        )
        self.executor = Executor(
            llm=executor_llm if executor_llm else default_llm,
            formatter_llm=default_llm
        )
        self.validator = Validator(
            llm=validator_llm if validator_llm else default_llm,
            formatter_llm=default_llm
        )
        self.evaluator = Evaluator(llm=default_llm, formatter_llm=default_llm)
        self.output_formater = OutputFormater(llm=default_llm)

        self.max_retry_times_per_node: int = max_retry_times_per_node

    @staticmethod
    def _get_task_template_id(task_template: TaskTemplate) -> int:
        """
        Get task template ID
        """

        task_template_json = task_template.model_dump_json()

        ro = TaskTemplateStorage.find_by_content(task_template_json)
        if ro:
            return ro.id

        return TaskTemplateStorage.insert(task_template_json)

    @staticmethod
    def _extract_task_template(task: Task) -> TaskTemplate:
        return TaskTemplate(
            material_names=[m.name for m in task.materials],
            requirements=task.requirements
        )

    def run(self, task: Task) -> str:
        """
        Execute task
        """
        task_template = self._extract_task_template(task)
        task_template_id = self._get_task_template_id(task_template)
        advice = self.plan_advisor.make_advice(task_template_id, self.advising_strategy)
        plan = self.planner.make_plan(task_template, advice)
        output = self._orchestrate(task.materials, plan)
        self.evaluator.score(task_template_id, plan, task, output)
        output = self.output_formater.format_output(task.requirements, output)
        return output

    def _orchestrate(self, materials: list[Material], plan: Plan) -> str:
        """
        Orchestrate the entire workflow according to the plan
        """
        materials_dict = {m.name: m.content for m in materials}
        intermediate_data: dict[str, str] = {}
        cur_output: str | dict[str, str] | None = None
        if (not plan.nodes) or len(plan.nodes) == 0:
            raise PlanValidationError("Plan contains 0 nodes")
        for plan_node in plan.nodes:
            input_materials: dict[str, str] = {}
            for input_field in plan_node.input_fields:
                if input_field.source_type == InputFieldSourceType.ORIGINAL_MATERIAL:
                    input_materials[input_field.material_name] = materials_dict[input_field.material_name]
                elif input_field.source_type == InputFieldSourceType.OUTPUT_OF_ANOTHER_NODE:
                    dep_node = input_field.output_of_another_node
                    if dep_node is None:
                        raise PlanValidationError("output_of_another_node is required", node_id=plan_node.id)
                    key = f"{dep_node.node_id}.{dep_node.output_field_name}"
                    input_materials[key] = intermediate_data[key]
            output_names = plan_node.output_names or {}
            for _ in range(self.max_retry_times_per_node):
                cur_output = self.executor.execute(input_materials, plan_node.requirements, output_names)
                if output_names:
                    validate_result = self.validator.validate(
                        input_materials, plan_node.requirements, output_names, cur_output
                    )
                    if validate_result.passed:
                        break
                    else:
                        cur_output = self.executor.execute(
                            input_materials, plan_node.requirements, output_names,
                            last_output=cur_output, reject_reason=validate_result.reason
                        )
                else:
                    break
            if isinstance(cur_output, dict):
                for name, value in cur_output.items():
                    intermediate_data[f"{plan_node.id}.{name}"] = value

        if not isinstance(cur_output, str):
            raise ExecutionError(
                f"Final output must be string, got {type(cur_output).__name__}. "
                "This usually indicates the final node did not produce the expected output format."
            )

        return cur_output
