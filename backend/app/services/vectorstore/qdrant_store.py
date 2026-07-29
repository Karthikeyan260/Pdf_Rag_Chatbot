from qdrant_client import AsyncQdrantClient, models

from app.core.config import get_settings
from app.services.vectorstore.base import BaseVectorStore, VectorRecord, VectorSearchHit

settings = get_settings()


class QdrantVectorStore(BaseVectorStore):
    """Live adapter for Qdrant."""

    def __init__(self) -> None:
        self._client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
        self._collection = f"{settings.qdrant_collection_prefix}_chunks"

    async def ensure_collection(self, dimension: int) -> None:
        exists = await self._client.collection_exists(self._collection)
        if not exists:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
            )
            await self._client.create_payload_index(
                collection_name=self._collection,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

    async def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        points = [
            models.PointStruct(id=r.id, vector=r.vector, payload=r.payload)
            for r in records
        ]
        await self._client.upsert(collection_name=self._collection, points=points)

    async def search(
        self, query_vector: list[float], top_k: int, document_ids: list[str] | None = None
    ) -> list[VectorSearchHit]:
        query_filter = None
        if document_ids:
            query_filter = models.Filter(
                must=[models.FieldCondition(key="document_id", match=models.MatchAny(any=document_ids))]
            )
        results = await self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )
        return [
            VectorSearchHit(id=str(point.id), score=point.score, payload=point.payload or {})
            for point in results.points
        ]

    async def delete_document(self, document_id: str) -> None:
        if not await self._client.collection_exists(self._collection):
            return
        await self._client.delete(
            collection_name=self._collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
                )
            ),
        )
