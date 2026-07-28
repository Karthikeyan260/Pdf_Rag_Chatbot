from app.services.embeddings.base import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Phase 2 stub — implement via `openai.AsyncOpenAI().embeddings.create(model="text-embedding-3-large")`."""

    def __init__(self) -> None:
        self.dimension = 3072

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("OpenAI embeddings provider is a Phase 2 stub")

    async def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("OpenAI embeddings provider is a Phase 2 stub")
