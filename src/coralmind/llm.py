from __future__ import annotations

import json
import logging
from typing import Any, Generic, TypeVar, cast, overload

from openai import OpenAI
from pydantic import BaseModel, Field

from .exceptions import ConfigurationError, LLMError

logger = logging.getLogger(__name__)

__all__ = ["LLMConfig", "LLMResponse", "TokenCost", "call_llm", "as_user_messages", "build_user_message", "build_assistant_message"]


class LLMConfig(BaseModel):
    """LLM Configuration"""
    model_id: str
    base_url: str
    api_key: str
    max_tokens: int = 8196
    timeout: float | None = Field(default=None, description="Request timeout in seconds, None means no timeout")


class TokenCost(BaseModel):
    """Token Cost"""
    prompt: int
    completion: int
    total: int

    def __add__(self, other: TokenCost) -> TokenCost:
        return TokenCost(
            prompt=self.prompt + other.prompt,
            completion=self.completion + other.completion,
            total=self.total + other.total,
        )


T = TypeVar("T")


class LLMResponse(BaseModel, Generic[T]):
    """Response from LLM"""
    content: T
    token_cost: TokenCost
    model: str


def build_user_message(message: str) -> dict[str, str]:
    return {"role": "user", "content": message}


def build_assistant_message(message: str) -> dict[str, str]:
    return {"role": "assistant", "content": message}


def as_user_messages(messages: list[str]) -> list[dict[str, str]]:
    return [build_user_message(m) for m in messages]


@overload
def call_llm(llm: LLMConfig, messages: list[dict[str, str]], output_type: type[str],
             formatter_llm: LLMConfig | None = None) -> LLMResponse[str]: ...


@overload
def call_llm(llm: LLMConfig, messages: list[dict[str, str]], output_type: type[dict[Any, Any]],
             formatter_llm: LLMConfig | None = None) -> LLMResponse[dict[str, str]]: ...


@overload
def call_llm(llm: LLMConfig, messages: list[dict[str, str]], output_type: type[BaseModel],
             formatter_llm: LLMConfig | None = None) -> LLMResponse[BaseModel]: ...


def call_llm(
        llm: LLMConfig,
        messages: list[dict[str, str]],
        output_type: type[str] | type[dict[Any, Any]] | type[BaseModel],
        formatter_llm: LLMConfig | None = None
) -> LLMResponse[str] | LLMResponse[dict[str, str]] | LLMResponse[BaseModel]:
    """Call LLM"""

    raw_response = _call_llm(llm, messages)
    content = raw_response.content

    if output_type is str:
        return raw_response

    fixed_content = _quick_fix_object_json(content)
    if not formatter_llm:
        formatter_llm = llm

    if output_type is dict:
        dict_content = _to_dict(formatter_llm, fixed_content)
        return LLMResponse(content=dict_content, token_cost=raw_response.token_cost, model=raw_response.model)
    else:
        model_content = _to_model(formatter_llm, fixed_content, cast(type[BaseModel], output_type))
        return LLMResponse(content=model_content, token_cost=raw_response.token_cost, model=raw_response.model)


def _call_llm(llm: LLMConfig, messages: list[dict[str, str]]) -> LLMResponse[str]:
    client = OpenAI(
        api_key=llm.api_key,
        base_url=llm.base_url,
        timeout=llm.timeout,
    )
    if len(messages) == 0:
        raise ConfigurationError("LLM messages cannot be empty", parameter="messages")
    model_name = llm.model_id
    logger.debug(f'messages: {messages}')
    logger.info(f'chat completion created | model: {model_name}')
    completion = client.chat.completions.create(model=model_name, messages=messages, max_tokens=llm.max_tokens)  # type: ignore[arg-type]
    usage = completion.usage
    token_cost = TokenCost(
        prompt=usage.prompt_tokens if usage else 0,
        completion=usage.completion_tokens if usage else 0,
        total=usage.total_tokens if usage else 0,
    )
    if usage:
        logger.info(f'receiving done | model: {model_name} | '
                    f'TokenCost: completion {usage.completion_tokens}, prompt {usage.prompt_tokens}, total {usage.total_tokens}')
    else:
        logger.info(f'receiving done | model: {model_name}')
    content = completion.choices[0].message.content
    if content is None:
        raise LLMError("LLM returned empty content", model=model_name)
    logger.debug(f'response: {content}')
    return LLMResponse(content=content, token_cost=token_cost, model=model_name)


def _quick_fix_object_json(json_str: str) -> str:
    """Quick fix for common JSON string errors"""
    left_index = json_str.find('{')
    right_index = json_str.rfind('}')
    return json_str[left_index: right_index + 1] if (-1 < left_index < right_index) else json_str


def _to_dict(llm: LLMConfig, json_string: str, max_retries: int = 2) -> dict[str, str]:
    """
    Convert JSON string to dict[str, str] with retry mechanism.

    When structure is incorrect (e.g., nested objects, arrays),
    use LLM to fix it with detailed error information.
    """
    current_json = json_string

    for attempt in range(max_retries + 1):
        try:
            obj = json.loads(current_json)

            if not isinstance(obj, dict):
                error_msg = f"Expected JSON object (dict), got {type(obj).__name__}. The output must be a flat dictionary with string values only."
                if attempt < max_retries:
                    logger.debug(f"Structure error (attempt {attempt + 1}): {error_msg}")
                    current_json = _fix_dict_structure_by_llm(llm, current_json, error_msg)
                    continue
                raise LLMError(error_msg, model=llm.model_id)

            if not _is_dict_str_str(obj):
                non_str_items = [(k, type(v).__name__) for k, v in obj.items() if not isinstance(v, str)]
                error_msg = f"Expected dict[str, str], but some values are not strings: {non_str_items}. All values must be plain strings, not arrays or nested objects."
                if attempt < max_retries:
                    logger.debug(f"Structure error (attempt {attempt + 1}): {error_msg}")
                    current_json = _fix_dict_structure_by_llm(llm, current_json, error_msg)
                    continue
                raise LLMError(error_msg, model=llm.model_id)

            return cast(dict[str, str], obj)

        except json.JSONDecodeError as e:
            if attempt < max_retries:
                logger.debug(f"JSON parse error (attempt {attempt + 1}): {e}")
                current_json = _fix_dict_structure_by_llm(llm, current_json, f"JSON parse error: {e}")
                continue
            raise LLMError(f"Failed to parse JSON after {max_retries} retries: {e}", model=llm.model_id) from e

    raise LLMError(f"Failed to get valid dict[str, str] after {max_retries} retries", model=llm.model_id)


def _fix_dict_structure_by_llm(llm: LLMConfig, json_string: str, error_msg: str) -> str:
    """
    Use LLM to fix JSON structure errors for dict[str, str] conversion.

    Args:
        llm: LLM configuration
        json_string: The problematic JSON string
        error_msg: Description of the error

    Returns:
        Fixed JSON string that should be a dict with string values
    """
    prompt = f"""The following JSON has a structure error:

```json
{json_string}
```

Error: {error_msg}

Please fix the JSON and return ONLY the corrected JSON. Requirements:
1. The output must be a JSON object (dict), not an array
2. All values must be strings (str), not arrays or nested objects
3. If you need to represent multiple items, use newline-separated strings or JSON-stringified strings
4. Do not include any markdown formatting or explanations, just the raw JSON"""

    fixed_json = _call_llm(llm, [build_user_message(prompt)]).content
    return _quick_fix_object_json(fixed_json)


def _is_dict_str_str(d: dict) -> bool:
    return all(isinstance(k, str) and isinstance(v, str) for k, v in d.items())


def _to_model(llm: LLMConfig, json_string: str, model_type: type[BaseModel], max_retries: int = 2) -> BaseModel:
    """
    Convert JSON string to Pydantic model with retry mechanism.

    When validation fails, use LLM to fix it with detailed error information.
    """
    current_json = json_string

    for attempt in range(max_retries + 1):
        try:
            return model_type.model_validate_json(current_json)
        except Exception as e:
            if attempt < max_retries:
                logger.debug(f"Model validation error (attempt {attempt + 1}): {e}")
                current_json = _fix_model_json_by_llm(llm, current_json, model_type, str(e))
                continue
            raise LLMError(f"Failed to validate {model_type.__name__} after {max_retries} retries: {e}", model=llm.model_id) from e

    raise LLMError(f"Failed to get valid {model_type.__name__} after {max_retries} retries", model=llm.model_id)


def _fix_model_json_by_llm(llm: LLMConfig, json_string: str, model_type: type[BaseModel], error_msg: str) -> str:
    """
    Use LLM to fix JSON structure errors for Pydantic model validation.

    Args:
        llm: LLM configuration
        json_string: The problematic JSON string
        model_type: Target Pydantic model type
        error_msg: Description of the validation error

    Returns:
        Fixed JSON string that should conform to the model schema
    """
    schema = model_type.model_json_schema()
    prompt = f"""The following JSON has validation errors:

```json
{json_string}
```

Error: {error_msg}

Target schema:
```json_schema
{schema}
```

Please fix the JSON and return ONLY the corrected JSON. Requirements:
1. The output must conform to the target schema exactly
2. All required fields must be present
3. Field types must match the schema definitions
4. Do not include any markdown formatting or explanations, just the raw JSON"""

    fixed_json = _call_llm(llm, [build_user_message(prompt)]).content
    return _quick_fix_object_json(fixed_json)
