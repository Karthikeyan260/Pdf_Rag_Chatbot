from app.services.embeddings.base import BaseEmbeddingProvider


class VoyageEmbeddingProvider(BaseEmbeddingProvider):
    """Phase 2 stub — implement via the `voyageai` SDK (`settings.voyage_api_key`)."""

    def __init__(self) -> None:
        self.dimension = 1024

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Voyage embeddings provider is a Phase 2 stub")

    async def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("Voyage embeddings provider is a Phase 2 stub")
