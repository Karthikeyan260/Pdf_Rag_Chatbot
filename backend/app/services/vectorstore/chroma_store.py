import asyncio

import chromadb

from app.core.config import get_settings
from app.services.vectorstore.base import BaseVectorStore, VectorRecord, VectorSearchHit

settings = get_settings()


class ChromaVectorStore(BaseVectorStore):
    """Live adapter for Chroma — used for local development/tests.

    chromadb's Python client is synchronous; calls are pushed to a worker thread
    to keep the interface consistent with the async Qdrant adapter.
    """

    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection_name = f"{settings.qdrant_collection_prefix}_chunks"
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(self._collection_name)
        return self._collection

    async def ensure_collection(self, dimension: int) -> None:
        await asyncio.to_thread(self._get_collection)

    def _upsert(self, records: list[VectorRecord]) -> None:
        collection = self._get_collection()
        collection.upsert(
            ids=[r.id for r in records],
            embeddings=[r.vector for r in records],
            metadatas=[r.payload for r in records],
        )

    async def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        await asyncio.to_thread(self._upsert, records)

    def _search(
        self, query_vector: list[float], top_k: int, document_ids: list[str] | None
    ) -> list[VectorSearchHit]:
        collection = self._get_collection()
        where = {"document_id": {"$in": document_ids}} if document_ids else None
        result = collection.query(query_embeddings=[query_vector], n_results=top_k, where=where)
        hits: list[VectorSearchHit] = []
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        for id_, distance, metadata in zip(ids, distances, metadatas):
            # Chroma returns a distance (lower = closer); convert to a similarity-like score.
            hits.append(VectorSearchHit(id=id_, score=1.0 - distance, payload=metadata or {}))
        return hits

    async def search(
        self, query_vector: list[float], top_k: int, document_ids: list[str] | None = None
    ) -> list[VectorSearchHit]:
        return await asyncio.to_thread(self._search, query_vector, top_k, document_ids)

    def _delete_document(self, document_id: str) -> None:
        collection = self._get_collection()
        collection.delete(where={"document_id": document_id})

    async def delete_document(self, document_id: str) -> None:
        await asyncio.to_thread(self._delete_document, document_id)
