from app.services.vectorstore.base import BaseVectorStore, VectorRecord, VectorSearchHit


class PineconeVectorStore(BaseVectorStore):
    """Phase 2 stub — implement via the `pinecone` SDK (`settings.pinecone_api_key`/`pinecone_environment`)."""

    def __init__(self) -> None:
        pass

    async def ensure_collection(self, dimension: int) -> None:
        raise NotImplementedError("Pinecone vector store is a Phase 2 stub")

    async def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError("Pinecone vector store is a Phase 2 stub")

    async def search(
        self, query_vector: list[float], top_k: int, document_ids: list[str] | None = None
    ) -> list[VectorSearchHit]:
        raise NotImplementedError("Pinecone vector store is a Phase 2 stub")

    async def delete_document(self, document_id: str) -> None:
        raise NotImplementedError("Pinecone vector store is a Phase 2 stub")
