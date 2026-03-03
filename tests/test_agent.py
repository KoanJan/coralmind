import pytest
from fake_llm import FakeLLM, FakeLLMInstance, create_mock_llm

from coralmind import Agent, Material, PlanValidationError, Task
from coralmind.model import InputField, InputFieldSourceType, Plan, PlanNode, TaskTemplate


def test_agent_simple_task():
    fake = FakeLLM()

    fake.set_response("plan", Plan(
        nodes=[
            PlanNode(
                id="node_1",
                requirements="对输入文本进行摘要",
                input_fields=[
                    InputField(
                        source_type=InputFieldSourceType.ORIGINAL_MATERIAL,
                        material_name="input_text",
                        output_of_another_node=None,
                    )
                ],
                output_names=None,
                is_final_node=True,
            )
        ]
    ))
    fake.set_response("execute", "这是一个摘要结果。")
    fake.set_response("validate", {"passed": True, "reason": ""})
    fake.set_response("score", {"score": 8, "reason": "摘要准确简洁"})
    fake.set_response("format", {"need_reformat": False, "new_content": None})

    with create_mock_llm(fake):
        agent = Agent(default_llm=fake.get_config())

        task = Task(
            materials=[Material(name="input_text", content="这是一段需要摘要的长文本内容...")],
            requirements="对输入文本进行摘要，不超过100字"
        )

        result = agent.run(task)

        assert result is not None
        assert len(fake.call_history) > 0


def test_agent_multi_node_task():
    fake = FakeLLM()

    fake.set_response("plan", Plan(
        nodes=[
            PlanNode(
                id="node_1",
                requirements="提取文章的关键词",
                input_fields=[
                    InputField(
                        source_type=InputFieldSourceType.ORIGINAL_MATERIAL,
                        material_name="article",
                        output_of_another_node=None,
                    )
                ],
                output_names={"keywords": "文章关键词列表"},
                is_final_node=False,
            ),
            PlanNode(
                id="node_2",
                requirements="根据关键词生成摘要",
                input_fields=[
                    InputField(
                        source_type=InputFieldSourceType.OUTPUT_OF_ANOTHER_NODE,
                        material_name="",
                        output_of_another_node=InputField.OutputOfAnotherNode(
                            node_id="node_1",
                            output_field_name="keywords",
                        )
                    )
                ],
                output_names=None,
                is_final_node=True,
            )
        ]
    ))
    fake.set_response("execute", {"keywords": "人工智能, 机器学习, 深度学习"})
    fake.set_response("validate", {"passed": True, "reason": ""})
    fake.set_response("score", {"score": 9, "reason": "关键词提取准确"})
    fake.set_response("format", {"need_reformat": False, "new_content": None})

    with create_mock_llm(fake):
        agent = Agent(default_llm=fake.get_config())

        task = Task(
            materials=[Material(name="article", content="这是一篇关于人工智能的文章...")],
            requirements="先提取关键词，再根据关键词生成摘要"
        )

        result = agent.run(task)

        assert result is not None


def test_plan_validation():
    agent = Agent(default_llm=FakeLLMInstance)

    plan = Plan(
        nodes=[
            PlanNode(
                id="node_1",
                requirements="处理输入",
                input_fields=[
                    InputField(
                        source_type=InputFieldSourceType.ORIGINAL_MATERIAL,
                        material_name="input",
                        output_of_another_node=None,
                    )
                ],
                output_names=None,
                is_final_node=True,
            )
        ]
    )

    task_template = TaskTemplate(material_names=["input"], requirements="测试任务")

    agent.planner._validate_plan(task_template, plan)


def test_plan_validation_empty_nodes():
    agent = Agent(default_llm=FakeLLMInstance)

    plan = Plan(nodes=[])
    task_template = TaskTemplate(material_names=["input"], requirements="测试任务")

    with pytest.raises(PlanValidationError, match="at least 1 node"):
        agent.planner._validate_plan(task_template, plan)


def test_plan_validation_duplicate_node_id():
    agent = Agent(default_llm=FakeLLMInstance)

    plan = Plan(
        nodes=[
            PlanNode(
                id="node_1",
                requirements="处理输入",
                input_fields=[
                    InputField(
                        source_type=InputFieldSourceType.ORIGINAL_MATERIAL,
                        material_name="input",
                        output_of_another_node=None,
                    )
                ],
                output_names={"result": "输出"},
                is_final_node=False,
            ),
            PlanNode(
                id="node_1",
                requirements="最终处理",
                input_fields=[
                    InputField(
                        source_type=InputFieldSourceType.OUTPUT_OF_ANOTHER_NODE,
                        material_name="",
                        output_of_another_node=InputField.OutputOfAnotherNode(
                            node_id="node_1",
                            output_field_name="result",
                        )
                    )
                ],
                output_names=None,
                is_final_node=True,
            ),
        ]
    )
    task_template = TaskTemplate(material_names=["input"], requirements="测试任务")

    with pytest.raises(PlanValidationError, match="Duplicate node_id"):
        agent.planner._validate_plan(task_template, plan)


def test_plan_validation_invalid_material():
    agent = Agent(default_llm=FakeLLMInstance)

    plan = Plan(
        nodes=[
            PlanNode(
                id="node_1",
                requirements="处理输入",
                input_fields=[
                    InputField(
                        source_type=InputFieldSourceType.ORIGINAL_MATERIAL,
                        material_name="non_existent",
                        output_of_another_node=None,
                    )
                ],
                output_names=None,
                is_final_node=True,
            )
        ]
    )
    task_template = TaskTemplate(material_names=["input"], requirements="测试任务")

    with pytest.raises(PlanValidationError, match="not found in task template"):
        agent.planner._validate_plan(task_template, plan)
