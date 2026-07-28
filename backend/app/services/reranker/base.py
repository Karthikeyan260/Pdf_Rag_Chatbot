from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RerankCandidate:
    id: str
    text: str


@dataclass
class RerankResult:
    id: str
    score: float


class BaseRerankerProvider(ABC):
    @abstractmethod
    async def rerank(self, query: str, candidates: list[RerankCandidate], top_k: int) -> list[RerankResult]:
        """Return candidates re-scored and sorted best-first, truncated to top_k."""
