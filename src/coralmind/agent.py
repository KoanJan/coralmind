import logging

from pydantic import BaseModel

from .exceptions import ExecutionError, PlanValidationError
from .llm import LLMConfig, LLMResponse, TokenCost
from .model import InputFieldSourceType, OutputType, Plan, PlanAdvice, Task, TaskStep, TaskTemplate
from .requirements_finder import RelevantRequirementsFinder
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
            embedding_llm: LLMConfig | None = None,
            advising_strategy: BasePlanStrategy | None = None,
            max_retry_times_per_node: int = 3,
            max_retry_times_for_plan: int = 3,
    ):
        init_storage()

        self.default_llm = default_llm
        self.embedding_llm = embedding_llm
        self.advising_strategy = advising_strategy if advising_strategy else _DEFAULT_STRATEGY

        self.plan_advisor = PlanAdvisor()
        self.validator = Validator(
            llm=validator_llm if validator_llm else default_llm,
            formatter_llm=default_llm
        )
        self.planner = Planner(
            llm=planner_llm if planner_llm else default_llm,
            formatter_llm=default_llm
        )
        self.executor = Executor(
            llm=executor_llm if executor_llm else default_llm,
            formatter_llm=default_llm
        )

        if validator_llm:
            evaluator_llm = validator_llm
        elif planner_llm:
            evaluator_llm = planner_llm
        else:
            evaluator_llm = default_llm
        self.evaluator = Evaluator(llm=evaluator_llm, formatter_llm=default_llm)
        self.output_formatter = OutputFormatter(llm=default_llm)

        self.max_retry_times_per_node: int = max_retry_times_per_node
        self.max_retry_times_for_plan: int = max_retry_times_for_plan

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

        finder = RelevantRequirementsFinder(
            self.default_llm,
            self.embedding_llm,
            task.requirements,
            task_template_id,
            language=task.language
        )

        advice = self.plan_advisor.make_advice(task_template_id, self.advising_strategy)
        logger.debug(f"Plan advice: type={advice.type if advice else None}")

        plan_response = self._generate_plan(task_template, advice)
        plan = plan_response.content
        logger.info(f"Plan generated: {len(plan.nodes)} nodes, token_cost={plan_response.token_cost.total}")

        orchestrate_response = self._orchestrate(task, plan, finder)
        output = orchestrate_response.content
        logger.info(f"Orchestration completed: output_length={len(output)}, token_cost={orchestrate_response.token_cost.total}")

        score_response = self.evaluator.score(task, output)
        logger.info(f"Evaluation completed: score={score_response.content.score}, token_cost={score_response.token_cost.total}")

        self._save_plan(task_template_id, plan, plan_response, orchestrate_response, score_response)
        logger.debug("Plan saved to database")

        output = self.output_formatter.format_output(task.requirements, output, task.output_format, language=task.language)
        logger.debug(f"Task execution completed: final_output_length={len(output)}")
        return output

    def _generate_plan(self, task_template: TaskTemplate, advice: PlanAdvice | None) -> LLMResponse[Plan]:
        """
        Generate plan with simple retry mechanism

        Args:
            task_template: Task template containing material names and requirements
            advice: Optional plan advice containing historical good plans

        Returns:
            LLMResponse[Plan]: Response containing plan and token cost

        Raises:
            PlanValidationError: If plan validation fails after all retry attempts
        """
        last_error: PlanValidationError | None = None

        for attempt in range(self.max_retry_times_for_plan):
            logger.debug(f"Plan generation attempt {attempt + 1}/{self.max_retry_times_for_plan}")

            try:
                plan_response = self.planner.make_plan(task_template, advice)
                logger.debug(f"Plan generated: {len(plan_response.content.nodes)} nodes")
                return plan_response
            except PlanValidationError as e:
                last_error = e
                logger.debug(f"Plan validation failed: {e}")

        logger.error(f"Plan validation failed after {self.max_retry_times_for_plan} attempts")
        raise PlanValidationError(
            f"Plan validation failed after {self.max_retry_times_for_plan} attempts. "
            f"Last error: {last_error}"
        )

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

    def _orchestrate(self, task: Task, plan: Plan, finder: RelevantRequirementsFinder) -> LLMResponse[str]:
        """
        Orchestrate the entire workflow according to the plan

        Args:
            task: Task containing materials, requirements and language
            plan: Execution plan
            finder: RelevantRequirementsFinder for retrieving relevant requirements

        Returns:
            LLMResponse[str]: Response containing final output and accumulated token cost
        """
        logger.debug(f"Starting orchestration with {len(plan.nodes)} nodes")

        # Initialize: convert materials list to dict for easy lookup by name
        materials_dict = {m.name: m.content for m in task.materials}
        # Store intermediate node outputs, key format: "node_id.field_name"
        intermediate_data: dict[str, str] = {}
        cur_output: str | BaseModel | None = None
        total_token_cost = TokenCost(prompt=0, completion=0, total=0)

        if (not plan.nodes) or len(plan.nodes) == 0:
            raise PlanValidationError("Plan contains 0 nodes")

        # Execute each node in the plan sequentially
        for i, plan_node in enumerate(plan.nodes):
            logger.debug(f"Executing node {i+1}/{len(plan.nodes)}: {plan_node.id} (is_final={plan_node.is_final_node})")

            # Prepare input materials: include all original materials by default
            input_materials: dict[str, str] = dict(materials_dict)
            # Add outputs from other nodes as inputs
            for input_field in plan_node.input_fields:
                if input_field.source_type == InputFieldSourceType.OUTPUT_OF_ANOTHER_NODE:
                    dep_node = input_field.output_of_another_node
                    if dep_node is None:
                        raise PlanValidationError("output_of_another_node is required", node_id=plan_node.id)
                    key = f"{dep_node.node_id}.{dep_node.output_field_name}"
                    input_materials[key] = intermediate_data[key]

            logger.debug(f"Node {plan_node.id}: input_materials={list(input_materials.keys())}")

            # Find relevant requirements for current node
            relevant_requirements = finder.find(plan_node.requirements)

            # Build task step
            task_step = TaskStep(
                materials=input_materials,
                requirements=plan_node.requirements,
                output_constraints=plan_node.output_constraints,
                language=task.language,
                relevant_requirements=relevant_requirements
            )

            # Execute-validate loop with retry support
            for attempt in range(self.max_retry_times_per_node):
                logger.debug(f"Node {plan_node.id}: execution attempt {attempt + 1}/{self.max_retry_times_per_node}")

                # Execute node task
                exec_response = self.executor.execute(task_step)
                total_token_cost = total_token_cost + exec_response.token_cost
                cur_output = exec_response.content

                # Validate execution result
                validate_response = self.validator.validate_execution(task_step, cur_output)
                total_token_cost = total_token_cost + validate_response.token_cost

                if validate_response.content.passed:
                    logger.debug(f"Node {plan_node.id}: validation passed")
                    break
                else:
                    # Validation failed, retry with rejection reason
                    logger.debug(f"Node {plan_node.id}: validation failed, reason: {validate_response.content.reason}")
                    exec_response = self.executor.execute(
                        task_step,
                        last_output=cur_output,
                        reject_reason=validate_response.content.reason
                    )
                    total_token_cost = total_token_cost + exec_response.token_cost
                    cur_output = exec_response.content

            # If MODEL type output, store each field in intermediate_data for subsequent nodes
            if task_step.output_constraints.output_type == OutputType.MODEL and task_step.output_constraints.fields is not None and isinstance(cur_output, BaseModel):
                for name in cur_output.model_fields:
                    intermediate_data[f"{plan_node.id}.{name}"] = getattr(cur_output, name)
                logger.debug(f"Node {plan_node.id}: output_names={list(cur_output.model_fields.keys())}")

        # Final output must be string type
        if not isinstance(cur_output, str):
            raise ExecutionError(
                f"Final output must be string, got {type(cur_output).__name__}. "
                "This usually indicates the final node did not produce the expected output format."
            )

        logger.debug(f"Orchestration completed: total_token_cost={total_token_cost.total}")
        return LLMResponse(content=cur_output, token_cost=total_token_cost, model="")
