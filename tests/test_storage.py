import json
import os
import tempfile

import pytest

from coralmind.storage import set_db_path, get_db_path
from coralmind.storage.plan import PlanStorage, PlanRO
from coralmind.storage.task_template import TaskTemplateStorage, TaskTemplateRO
from coralmind.model import Plan, PlanNode, InputField, InputFieldSourceType


class TestConnection:
    
    def test_set_and_get_db_path(self):
        original_path = get_db_path()
        try:
            set_db_path("/custom/path/test.db")
            assert get_db_path() == "/custom/path/test.db"
        finally:
            set_db_path(original_path)
    
    def test_set_db_path_with_path_object(self):
        original_path = get_db_path()
        try:
            from pathlib import Path
            set_db_path(Path("/custom/path/test.db"))
            assert get_db_path() == "/custom/path/test.db"
        finally:
            set_db_path(original_path)


class TestPlanStorage:
    
    @pytest.fixture(autouse=True)
    def setup_temp_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            self.temp_db_path = f.name
        set_db_path(self.temp_db_path)
        PlanStorage.init_table()
        yield
        os.unlink(self.temp_db_path)
    
    def test_init_table_creates_db_file(self):
        assert os.path.exists(self.temp_db_path)
        assert os.path.getsize(self.temp_db_path) > 0
    
    def test_insert_and_get_by_id(self):
        plan_json = '{"nodes": []}'
        plan_id = PlanStorage.insert(task_template_id=1, plan_json=plan_json, first_score=8)
        
        result = PlanStorage.get_by_id(plan_id)
        
        assert result is not None
        assert result.id == plan_id
        assert result.plan_json == plan_json
        assert result.task_template_id == 1
        assert result.exec_times == 1
        assert result.total_score == 8
    
    def test_get_by_task_template_id(self):
        PlanStorage.insert(task_template_id=1, plan_json='{"nodes": [1]}', first_score=8)
        PlanStorage.insert(task_template_id=1, plan_json='{"nodes": [2]}', first_score=7)
        PlanStorage.insert(task_template_id=2, plan_json='{"nodes": [3]}', first_score=9)
        
        results = PlanStorage.get_by_task_template_id(1)
        
        assert len(results) == 2
        assert all(r.task_template_id == 1 for r in results)
    
    def test_get_by_task_template_id_empty(self):
        results = PlanStorage.get_by_task_template_id(999)
        assert results == []
    
    def test_update_score(self):
        plan_id = PlanStorage.insert(task_template_id=1, plan_json='{"nodes": []}', first_score=8)
        
        PlanStorage.update_score(plan_id, score=9)
        
        result = PlanStorage.get_by_id(plan_id)
        assert result.exec_times == 2
        assert result.total_score == 17
    
    def test_upsert_insert_new(self):
        plan_json = '{"nodes": []}'
        PlanStorage.upsert(task_template_id=1, plan_json=plan_json, first_score=8)
        
        result = PlanStorage.get_by_task_template_id(1)
        assert len(result) == 1
        assert result[0].exec_times == 1
        assert result[0].total_score == 8
    
    def test_upsert_update_existing(self):
        plan_json = '{"nodes": []}'
        PlanStorage.upsert(task_template_id=1, plan_json=plan_json, first_score=8)
        PlanStorage.upsert(task_template_id=1, plan_json=plan_json, first_score=9)
        
        result = PlanStorage.get_by_task_template_id(1)
        assert len(result) == 1
        assert result[0].exec_times == 2
        assert result[0].total_score == 17
    
    def test_plan_ro_avg_score(self):
        ro = PlanRO(id=1, task_template_id=1, plan_json='{}', exec_times=2, total_score=18)
        assert ro.avg_score == 9.0
    
    def test_plan_ro_avg_score_zero_exec_times(self):
        ro = PlanRO(id=1, task_template_id=1, plan_json='{}', exec_times=0, total_score=0)
        assert ro.avg_score == 0.0


class TestTaskTemplateStorage:
    
    @pytest.fixture(autouse=True)
    def setup_temp_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            self.temp_db_path = f.name
        set_db_path(self.temp_db_path)
        TaskTemplateStorage.init_table()
        yield
        os.unlink(self.temp_db_path)
    
    def test_insert_and_get_by_id(self):
        template_json = '{"material_names": ["input"], "requirements": "test"}'
        template_id = TaskTemplateStorage.insert(template_json)
        
        result = TaskTemplateStorage.get_by_id(template_id)
        
        assert result is not None
        assert result.id == template_id
        assert result.task_template_json == template_json
    
    def test_insert_duplicate_returns_same_id(self):
        template_json = '{"material_names": ["input"], "requirements": "test"}'
        id1 = TaskTemplateStorage.insert(template_json)
        id2 = TaskTemplateStorage.insert(template_json)
        
        assert id1 == id2
    
    def test_find_by_content(self):
        template_json = '{"material_names": ["input"], "requirements": "test"}'
        TaskTemplateStorage.insert(template_json)
        
        result = TaskTemplateStorage.find_by_content(template_json)
        
        assert result is not None
        assert result.task_template_json == template_json
    
    def test_find_by_content_not_found(self):
        result = TaskTemplateStorage.find_by_content('{"nonexistent": true}')
        assert result is None
    
    def test_task_template_ro_properties(self):
        template_json = '{"material_names": ["article", "summary"], "requirements": "generate summary"}'
        TaskTemplateStorage.insert(template_json)
        
        ro = TaskTemplateStorage.find_by_content(template_json)
        
        assert ro.material_names == ["article", "summary"]
        assert ro.requirements == "generate summary"
    
    def test_get_by_id_not_found(self):
        result = TaskTemplateStorage.get_by_id(99999)
        assert result is None
