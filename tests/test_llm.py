from pydantic import BaseModel, Field

from coralmind.llm import (
    LLMResponse,
    TokenCost,
    as_user_messages,
    call_llm,
)


class SampleModel(BaseModel):
    name: str = Field(description="Name")
    count: int = Field(description="Count")


class TestCallLLM:
    """Test call_llm function with structured output"""

    def test_str_output(self):
        """Test that str output type returns string content"""
        from unittest.mock import MagicMock, patch

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, world!"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        with patch('coralmind.llm.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response

            from coralmind.llm import LLMConfig
            config = LLMConfig(
                model_id="test-model",
                base_url="https://api.test.com",
                api_key="test-key"
            )

            result = call_llm(config, as_user_messages(["test"]), str)
            assert result.content == "Hello, world!"
            assert result.token_cost.total == 15


class TestTokenCost:
    """Test TokenCost model"""

    def test_addition(self):
        cost1 = TokenCost(prompt=10, completion=5, total=15)
        cost2 = TokenCost(prompt=20, completion=10, total=30)
        result = cost1 + cost2
        assert result.prompt == 30
        assert result.completion == 15
        assert result.total == 45


class TestLLMResponse:
    """Test LLMResponse model"""

    def test_model_response(self):
        model = SampleModel(name="test", count=5)
        response = LLMResponse(
            content=model,
            token_cost=TokenCost(prompt=10, completion=5, total=15),
            model="test-model"
        )
        assert response.content.name == "test"
        assert response.content.count == 5

    def test_str_response(self):
        response = LLMResponse(
            content="test output",
            token_cost=TokenCost(prompt=10, completion=5, total=15),
            model="test-model"
        )
        assert response.content == "test output"
