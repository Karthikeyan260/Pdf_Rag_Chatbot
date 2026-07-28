from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    dimension: int

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of chunk texts for indexing."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string for retrieval."""
