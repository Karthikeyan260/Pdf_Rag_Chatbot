from functools import lru_cache

from app.core.config import get_settings
from app.services.embeddings.base import BaseEmbeddingProvider

settings = get_settings()


@lru_cache
def get_embedding_provider() -> BaseEmbeddingProvider:
    provider = settings.embedding_provider

    if provider == "bge_m3":
        from app.services.embeddings.bge_m3 import BGEM3Provider

        return BGEM3Provider()
    if provider == "jina":
        from app.services.embeddings.jina import JinaEmbeddingProvider

        return JinaEmbeddingProvider()
    if provider == "voyage":
        from app.services.embeddings.voyage import VoyageEmbeddingProvider

        return VoyageEmbeddingProvider()
    if provider == "openai":
        from app.services.embeddings.openai_embed import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider()

    raise ValueError(f"Unknown embedding_provider: {provider}")
