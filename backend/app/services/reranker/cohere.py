from app.services.reranker.base import BaseRerankerProvider, RerankCandidate, RerankResult


class CohereRerankerProvider(BaseRerankerProvider):
    """Phase 2 stub — implement via `cohere.AsyncClient().rerank(...)` (`settings.cohere_api_key`)."""

    def __init__(self) -> None:
        pass

    async def rerank(self, query: str, candidates: list[RerankCandidate], top_k: int) -> list[RerankResult]:
        raise NotImplementedError("Cohere reranker provider is a Phase 2 stub")
