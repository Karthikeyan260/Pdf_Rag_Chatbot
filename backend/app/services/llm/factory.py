from functools import lru_cache

from app.core.config import get_settings
from app.services.llm.base import BaseLLMProvider

settings = get_settings()


@lru_cache
def get_llm_provider() -> BaseLLMProvider:
    provider = settings.llm_provider

    if provider == "gemini":
        from app.services.llm.gemini import GeminiProvider

        return GeminiProvider()
    if provider == "openai":
        from app.services.llm.openai_provider import OpenAIProvider

        return OpenAIProvider()
    if provider == "claude":
        from app.services.llm.claude import ClaudeProvider

        return ClaudeProvider()
    if provider == "llama":
        from app.services.llm.llama import LlamaProvider

        return LlamaProvider()

    raise ValueError(f"Unknown llm_provider: {provider}")
