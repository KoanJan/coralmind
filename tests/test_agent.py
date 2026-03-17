import os
import tempfile

from fake_llm import FakeLLM, create_mock_llm

from coralmind import Agent, Material, Task
from coralmind.model import (
    InputField,
    InputFieldSourceType,
    OutputConstraints,
    OutputType,
    Plan,
    PlanNode,
)
from coralmind.storage import init_storage, set_db_path


def _reset_and_init_storage(db_path: str):
    import coralmind.storage as storage_module
    storage_module._initialized = False
    set_db_path(db_path)
    init_storage()


def test_agent_simple_task():
    fake = FakeLLM()

    fake.set_response("plan", Plan(
        deliverable="摘要结果",
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
                output_constraints=OutputConstraints(
                    output_type=OutputType.TEXT,
                    content_spec="摘要结果"
                ),
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
        deliverable="摘要结果",
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
                output_constraints=OutputConstraints(
                    output_type=OutputType.MODEL,
                    fields={"keywords": "文章关键词列表"},
                    content_spec="文章关键词列表"
                ),
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
                output_constraints=OutputConstraints(
                    output_type=OutputType.TEXT,
                    content_spec="摘要结果"
                ),
                is_final_node=True,
            )
        ]
    ))
    fake.set_responses("execute", [
        '{"keywords": "人工智能, 机器学习, 深度学习"}',
        "这是一篇关于人工智能、机器学习和深度学习的文章摘要。",
    ])
    fake.set_response("validate", {"passed": True, "reason": ""})
    fake.set_response("score", {"score": 9, "reason": "关键词提取准确"})
    fake.set_response("format", {"need_reformat": False, "new_content": ""})

    with create_mock_llm(fake):
        agent = Agent(default_llm=fake.get_config())

        task = Task(
            materials=[Material(name="article", content="这是一篇关于人工智能的文章...")],
            requirements="先提取关键词，再根据关键词生成摘要"
        )

        result = agent.run(task)

        assert result is not None
        assert len(fake.call_history) > 0


def test_agent_final_node_with_output_constraints():
    fake = FakeLLM()

    fake.set_response("plan", Plan(
        deliverable="文本摘要",
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
                output_constraints=OutputConstraints(
                    output_type=OutputType.TEXT,
                    content_spec="一段简洁的摘要，不超过100字"
                ),
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


class TestAgentStorage:

    def test_agent_with_storage(self):
        fake = FakeLLM()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            _reset_and_init_storage(db_path)

            fake.set_response("plan", Plan(
                deliverable="处理结果",
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
                        output_constraints=OutputConstraints(
                            output_type=OutputType.TEXT,
                            content_spec="处理结果"
                        ),
                        is_final_node=True,
                    )
                ]
            ))
            fake.set_response("execute", "处理结果")
            fake.set_response("validate", {"passed": True, "reason": ""})
            fake.set_response("score", {"score": 8, "reason": "良好"})
            fake.set_response("format", {"need_reformat": False, "new_content": None})

            with create_mock_llm(fake):
                agent = Agent(default_llm=fake.get_config())

                task = Task(
                    materials=[Material(name="input", content="测试内容")],
                    requirements="处理输入"
                )

                result = agent.run(task)

                assert result is not None
