import json
from unittest.mock import patch

import pytest
from fake_llm import FakeLLM
from pydantic import BaseModel, Field

from coralmind.exceptions import LLMError
from coralmind.llm import (
    LLMResponse,
    TokenCost,
    _fix_dict_structure_by_llm,
    _fix_model_json_by_llm,
    _is_dict_str_str,
    _to_dict,
    _to_model,
)


class TestIsDictStrStr:

    def test_all_strings(self):
        assert _is_dict_str_str({"a": "1", "b": "2"}) is True

    def test_non_string_value(self):
        assert _is_dict_str_str({"a": 1}) is False
        assert _is_dict_str_str({"a": ["1", "2"]}) is False
        assert _is_dict_str_str({"a": {"b": "c"}}) is False

    def test_non_string_key(self):
        assert _is_dict_str_str({1: "a"}) is False

    def test_empty_dict(self):
        assert _is_dict_str_str({}) is True


class TestToDict:

    def test_valid_dict_str_str(self):
        fake = FakeLLM()
        result = _to_dict(fake.get_config(), '{"key": "value"}')
        assert result == {"key": "value"}

    def test_non_dict_raises_error_no_retry(self):
        fake = FakeLLM()
        with pytest.raises(LLMError, match="Expected JSON object"):
            _to_dict(fake.get_config(), '["item1", "item2"]', max_retries=0)

    def test_nested_value_raises_error_no_retry(self):
        fake = FakeLLM()
        with pytest.raises(LLMError, match="not strings"):
            _to_dict(fake.get_config(), '{"key": {"nested": "value"}}', max_retries=0)

    def test_array_value_raises_error_no_retry(self):
        fake = FakeLLM()
        with pytest.raises(LLMError, match="not strings"):
            _to_dict(fake.get_config(), '{"items": ["a", "b"]}', max_retries=0)

    def test_invalid_json_raises_error_no_retry(self):
        fake = FakeLLM()
        with pytest.raises(LLMError, match="Failed to parse JSON"):
            _to_dict(fake.get_config(), 'not valid json', max_retries=0)

    def test_retry_with_llm_fix_success(self):
        fake = FakeLLM()
        call_count = 0

        def mock_call(llm, messages):
            nonlocal call_count
            call_count += 1
            return LLMResponse(
                content='{"items": "item1\\nitem2"}',
                token_cost=TokenCost(prompt=1, completion=1, total=2),
                model="fake"
            )

        with patch('coralmind.llm._call_llm', side_effect=mock_call):
            result = _to_dict(fake.get_config(), '{"items": ["item1", "item2"]}', max_retries=1)
            assert result == {"items": "item1\nitem2"}
            assert call_count == 1

    def test_retry_exhausted_raises_error(self):
        fake = FakeLLM()
        call_count = 0

        def mock_call(llm, messages):
            nonlocal call_count
            call_count += 1
            return LLMResponse(
                content='{"items": ["still", "array"]}',
                token_cost=TokenCost(prompt=1, completion=1, total=2),
                model="fake"
            )

        with patch('coralmind.llm._call_llm', side_effect=mock_call):
            with pytest.raises(LLMError, match="not strings"):
                _to_dict(fake.get_config(), '{"items": ["item1", "item2"]}', max_retries=2)
            assert call_count == 2


class TestFixDictStructureByLLM:

    def test_fix_returns_json_string(self):
        fake = FakeLLM()

        def mock_call(llm, messages):
            return LLMResponse(
                content='{"data": "value1, value2"}',
                token_cost=TokenCost(prompt=1, completion=1, total=2),
                model="fake"
            )

        with patch('coralmind.llm._call_llm', side_effect=mock_call):
            result = _fix_dict_structure_by_llm(
                fake.get_config(),
                '{"data": ["value1", "value2"]}',
                "values are not strings"
            )
            parsed = json.loads(result)
            assert "data" in parsed
            assert parsed["data"] == "value1, value2"


class SampleModel(BaseModel):
    name: str = Field(description="Name")
    count: int = Field(description="Count")


class TestToModel:

    def test_valid_model(self):
        fake = FakeLLM()
        result = _to_model(fake.get_config(), '{"name": "test", "count": 5}', SampleModel)
        assert result.name == "test"
        assert result.count == 5

    def test_invalid_model_raises_error_no_retry(self):
        fake = FakeLLM()
        with pytest.raises(LLMError, match="Failed to validate"):
            _to_model(fake.get_config(), '{"name": "test"}', SampleModel, max_retries=0)

    def test_retry_with_llm_fix_success(self):
        fake = FakeLLM()
        call_count = 0

        def mock_call(llm, messages):
            nonlocal call_count
            call_count += 1
            return LLMResponse(
                content='{"name": "test", "count": 10}',
                token_cost=TokenCost(prompt=1, completion=1, total=2),
                model="fake"
            )

        with patch('coralmind.llm._call_llm', side_effect=mock_call):
            result = _to_model(fake.get_config(), '{"name": "test"}', SampleModel, max_retries=1)
            assert result.name == "test"
            assert result.count == 10
            assert call_count == 1

    def test_retry_exhausted_raises_error(self):
        fake = FakeLLM()
        call_count = 0

        def mock_call(llm, messages):
            nonlocal call_count
            call_count += 1
            return LLMResponse(
                content='{"name": "test"}',
                token_cost=TokenCost(prompt=1, completion=1, total=2),
                model="fake"
            )

        with patch('coralmind.llm._call_llm', side_effect=mock_call):
            with pytest.raises(LLMError, match="Failed to validate"):
                _to_model(fake.get_config(), '{"name": "test"}', SampleModel, max_retries=2)
            assert call_count == 2


class TestFixModelJsonByLLM:

    def test_fix_returns_valid_json(self):
        fake = FakeLLM()

        def mock_call(llm, messages):
            return LLMResponse(
                content='{"name": "fixed", "count": 0}',
                token_cost=TokenCost(prompt=1, completion=1, total=2),
                model="fake"
            )

        with patch('coralmind.llm._call_llm', side_effect=mock_call):
            result = _fix_model_json_by_llm(
                fake.get_config(),
                '{"name": "test"}',
                SampleModel,
                "Field required: count"
            )
            parsed = json.loads(result)
            assert "name" in parsed
            assert "count" in parsed
