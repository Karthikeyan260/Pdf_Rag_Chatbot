from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class BaseLLMProvider(ABC):
    """Common interface every LLM provider adapter must implement.

    Keeping generate/stream/embed-adjacent concerns separate from the embeddings
    provider lets a multimodal-capable LLM (e.g. Gemini) still be swapped independently
    of the embedding model.
    """

    @abstractmethod
    async def generate(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> LLMResponse:
        """Return a full, non-streamed completion."""

    @abstractmethod
    async def stream(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> AsyncIterator[str]:
        """Yield completion text incrementally for streaming chat responses."""
