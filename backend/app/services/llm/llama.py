from collections.abc import AsyncIterator

from app.services.llm.base import BaseLLMProvider, LLMMessage, LLMResponse


class LlamaProvider(BaseLLMProvider):
    """Phase 2 stub — correct interface, not yet wired to a local Llama server.

    To implement: call an OpenAI-compatible local server (e.g. Ollama, vLLM, TGI)
    at `settings.llama_base_url` via `httpx.AsyncClient`.
    """

    def __init__(self) -> None:
        pass

    async def generate(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> LLMResponse:
        raise NotImplementedError("Llama provider is a Phase 2 stub — implement via local inference server")

    async def stream(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> AsyncIterator[str]:
        raise NotImplementedError("Llama provider is a Phase 2 stub — implement via local inference server")
        yield  # pragma: no cover
