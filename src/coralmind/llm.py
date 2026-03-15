from __future__ import annotations

import logging
from typing import Generic, TypeVar, cast, overload

from openai import OpenAI
from pydantic import BaseModel, Field

from .exceptions import ConfigurationError, LLMError
from .prompts import PromptTemplateName, build_prompt

logger = logging.getLogger(__name__)

__all__ = ["LLMConfig", "LLMResponse", "TokenCost", "call_llm", "as_user_messages", "build_user_message", "build_assistant_message", "get_embedding"]


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
def call_llm(llm: LLMConfig, messages: list[dict[str, str]], output_type: type[BaseModel],
             formatter_llm: LLMConfig | None = None) -> LLMResponse[BaseModel]: ...


def call_llm(
        llm: LLMConfig,
        messages: list[dict[str, str]],
        output_type: type[str] | type[BaseModel],
        formatter_llm: LLMConfig | None = None
) -> LLMResponse[str] | LLMResponse[BaseModel]:
    """Call LLM"""

    raw_response = _call_llm(llm, messages)
    content = raw_response.content

    if output_type is str:
        return raw_response

    fixed_content = _quick_fix_object_json(content)
    if not formatter_llm:
        formatter_llm = llm

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
    prompt = build_prompt(
        PromptTemplateName.FIX_MODEL_VALIDATION,
        json_string=json_string,
        error_msg=error_msg,
        schema=schema
    )

    fixed_json = _call_llm(llm, [build_user_message(prompt)]).content
    return _quick_fix_object_json(fixed_json)


def get_embedding(llm: LLMConfig, text: str) -> list[float]:
    """
    Get embedding vector for text using embedding API.

    Args:
        llm: LLM configuration (uses model_id as embedding model)
        text: Text to embed

    Returns:
        Embedding vector as list of floats
    """
    client = OpenAI(
        api_key=llm.api_key,
        base_url=llm.base_url,
        timeout=llm.timeout,
    )

    logger.debug(f"Getting embedding for text (length={len(text)}) using model: {llm.model_id}")

    response = client.embeddings.create(
        model=llm.model_id,
        input=text,
    )

    embedding = response.data[0].embedding
    logger.debug(f"Embedding obtained, dimension={len(embedding)}")
    return embedding
