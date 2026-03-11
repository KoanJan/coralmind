import logging

from .exceptions import ExecutionError, PlanValidationError
from .llm import LLMConfig, LLMResponse, TokenCost
from .model import InputFieldSourceType, Language, Material, Plan, Task, TaskTemplate
from .storage import PlanStorage, TaskTemplateStorage, init_storage
from .strategy.advising import BasePlanStrategy, ThresholdStrategy
from .worker import Evaluator, Executor, OutputFormatter, PlanAdvisor, Planner, Validator

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
        self.output_formatter = OutputFormatter(llm=default_llm)

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
            requirements=task.requirements,
            output_format=task.output_format,
            language=task.language,
        )

    def run(self, task: Task) -> str:
        """
        Execute task
        """
        logger.debug(f"Starting task execution with {len(task.materials)} materials")

        task_template = self._extract_task_template(task)
        logger.debug(f"Task template extracted: materials={task_template.material_names}, has_output_format={task_template.output_format is not None}")

        task_template_id = self._get_task_template_id(task_template)
        logger.debug(f"Task template ID: {task_template_id}")

        advice = self.plan_advisor.make_advice(task_template_id, self.advising_strategy)
        logger.debug(f"Plan advice: type={advice.type if advice else None}")

        plan_response = self.planner.make_plan(task_template, advice)
        plan = plan_response.content
        logger.info(f"Plan generated: {len(plan.nodes)} nodes, token_cost={plan_response.token_cost.total}")

        orchestrate_response = self._orchestrate(task.materials, plan, task.language)
        output = orchestrate_response.content
        logger.info(f"Orchestration completed: output_length={len(output)}, token_cost={orchestrate_response.token_cost.total}")

        score_response = self.evaluator.score(task, output)
        logger.info(f"Evaluation completed: score={score_response.content.score}, token_cost={score_response.token_cost.total}")

        self._save_plan(task_template_id, plan, plan_response, orchestrate_response, score_response)
        logger.debug("Plan saved to database")

        output = self.output_formatter.format_output(task.requirements, output, task.output_format, language=task.language)
        logger.debug(f"Task execution completed: final_output_length={len(output)}")
        return output

    @staticmethod
    def _save_plan(
            task_template_id: int,
            plan: Plan,
            plan_response: LLMResponse[Plan],
            orchestrate_response: LLMResponse[str],
            score_response: LLMResponse,
    ) -> None:
        """
        Save plan with aggregated token cost and score to database
        """
        plan_json = plan.model_dump_json()
        score = score_response.content.score

        total_token_cost = (
            plan_response.token_cost
            + orchestrate_response.token_cost
            + score_response.token_cost
        )

        old_plans = PlanStorage.get_by_task_template_id(task_template_id)
        for old_plan in old_plans:
            if old_plan.plan_json == plan_json:
                PlanStorage.update_score(
                    old_plan.id, score,
                    total_token_cost.prompt, total_token_cost.completion, total_token_cost.total
                )
                return

        PlanStorage.upsert(
            task_template_id, plan_json, score,
            total_token_cost.prompt, total_token_cost.completion, total_token_cost.total
        )

    def _orchestrate(self, materials: list[Material], plan: Plan, language: Language) -> LLMResponse[str]:
        """
        Orchestrate the entire workflow according to the plan

        Returns:
            LLMResponse[str]: Response containing final output and accumulated token cost
        """
        logger.debug(f"Starting orchestration with {len(plan.nodes)} nodes")

        materials_dict = {m.name: m.content for m in materials}
        intermediate_data: dict[str, str] = {}
        cur_output: str | dict[str, str] | None = None
        total_token_cost = TokenCost(prompt=0, completion=0, total=0)

        if (not plan.nodes) or len(plan.nodes) == 0:
            raise PlanValidationError("Plan contains 0 nodes")

        for i, plan_node in enumerate(plan.nodes):
            logger.debug(f"Executing node {i+1}/{len(plan.nodes)}: {plan_node.id} (is_final={plan_node.is_final_node})")

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

            logger.debug(f"Node {plan_node.id}: input_materials={list(input_materials.keys())}")

            output_names = plan_node.output_names or {}
            for attempt in range(self.max_retry_times_per_node):
                logger.debug(f"Node {plan_node.id}: execution attempt {attempt + 1}/{self.max_retry_times_per_node}")

                exec_response = self.executor.execute(input_materials, plan_node.requirements, output_names, language=language)
                total_token_cost = total_token_cost + exec_response.token_cost
                cur_output = exec_response.content

                if output_names:
                    validate_response = self.validator.validate(
                        input_materials, plan_node.requirements, output_names, cur_output, language=language
                    )
                    total_token_cost = total_token_cost + validate_response.token_cost

                    if validate_response.content.passed:
                        logger.debug(f"Node {plan_node.id}: validation passed")
                        break
                    else:
                        logger.debug(f"Node {plan_node.id}: validation failed, reason: {validate_response.content.reason}")
                        exec_response = self.executor.execute(
                            input_materials, plan_node.requirements, output_names,
                            last_output=cur_output, reject_reason=validate_response.content.reason,
                            language=language
                        )
                        total_token_cost = total_token_cost + exec_response.token_cost
                        cur_output = exec_response.content
                else:
                    logger.debug(f"Node {plan_node.id}: no output_names, skipping validation")
                    break

            if isinstance(cur_output, dict):
                for name, value in cur_output.items():
                    intermediate_data[f"{plan_node.id}.{name}"] = value
                logger.debug(f"Node {plan_node.id}: output_names={list(cur_output.keys())}")

        if not isinstance(cur_output, str):
            raise ExecutionError(
                f"Final output must be string, got {type(cur_output).__name__}. "
                "This usually indicates the final node did not produce the expected output format."
            )

        logger.debug(f"Orchestration completed: total_token_cost={total_token_cost.total}")
        return LLMResponse(content=cur_output, token_cost=total_token_cost, model="")
