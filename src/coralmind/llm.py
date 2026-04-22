from __future__ import annotations

import logging
from typing import Generic, TypeVar, cast, overload

from openai import OpenAI
from pydantic import BaseModel, Field

from .exceptions import ConfigurationError, LLMError

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
def call_llm(llm: LLMConfig, messages: list[dict[str, str]], output_type: type[str]) -> LLMResponse[str]: ...


@overload
def call_llm(llm: LLMConfig, messages: list[dict[str, str]], output_type: type[BaseModel]) -> LLMResponse[BaseModel]: ...


def call_llm(
        llm: LLMConfig,
        messages: list[dict[str, str]],
        output_type: type[str] | type[BaseModel],
) -> LLMResponse[str] | LLMResponse[BaseModel]:
    """
    Call LLM with optional structured output.

    For BaseModel output_type, uses OpenAI's json_schema response_format
    to guarantee valid JSON output conforming to the model schema.
    """
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

    if output_type is str:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=llm.max_tokens,
        )
    else:
        model_type = cast(type[BaseModel], output_type)
        completion = client.chat.completions.create(  # type: ignore[call-overload]
            model=model_name,
            messages=messages,
            max_tokens=llm.max_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": model_type.__name__,
                    "schema": model_type.model_json_schema(),
                    "strict": False,
                }
            }
        )

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

    if output_type is str:
        return LLMResponse(content=content, token_cost=token_cost, model=model_name)

    model_type = cast(type[BaseModel], output_type)
    try:
        model_content = model_type.model_validate_json(content)
    except Exception as e:
        raise LLMError(f"Failed to validate {model_type.__name__}: {e}", model=model_name) from e

    return LLMResponse(content=model_content, token_cost=token_cost, model=model_name)


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
