import asyncio

from app.core.config import get_settings
from app.services.reranker.base import BaseRerankerProvider, RerankCandidate, RerankResult

settings = get_settings()


class BGERerankerProvider(BaseRerankerProvider):
    """Live adapter for BAAI/bge-reranker-v2-m3 cross-encoder reranking via FlagEmbedding."""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            from FlagEmbedding import FlagReranker

            self._model = FlagReranker(settings.bge_reranker_model_name, use_fp16=True)
        return self._model

    def _score(self, query: str, candidates: list[RerankCandidate]) -> list[RerankResult]:
        model = self._get_model()
        pairs = [[query, c.text] for c in candidates]
        scores = model.compute_score(pairs, normalize=True)
        if isinstance(scores, float):
            scores = [scores]
        return [RerankResult(id=c.id, score=float(s)) for c, s in zip(candidates, scores)]

    async def rerank(self, query: str, candidates: list[RerankCandidate], top_k: int) -> list[RerankResult]:
        if not candidates:
            return []
        results = await asyncio.to_thread(self._score, query, candidates)
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
