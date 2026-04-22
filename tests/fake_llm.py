import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

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
        self._call_count: dict[str, int] = {}

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

    def set_responses(self, key: str, responses: list[str | dict | BaseModel]):
        """Set multiple responses for the same key, returned in order"""
        self.responses[f"{key}_list"] = [
            r.model_dump_json() if isinstance(r, BaseModel) else
            json.dumps(r) if isinstance(r, dict) else r
            for r in responses
        ]
        self._call_count[key] = 0

    def mock_call(self, llm, messages: list[dict], output_type: type):
        self.call_history.append({"messages": messages, "output_type": output_type})

        response_key = self._extract_key(messages, output_type)

        list_key = f"{response_key}_list"
        if list_key in self.responses:
            idx = self._call_count.get(response_key, 0)
            if idx < len(self.responses[list_key]):
                content = self.responses[list_key][idx]
                self._call_count[response_key] = idx + 1
            else:
                content = self._generate_default_response(output_type)
        elif response_key in self.responses:
            content = self.responses[response_key]
        else:
            content = self._generate_default_response(output_type)

        if output_type is str:
            parsed_content = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        else:
            if isinstance(content, str):
                parsed_content = output_type.model_validate_json(content)
            else:
                parsed_content = output_type.model_validate(content)

        return LLMResponse(
            content=parsed_content,
            token_cost=TokenCost(prompt=10, completion=20, total=30),
            model="fake-model",
        )

    def _extract_key(self, messages: list[dict], output_type: type) -> str:
        all_content = " ".join([m.get("content", "") for m in messages])

        if output_type and hasattr(output_type, '__name__'):
            type_name = output_type.__name__
            if 'Plan' in type_name and 'Validation' not in type_name:
                return "plan"
            elif 'Validate' in type_name:
                return "validate"
            elif 'Evaluation' in type_name or 'Score' in type_name:
                return "score"
            elif 'TreeNode' in type_name:
                return "tree"

        if output_type is str:
            if "Execution Plan Standard" in all_content or "Create a detailed execution plan" in all_content:
                return "plan"
            if "Validation Task" in all_content or "validate whether" in all_content:
                return "validate"
            if "Evaluation Standard" in all_content or "evaluation result" in all_content:
                return "score"
            if "Output fields" in all_content or "Return the final result directly" in all_content:
                return "execute"
            if "Original Task Output Requirements" in all_content:
                return "format"
            if "格式化" in all_content or "format" in all_content.lower():
                return "format"
            if "校验" in all_content or "validate" in all_content.lower():
                return "validate"
            if "评分" in all_content or "score" in all_content.lower():
                return "score"
            return "execute"

        if "执行计划" in all_content or "plan" in all_content.lower():
            return "plan"
        elif "校验" in all_content or "validate" in all_content.lower():
            return "validate"
        elif "评分" in all_content or "score" in all_content.lower():
            return "score"
        else:
            return "execute"

    def _generate_default_response(self, output_type: type) -> str:
        if output_type is str:
            return "Fake LLM response"
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
                elif prop_type == "array":
                    fake_data[k] = []
                else:
                    fake_data[k] = "fake"
            return json.dumps(fake_data)
        return "{}"


@contextmanager
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
    def mock_create(model, messages, max_tokens, **kwargs):
        if 'response_format' in kwargs:
            response_format = kwargs['response_format']
            if response_format.get('type') == 'json_schema':
                json_schema = response_format.get('json_schema', {})
                schema = json_schema.get('schema', {})
                schema_name = json_schema.get('name', '')

                response_key = _extract_key_from_schema_name(schema_name, messages)
                list_key = f"{response_key}_list"

                if list_key in fake_llm.responses:
                    idx = fake_llm._call_count.get(response_key, 0)
                    if idx < len(fake_llm.responses[list_key]):
                        content = fake_llm.responses[list_key][idx]
                        fake_llm._call_count[response_key] = idx + 1
                    else:
                        content = _generate_default_from_schema(schema)
                elif response_key in fake_llm.responses:
                    content = fake_llm.responses[response_key]
                else:
                    content = _generate_default_from_schema(schema)

                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = content
                mock_response.usage.prompt_tokens = 10
                mock_response.usage.completion_tokens = 20
                mock_response.usage.total_tokens = 30
                return mock_response

        fake_config = LLMConfig(
            model_id=model,
            base_url="https://fake.api/v1",
            api_key="fake-key"
        )
        response = fake_llm.mock_call(fake_config, messages, str)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = response.content if isinstance(response.content, str) else response.content.model_dump_json()
        mock_response.usage.prompt_tokens = response.token_cost.prompt
        mock_response.usage.completion_tokens = response.token_cost.completion
        mock_response.usage.total_tokens = response.token_cost.total
        return mock_response

    with patch('coralmind.llm.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = mock_create
        yield mock_openai


def _extract_key_from_schema_name(schema_name: str, messages: list[dict]) -> str:
    """Extract response key from schema name and messages"""
    all_content = " ".join([m.get("content", "") for m in messages])

    if 'Plan' in schema_name and 'Validation' not in schema_name:
        return "plan"
    elif 'Validate' in schema_name:
        return "validate"
    elif 'Evaluation' in schema_name or 'Score' in schema_name:
        return "score"
    elif 'TreeNode' in schema_name:
        return "tree"
    elif 'DynamicOutput' in schema_name or 'Output' in schema_name:
        return "execute"
    elif 'DynamicModel' in schema_name:
        return "format"

    if "Execution Plan Standard" in all_content or "Create a detailed execution plan" in all_content:
        return "plan"
    if "Validation Task" in all_content or "validate whether" in all_content:
        return "validate"
    if "Evaluation Standard" in all_content or "evaluation result" in all_content:
        return "score"
    if "Output fields" in all_content or "Return the final result directly" in all_content:
        return "execute"
    if "Original Output" in all_content or "Transform the original output" in all_content:
        return "format"

    return "execute"


def _generate_default_from_schema(schema: dict) -> str:
    """Generate a default response from JSON schema"""
    properties = schema.get("properties", {})
    fake_data = {}
    for k, v in properties.items():
        prop_type = v.get("type", "string")
        if prop_type == "integer":
            fake_data[k] = 8
        elif prop_type == "boolean":
            fake_data[k] = True
        elif prop_type == "array":
            fake_data[k] = []
        elif prop_type == "number":
            fake_data[k] = 0.5
        else:
            fake_data[k] = "fake"
    return json.dumps(fake_data)


FakeLLMInstance = LLMConfig(
    model_id="fake-model",
    base_url="https://fake.api/v1",
    api_key="fake-api-key",
)
