import json
import os
import tempfile

import pytest

from coralmind import Agent, Task, Material, LLMConfig, PlanValidationError
from coralmind.model import Plan, PlanNode, InputField, InputFieldSourceType, TaskTemplate, PlanAdvice, PlanAdviceType
from coralmind.worker import Planner, Executor, Validator, Evaluator, PlanAdvisor, OutputFormater
from coralmind.storage import set_db_path, init_storage
from coralmind.storage.plan import PlanStorage
from coralmind.storage.task_template import TaskTemplateStorage
from fake_llm import FakeLLM, create_mock_llm


def _reset_and_init_storage(db_path: str):
    import coralmind.storage as storage_module
    storage_module._initialized = False
    set_db_path(db_path)
    init_storage()


class TestPlanner:
    
    def test_make_plan_without_advice(self):
        fake = FakeLLM()
        expected_plan = Plan(
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
        fake.set_response("plan", expected_plan)
        
        with create_mock_llm(fake):
            planner = Planner(llm=fake.get_config(), formatter_llm=fake.get_config())
            task_template = TaskTemplate(material_names=["input"], requirements="测试任务")
            
            result = planner.make_plan(task_template, advice=None)
            
            assert result is not None
            assert len(result.nodes) == 1
    
    def test_make_plan_with_use_advice(self):
        fake = FakeLLM()
        
        old_plan = Plan(
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
        
        from coralmind.model import PlanAdvice, PlanAdviceType
        advice = PlanAdvice(type=PlanAdviceType.USE, old_plan=old_plan)
        
        with create_mock_llm(fake):
            planner = Planner(llm=fake.get_config(), formatter_llm=fake.get_config())
            task_template = TaskTemplate(material_names=["input"], requirements="测试任务")
            
            result = planner.make_plan(task_template, advice)
            
            assert result.nodes[0].id == "node_1"
    
    def test_validate_plan_empty_nodes(self):
        fake = FakeLLM()
        planner = Planner(llm=fake.get_config(), formatter_llm=fake.get_config())
        
        plan = Plan(nodes=[])
        task_template = TaskTemplate(material_names=["input"], requirements="测试")
        
        with pytest.raises(PlanValidationError, match="at least 1 node"):
            planner._validate_plan(task_template, plan)
    
    def test_validate_plan_invalid_final_node(self):
        fake = FakeLLM()
        planner = Planner(llm=fake.get_config(), formatter_llm=fake.get_config())
        
        plan = Plan(
            nodes=[
                PlanNode(
                    id="node_1",
                    requirements="处理",
                    input_fields=[
                        InputField(
                            source_type=InputFieldSourceType.ORIGINAL_MATERIAL,
                            material_name="input",
                            output_of_another_node=None,
                        )
                    ],
                    output_names={"result": "输出"},
                    is_final_node=False,
                )
            ]
        )
        task_template = TaskTemplate(material_names=["input"], requirements="测试")
        
        with pytest.raises(PlanValidationError, match="final node"):
            planner._validate_plan(task_template, plan)


class TestExecutor:
    
    def test_execute_string_output(self):
        fake = FakeLLM()
        fake.set_response("execute", "这是执行结果")
        
        with create_mock_llm(fake):
            executor = Executor(llm=fake.get_config(), formatter_llm=fake.get_config())
            
            result = executor.execute(
                materials={"input": "测试内容"},
                requirements="处理输入",
                output_names=None
            )
            
            assert result == "这是执行结果"
    
    def test_execute_dict_output(self):
        fake = FakeLLM()
        fake.set_response("execute", {"keywords": "AI, ML, DL"})
        
        with create_mock_llm(fake):
            executor = Executor(llm=fake.get_config(), formatter_llm=fake.get_config())
            
            result = executor.execute(
                materials={"article": "文章内容"},
                requirements="提取关键词",
                output_names={"keywords": "关键词列表"}
            )
            
            assert result == {"keywords": "AI, ML, DL"}
    
    def test_execute_with_retry(self):
        fake = FakeLLM()
        fake.set_response("execute", "重试后的结果")
        
        with create_mock_llm(fake):
            executor = Executor(llm=fake.get_config(), formatter_llm=fake.get_config())
            
            result = executor.execute(
                materials={"input": "测试"},
                requirements="处理",
                output_names=None,
                last_output="上次结果",
                reject_reason="输出不完整"
            )
            
            assert result == "重试后的结果"


class TestValidator:
    
    def test_validate_pass(self):
        fake = FakeLLM()
        fake.set_response("validate", {"passed": True, "reason": ""})
        
        with create_mock_llm(fake):
            validator = Validator(llm=fake.get_config(), formatter_llm=fake.get_config())
            
            result = validator.validate(
                materials={"input": "测试"},
                requirements="处理",
                output_names={},
                output="结果"
            )
            
            assert result.passed is True
    
    def test_validate_fail(self):
        fake = FakeLLM()
        fake.set_response("validate", {"passed": False, "reason": "输出不完整"})
        
        with create_mock_llm(fake):
            validator = Validator(llm=fake.get_config(), formatter_llm=fake.get_config())
            
            result = validator.validate(
                materials={"input": "测试"},
                requirements="处理",
                output_names={},
                output="结果"
            )
            
            assert result.passed is False
            assert "不完整" in result.reason
    
    def test_quick_check_missing_field(self):
        result = Validator._quick_check_output_type(
            output_names={"keywords": "关键词"},
            output={"other": "其他内容"}
        )
        
        assert result is not None
        assert result.passed is False
        assert "keywords" in result.reason
    
    def test_quick_check_non_string_value(self):
        result = Validator._quick_check_output_type(
            output_names={"keywords": "关键词"},
            output={"keywords": 123}
        )
        
        assert result is not None
        assert result.passed is False
        assert "string" in result.reason
    
    def test_quick_check_pass(self):
        result = Validator._quick_check_output_type(
            output_names={"keywords": "关键词"},
            output={"keywords": "AI, ML"}
        )
        
        assert result is None


class TestEvaluator:
    
    @pytest.fixture(autouse=True)
    def setup_temp_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            self.temp_db_path = f.name
        _reset_and_init_storage(self.temp_db_path)
        yield
        os.unlink(self.temp_db_path)
    
    def test_score_new_plan(self):
        fake = FakeLLM()
        fake.set_response("score", {"score": 8, "reason": "结果良好"})
        
        with create_mock_llm(fake):
            evaluator = Evaluator(llm=fake.get_config(), formatter_llm=fake.get_config())
            
            task = Task(
                materials=[Material(name="input", content="测试内容")],
                requirements="处理输入"
            )
            plan = Plan(
                nodes=[
                    PlanNode(
                        id="node_1",
                        requirements="处理",
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
            
            score = evaluator.score(task_template_id=1, plan=plan, task=task, output="结果")
            
            assert score == 8
    
    def test_score_updates_existing_plan(self):
        fake = FakeLLM()
        fake.set_response("score", {"score": 9, "reason": "结果优秀"})
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            _reset_and_init_storage(f.name)
            
            plan = Plan(
                nodes=[
                    PlanNode(
                        id="node_1",
                        requirements="处理",
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
            plan_json = plan.model_dump_json()
            plan_id = PlanStorage.insert(task_template_id=1, plan_json=plan_json, first_score=8)
            
            with create_mock_llm(fake):
                evaluator = Evaluator(llm=fake.get_config(), formatter_llm=fake.get_config())
                
                task = Task(
                    materials=[Material(name="input", content="测试")],
                    requirements="处理"
                )
                
                score = evaluator.score(task_template_id=1, plan=plan, task=task, output="结果")
                
                assert score == 9
                
                updated = PlanStorage.get_by_id(plan_id)
                assert updated.exec_times == 2
                assert updated.total_score == 17
            
            os.unlink(f.name)


class TestPlanAdvisor:
    
    @pytest.fixture(autouse=True)
    def setup_temp_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            self.temp_db_path = f.name
        _reset_and_init_storage(self.temp_db_path)
        yield
        os.unlink(self.temp_db_path)
    
    def test_make_advice_no_history(self):
        from coralmind.strategy.advising import ThresholdStrategy
        
        advice = PlanAdvisor.make_advice(task_template_id=999, strategy=ThresholdStrategy())
        
        assert advice is None
    
    def test_make_advice_with_high_score_plan(self):
        from coralmind.strategy.advising import ThresholdStrategy
        
        plan = Plan(
            nodes=[
                PlanNode(
                    id="node_1",
                    requirements="处理",
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
        plan_json = plan.model_dump_json()
        
        plan_id = PlanStorage.insert(task_template_id=1, plan_json=plan_json, first_score=9)
        PlanStorage.update_score(plan_id, score=9)
        PlanStorage.update_score(plan_id, score=9)
        
        strategy = ThresholdStrategy(s0=8.0, s1=9.0, c=1)
        advice = PlanAdvisor.make_advice(task_template_id=1, strategy=strategy)
        
        assert advice is not None
        assert advice.type == PlanAdviceType.USE


class TestOutputFormater:
    
    def test_format_output_no_change(self):
        fake = FakeLLM()
        fake.set_response("format", {"need_reformat": False, "new_content": None})
        
        with create_mock_llm(fake):
            formatter = OutputFormater(llm=fake.get_config())
            
            result = formatter.format_output(
                requirements="生成摘要",
                output="这是摘要内容"
            )
            
            assert result == "这是摘要内容"
    
    def test_format_output_with_change(self):
        fake = FakeLLM()
        fake.set_response("format", {
            "need_reformat": True,
            "new_content": "纯净的摘要内容"
        })
        
        with create_mock_llm(fake):
            formatter = OutputFormater(llm=fake.get_config())
            
            result = formatter.format_output(
                requirements="生成摘要",
                output="这是摘要内容，还有一些无关信息"
            )
            
            assert result == "纯净的摘要内容"
