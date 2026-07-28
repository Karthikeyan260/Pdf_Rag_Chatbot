from collections.abc import AsyncIterator

from app.services.llm.base import BaseLLMProvider, LLMMessage, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """Phase 2 stub — correct interface, not yet wired to the OpenAI SDK.

    To implement: use `openai.AsyncOpenAI(api_key=settings.openai_api_key)` with
    `chat.completions.create(..., stream=True)` for `stream()`.
    """

    def __init__(self) -> None:
        pass

    async def generate(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> LLMResponse:
        raise NotImplementedError("OpenAI provider is a Phase 2 stub — implement via openai SDK")

    async def stream(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> AsyncIterator[str]:
        raise NotImplementedError("OpenAI provider is a Phase 2 stub — implement via openai SDK")
        yield  # pragma: no cover — makes this an async generator for type-checkers
