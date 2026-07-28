from functools import lru_cache

from app.core.config import get_settings
from app.services.reranker.base import BaseRerankerProvider

settings = get_settings()


@lru_cache
def get_reranker_provider() -> BaseRerankerProvider:
    provider = settings.reranker_provider

    if provider == "bge":
        from app.services.reranker.bge_reranker import BGERerankerProvider

        return BGERerankerProvider()
    if provider == "cohere":
        from app.services.reranker.cohere import CohereRerankerProvider

        return CohereRerankerProvider()

    raise ValueError(f"Unknown reranker_provider: {provider}")
