import re
import uuid

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.chunk import Chunk
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.vectorstore.base import BaseVectorStore

settings = get_settings()

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


async def dense_search_ranked(
    embedder: BaseEmbeddingProvider, store: BaseVectorStore, query: str, document_ids: list[str], top_k: int
) -> list[str]:
    vector = await embedder.embed_query(query)
    hits = await store.search(vector, top_k=top_k, document_ids=document_ids)
    return [hit.payload.get("chunk_id", hit.id) for hit in hits]


async def bm25_search_ranked(db: AsyncSession, query: str, document_ids: list[str], top_k: int) -> list[str]:
    # Rebuilds the BM25 index from scratch per call, scoped to the conversation's
    # document_ids. Fine for MVP corpus sizes; a persistent/incremental BM25 index
    # (or a sparse-vector engine) is the Phase 2 upgrade path for very large corpora.
    doc_uuids = [uuid.UUID(d) for d in document_ids]
    result = await db.execute(select(Chunk.id, Chunk.text).where(Chunk.document_id.in_(doc_uuids)))
    rows = result.all()
    if not rows:
        return []

    corpus_ids = [str(row.id) for row in rows]
    corpus_tokens = [_tokenize(row.text) for row in rows]
    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(_tokenize(query))

    ranked = sorted(zip(corpus_ids, scores), key=lambda pair: pair[1], reverse=True)
    return [chunk_id for chunk_id, score in ranked[:top_k] if score > 0]
