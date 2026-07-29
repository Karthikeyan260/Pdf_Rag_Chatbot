import asyncio

from app.core.config import get_settings
from app.services.embeddings.base import BaseEmbeddingProvider

settings = get_settings()


class BGEM3Provider(BaseEmbeddingProvider):
    """Live adapter for BGE-family dense embeddings via sentence-transformers.

    Despite the class name (kept for config/factory compatibility —
    EMBEDDING_PROVIDER=bge_m3), this loads whatever model is set in
    `BGE_M3_MODEL_NAME`, not necessarily the full BAAI/bge-m3 checkpoint.
    BAAI/bge-m3 itself needs ~2-3GB RAM to load and won't fit on
    memory-constrained hosts (e.g. Railway's 1GB plan tier) alongside
    FastAPI/Celery — BAAI/bge-small-en-v1.5 (384-dim, ~130MB) or
    BAAI/bge-base-en-v1.5 (768-dim, ~440MB) are safe substitutes for those
    environments. Whichever model is configured, `EMBEDDING_DIMENSION` must
    match its actual output dimension or the vector store's collection will
    reject inserts.

    sentence-transformers' API is synchronous, so calls are pushed to a
    worker thread to keep the async interface non-blocking. The model is
    loaded lazily and once per process, then reused for every embed call.
    """

    def __init__(self) -> None:
        self.dimension = settings.embedding_dimension
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(settings.bge_m3_model_name)
        return self._model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return [vec.tolist() for vec in vectors]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._encode, texts)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await asyncio.to_thread(self._encode, [text])
        return vectors[0]
