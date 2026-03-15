from fake_llm import FakeLLMInstance
from plan_example import plan_example

from coralmind import Agent
from coralmind.model import OutputConstraints, OutputType, Plan, TaskTemplate


def test_plan():
    agent = Agent(default_llm=FakeLLMInstance)
    plan = Plan.model_validate(plan_example)
    task_template = TaskTemplate(
        material_names=["market_report", "competitor_analysis", "user_survey"],
        requirements="制定产品策略方案"
    )
    agent.planner._validate_plan_structure(task_template, plan)


def test_plan_single_node():
    from coralmind.model import InputField, InputFieldSourceType, PlanNode

    agent = Agent(default_llm=FakeLLMInstance)

    plan = Plan(
        nodes=[
            PlanNode(
                id="final",
                requirements="处理任务",
                input_fields=[
                    InputField(
                        source_type=InputFieldSourceType.ORIGINAL_MATERIAL,
                        material_name="input",
                        output_of_another_node=None,
                    )
                ],
                output_constraints=OutputConstraints(
                    output_type=OutputType.TEXT,
                    content_spec="处理结果"
                ),
                is_final_node=True,
            )
        ]
    )
    task_template = TaskTemplate(material_names=["input"], requirements="测试")

    agent.planner._validate_plan_structure(task_template, plan)
