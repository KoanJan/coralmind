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


def _to_dict(llm: LLMConfig, json_string: str) -> dict[str, str]:
    logger.debug("_to_dict called")
    try:
        obj = json.loads(json_string)
        if not isinstance(obj, dict):
            raise LLMError(
                f"Expected JSON object (dict), got {type(obj).__name__}. "
                f"LLM returned incorrect JSON structure.",
                model=llm.model_id
            )
        if not _is_dict_str_str(obj):
            raise LLMError(
                "Expected dict[str, str], but some keys or values are not strings. "
                "LLM returned incorrect JSON structure.",
                model=llm.model_id
            )
        return cast(dict[str, str], obj)
    except LLMError:
        raise
    except Exception as e:
        logger.debug(f"JSON parsing failed, attempting LLM fix: {e}")
        return _to_dict_by_llm(llm, json_string)


def _to_dict_by_llm(llm: LLMConfig, json_string: str) -> dict[str, str]:
    """Use LLM to intelligently fix JSON string errors"""
    prompt = f"{json_string}\n\nThe JSON above has formatting issues. Fix it and return a valid JSON directly (the outermost layer must be a dictionary, not a list). Do not include any non-JSON decorations such as ``` symbols or other language descriptions."
    fixed_json_string = _call_llm(llm, [build_user_message(prompt)]).content
    obj = json.loads(fixed_json_string)
    if not _is_dict_str_str(obj):
        raise LLMError(
            "Expected dict[str, str], but some keys or values are not strings. "
            "LLM returned incorrect JSON structure.",
            model=llm.model_id
        )
    return cast(dict[str, str], obj)


def _is_dict_str_str(d: dict) -> bool:
    return all(isinstance(k, str) and isinstance(v, str) for k, v in d.items())


def _to_model(llm: LLMConfig, json_string: str, model_type: type[BaseModel]) -> BaseModel:
    try:
        return model_type.model_validate_json(json_string)
    except Exception as e:
        logger.debug(f"JSON parsing failed, attempting LLM fix: {e}")
        return _to_model_by_llm(llm, json_string, model_type)


def _to_model_by_llm(llm: LLMConfig, json_string: str, model_type: type[BaseModel]) -> BaseModel:
    """Use LLM to intelligently fix JSON string errors"""
    schema = model_type.model_json_schema()
    prompt = f"{json_string}\n\nThe JSON above has formatting issues. Fix it and return a valid JSON directly, strictly following this JSONSchema: ```json_schema\n{schema}\n```\n\nDo not include any non-JSON decorations such as ``` symbols or other language descriptions."
    fixed_json_string = _call_llm(llm, [build_user_message(prompt)]).content
    return model_type.model_validate_json(fixed_json_string)
