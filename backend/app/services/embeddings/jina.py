from app.services.embeddings.base import BaseEmbeddingProvider


class JinaEmbeddingProvider(BaseEmbeddingProvider):
    """Phase 2 stub — implement via Jina AI Embeddings v3 REST API (`settings.jina_api_key`)."""

    def __init__(self) -> None:
        self.dimension = 1024

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Jina embeddings provider is a Phase 2 stub")

    async def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("Jina embeddings provider is a Phase 2 stub")
