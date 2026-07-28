from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    payload: dict = field(default_factory=dict)


@dataclass
class VectorSearchHit:
    id: str
    score: float
    payload: dict


class BaseVectorStore(ABC):
    """Common interface for the vector database layer.

    A single logical "collection" is used per deployment; multi-document and
    multi-PDF-chat scoping is done via a `document_id` filter on `payload`,
    not via one collection per document — this keeps hybrid search across many
    PDFs a single query instead of a fan-out.
    """

    @abstractmethod
    async def ensure_collection(self, dimension: int) -> None:
        """Create the collection if it doesn't already exist."""

    @abstractmethod
    async def upsert(self, records: list[VectorRecord]) -> None:
        """Insert or update vectors with their payload."""

    @abstractmethod
    async def search(
        self, query_vector: list[float], top_k: int, document_ids: list[str] | None = None
    ) -> list[VectorSearchHit]:
        """Dense similarity search, optionally scoped to a set of document ids."""

    @abstractmethod
    async def delete_document(self, document_id: str) -> None:
        """Remove all vectors belonging to a document."""
