from functools import lru_cache

from app.core.config import get_settings
from app.services.vectorstore.base import BaseVectorStore

settings = get_settings()


@lru_cache
def get_vector_store() -> BaseVectorStore:
    provider = settings.vectorstore_provider

    if provider == "qdrant":
        from app.services.vectorstore.qdrant_store import QdrantVectorStore

        return QdrantVectorStore()
    if provider == "chroma":
        from app.services.vectorstore.chroma_store import ChromaVectorStore

        return ChromaVectorStore()
    if provider == "pinecone":
        from app.services.vectorstore.pinecone_store import PineconeVectorStore

        return PineconeVectorStore()

    raise ValueError(f"Unknown vectorstore_provider: {provider}")
