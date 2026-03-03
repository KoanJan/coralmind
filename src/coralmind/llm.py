import json
import logging
from typing import TypeVar, cast, overload

from openai import OpenAI
from pydantic import BaseModel, Field

from .exceptions import ConfigurationError, LLMError

logger = logging.getLogger(__name__)

__all__ = ["LLMConfig", "call_llm", "as_user_messages", "build_user_message", "build_assistant_message"]


class LLMConfig(BaseModel):
    """LLM Configuration"""
    model_id: str
    base_url: str
    api_key: str
    max_tokens: int = 8196
    timeout: float | None = Field(default=None, description="Request timeout in seconds, None means no timeout")


T = TypeVar("T", str, dict, BaseModel)


def build_user_message(message: str) -> dict[str, str]:
    return {"role": "user", "content": message}


def build_assistant_message(message: str) -> dict[str, str]:
    return {"role": "assistant", "content": message}


def as_user_messages(messages: list[str]) -> list[dict[str, str]]:
    return [build_user_message(m) for m in messages]


@overload
def call_llm(llm: LLMConfig, messages: list[dict[str, str]], output_type: type[str],
             formatter_llm: LLMConfig | None = None) -> str: ...


@overload
def call_llm(llm: LLMConfig, messages: list[dict[str, str]], output_type: type[dict],
             formatter_llm: LLMConfig | None = None) -> dict[str, str]: ...


@overload
def call_llm(llm: LLMConfig, messages: list[dict[str, str]], output_type: type[BaseModel],
             formatter_llm: LLMConfig | None = None) -> BaseModel: ...


def call_llm(
        llm: LLMConfig,
        messages: list[dict[str, str]],
        output_type: type[str] | type[dict] | type[BaseModel],
        formatter_llm: LLMConfig | None = None
) -> str | dict[str, str] | BaseModel:
    """Call LLM"""

    content = _call_llm(llm, messages)

    if output_type is str:
        return content
    content = _quick_fix_object_json(content)
    if not formatter_llm:
        formatter_llm = llm
    if output_type is dict:
        return _to_dict(formatter_llm, content)
    else:
        return _to_model(formatter_llm, content, output_type)


def _call_llm(llm: LLMConfig, messages: list[dict[str, str]]) -> str:
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
    if usage:
        logger.info(f'receiving done | model: {model_name} | '
                    f'TokenCost: completion {usage.completion_tokens}, prompt {usage.prompt_tokens}, total {usage.total_tokens}')
    else:
        logger.info(f'receiving done | model: {model_name}')
    content = completion.choices[0].message.content
    if content is None:
        raise LLMError("LLM returned empty content", model=model_name)
    logger.debug(f'response: {content}')
    return content


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
        return cast(dict[str, str], obj)
    except LLMError:
        raise
    except Exception as e:
        logger.debug(f"JSON parsing failed, attempting LLM fix: {e}")
        return _to_dict_by_llm(llm, json_string)


def _to_dict_by_llm(llm: LLMConfig, json_string: str) -> dict[str, str]:
    """Use LLM to intelligently fix JSON string errors"""
    prompt = f"{json_string}\n\nThe JSON above has formatting issues. Fix it and return a valid JSON directly (the outermost layer must be a dictionary, not a list). Do not include any non-JSON decorations such as ``` symbols or other language descriptions."
    fixed_json_string = _call_llm(llm, [build_user_message(prompt)])
    return cast(dict[str, str], json.loads(fixed_json_string))


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
    fixed_json_string = _call_llm(llm, [build_user_message(prompt)])
    return model_type.model_validate_json(fixed_json_string)
