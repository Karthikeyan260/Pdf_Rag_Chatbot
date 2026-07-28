import asyncio

from app.core.config import get_settings
from app.services.embeddings.base import BaseEmbeddingProvider

settings = get_settings()


class BGEM3Provider(BaseEmbeddingProvider):
    """Live adapter for BAAI/bge-m3 dense embeddings via FlagEmbedding.

    The model is loaded lazily and once per process (BGEM3FlagModel is expensive to
    construct), then reused for every embed call. FlagEmbedding's API is synchronous,
    so calls are pushed to a worker thread to keep the async interface non-blocking.
    """

    def __init__(self) -> None:
        self.dimension = settings.embedding_dimension
        self._model = None

    def _get_model(self):
        if self._model is None:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(settings.bge_m3_model_name, use_fp16=True)
        return self._model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        output = model.encode(texts, return_dense=True, return_sparse=False, return_colbert_vecs=False)
        return [vec.tolist() for vec in output["dense_vecs"]]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._encode, texts)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await asyncio.to_thread(self._encode, [text])
        return vectors[0]
