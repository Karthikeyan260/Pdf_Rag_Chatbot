import uuid
from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.chunk import Chunk
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.llm.base import BaseLLMProvider
from app.services.reranker.base import BaseRerankerProvider, RerankCandidate
from app.services.retrieval.compression import compress_context
from app.services.retrieval.hybrid_search import bm25_search_ranked, dense_search_ranked
from app.services.retrieval.merge import reciprocal_rank_fusion
from app.services.retrieval.multi_query import generate_query_variants
from app.services.retrieval.query_rewriter import rewrite_query
from app.services.vectorstore.base import BaseVectorStore

settings = get_settings()

MAX_RERANK_CANDIDATES = 40


class RetrievalState(TypedDict, total=False):
    question: str
    history: list[dict]
    document_ids: list[str]
    rewritten_query: str
    query_variants: list[str]
    fused_ids: list[str]
    ranked_chunks: list[dict]
    context: str
    chunks: list[dict]
    confidence: float


class RetrievalResult(TypedDict):
    rewritten_query: str
    context: str
    chunks: list[dict]
    confidence: float


def build_retrieval_graph(
    llm: BaseLLMProvider,
    embedder: BaseEmbeddingProvider,
    store: BaseVectorStore,
    reranker: BaseRerankerProvider,
    db: AsyncSession,
):
    """Wires the query-rewrite -> multi-query -> hybrid-retrieve -> rerank -> compress
    pipeline as a LangGraph state machine. Built per-request because it closes over
    the request's AsyncSession — cheap, since the graph itself holds no heavy state.
    """

    async def node_rewrite(state: RetrievalState) -> dict:
        rewritten = await rewrite_query(llm, state["question"], state.get("history", []))
        return {"rewritten_query": rewritten}

    async def node_expand(state: RetrievalState) -> dict:
        variants = await generate_query_variants(llm, state["rewritten_query"], settings.multi_query_count)
        return {"query_variants": variants}

    async def node_retrieve(state: RetrievalState) -> dict:
        document_ids = state["document_ids"]
        all_queries = [state["rewritten_query"], *state.get("query_variants", [])]

        dense_lists = [
            await dense_search_ranked(embedder, store, q, document_ids, settings.hybrid_dense_top_k)
            for q in all_queries
        ]
        bm25_list = await bm25_search_ranked(db, state["rewritten_query"], document_ids, settings.hybrid_bm25_top_k)

        fused = reciprocal_rank_fusion([*dense_lists, bm25_list])
        fused_ids = [chunk_id for chunk_id, _ in fused[:MAX_RERANK_CANDIDATES]]
        return {"fused_ids": fused_ids}

    async def node_rerank(state: RetrievalState) -> dict:
        fused_ids = state.get("fused_ids", [])
        if not fused_ids:
            return {"chunks": [], "confidence": 0.0}

        chunk_uuids = [uuid.UUID(cid) for cid in fused_ids]
        result = await db.execute(select(Chunk).where(Chunk.id.in_(chunk_uuids)))
        chunk_by_id = {str(c.id): c for c in result.scalars().all()}

        ordered_chunks = [chunk_by_id[cid] for cid in fused_ids if cid in chunk_by_id]
        candidates = [RerankCandidate(id=str(c.id), text=c.text) for c in ordered_chunks]
        reranked = await reranker.rerank(state["rewritten_query"], candidates, settings.rerank_top_k)

        ranked_dicts = []
        for result_item in reranked:
            chunk = chunk_by_id[result_item.id]
            ranked_dicts.append(
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "text": chunk.text,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title,
                    "chunk_type": chunk.chunk_type.value,
                    "bbox": chunk.bbox,
                    "score": result_item.score,
                }
            )
        return {"ranked_chunks": ranked_dicts}

    async def node_compress(state: RetrievalState) -> dict:
        ranked_chunks = state.get("ranked_chunks", [])
        context, included = compress_context(ranked_chunks, settings.context_token_budget)
        confidence = sum(c["score"] for c in included) / len(included) if included else 0.0
        return {"context": context, "chunks": included, "confidence": min(max(confidence, 0.0), 1.0)}

    graph = StateGraph(RetrievalState)
    graph.add_node("rewrite", node_rewrite)
    graph.add_node("expand", node_expand)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("rerank", node_rerank)
    graph.add_node("compress", node_compress)

    graph.set_entry_point("rewrite")
    graph.add_edge("rewrite", "expand")
    graph.add_edge("expand", "retrieve")
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "compress")
    graph.add_edge("compress", END)

    return graph.compile()


async def run_retrieval(
    llm: BaseLLMProvider,
    embedder: BaseEmbeddingProvider,
    store: BaseVectorStore,
    reranker: BaseRerankerProvider,
    db: AsyncSession,
    question: str,
    history: list[dict],
    document_ids: list[str],
) -> RetrievalResult:
    graph = build_retrieval_graph(llm, embedder, store, reranker, db)
    final_state = await graph.ainvoke(
        {"question": question, "history": history, "document_ids": document_ids}
    )
    return {
        "rewritten_query": final_state.get("rewritten_query", question),
        "context": final_state.get("context", ""),
        "chunks": final_state.get("chunks", []),
        "confidence": final_state.get("confidence", 0.0),
    }
