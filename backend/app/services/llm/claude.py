from collections.abc import AsyncIterator

from app.services.llm.base import BaseLLMProvider, LLMMessage, LLMResponse


class ClaudeProvider(BaseLLMProvider):
    """Phase 2 stub — correct interface, not yet wired to the Anthropic SDK.

    To implement: use `anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)`
    with `messages.stream(...)` for `stream()`.
    """

    def __init__(self) -> None:
        pass

    async def generate(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> LLMResponse:
        raise NotImplementedError("Claude provider is a Phase 2 stub — implement via anthropic SDK")

    async def stream(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> AsyncIterator[str]:
        raise NotImplementedError("Claude provider is a Phase 2 stub — implement via anthropic SDK")
        yield  # pragma: no cover
