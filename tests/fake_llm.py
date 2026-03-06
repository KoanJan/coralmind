import json
from unittest.mock import patch

from pydantic import BaseModel

from coralmind import LLMConfig
from coralmind.llm import LLMResponse, TokenCost


class FakeLLM:
    """
    Fake LLM for testing purposes.

    Returns predefined responses instead of calling real LLM APIs.
    """

    def __init__(self, responses: dict | None = None):
        self.responses = responses or {}
        self.call_history: list[dict] = []

    def get_config(self) -> LLMConfig:
        return LLMConfig(
            model_id="fake-model",
            base_url="https://fake.api/v1",
            api_key="fake-api-key",
        )

    def set_response(self, key: str, response: str | dict | BaseModel):
        if isinstance(response, BaseModel):
            self.responses[key] = response.model_dump_json()
        elif isinstance(response, dict):
            self.responses[key] = json.dumps(response)
        else:
            self.responses[key] = response

    def mock_call(self, llm, messages: list[dict], output_type: type, formatter_llm=None):
        self.call_history.append({"messages": messages, "output_type": output_type})

        response_key = self._extract_key(messages, output_type)

        if response_key in self.responses:
            content = self.responses[response_key]
        else:
            content = self._generate_default_response(output_type)

        if output_type is str:
            parsed_content = content
        elif output_type is dict:
            parsed_content = json.loads(content) if isinstance(content, str) else content
        else:
            parsed_content = output_type.model_validate_json(content)

        return LLMResponse(
            content=parsed_content,
            token_cost=TokenCost(prompt=10, completion=20, total=30),
            model="fake-model",
        )

    def _extract_key(self, messages: list[dict], output_type: type) -> str:
        all_content = " ".join([m.get("content", "") for m in messages])

        if output_type and hasattr(output_type, '__name__'):
            type_name = output_type.__name__
            if 'Plan' in type_name:
                return "plan"
            elif 'Validate' in type_name:
                return "validate"
            elif 'Evaluation' in type_name or 'Score' in type_name:
                return "score"
            elif 'Format' in type_name:
                return "format"

        if "执行计划" in all_content or "plan" in all_content.lower():
            return "plan"
        elif "校验" in all_content or "validate" in all_content.lower():
            return "validate"
        elif "评分" in all_content or "score" in all_content.lower():
            return "score"
        elif "格式化" in all_content or "format" in all_content.lower():
            return "format"
        else:
            return "execute"

    def _generate_default_response(self, output_type: type) -> str:
        if output_type is str:
            return "Fake LLM response"
        elif output_type is dict:
            return '{"result": "fake output"}'
        elif hasattr(output_type, 'model_json_schema'):
            schema = output_type.model_json_schema()
            properties = schema.get("properties", {})
            fake_data = {}
            for k, v in properties.items():
                prop_type = v.get("type", "string")
                if prop_type == "integer":
                    fake_data[k] = 8
                elif prop_type == "boolean":
                    fake_data[k] = True
                else:
                    fake_data[k] = "fake"
            return json.dumps(fake_data)
        return "{}"


def create_mock_llm(fake_llm: FakeLLM):
    """
    Create a mock context manager that patches the LLM call.

    Usage:
        fake = FakeLLM()
        fake.set_response("plan", '{"nodes": [...]}')

        with create_mock_llm(fake):
            agent = Agent(default_llm=fake.get_config())
            result = agent.run(task)
    """
    def mock_call(llm, messages, output_type, formatter_llm=None):
        return fake_llm.mock_call(llm, messages, output_type, formatter_llm)

    return patch('coralmind.worker.call_llm', side_effect=mock_call)


FakeLLMInstance = LLMConfig(
    model_id="fake-model",
    base_url="https://fake.api/v1",
    api_key="fake-api-key",
)
