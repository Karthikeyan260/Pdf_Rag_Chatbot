def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Fuse multiple ranked id lists (dense search per query variant, BM25) into one ranking.

    RRF score for an id = sum over lists containing it of 1 / (k + rank). No score
    normalization needed across heterogeneous sources (cosine similarity vs. BM25),
    which is the whole point of using RRF for hybrid search.
    """
    scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, item_id in enumerate(ranked_list):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
