"""Reciprocal Rank Fusion for hybrid search."""


def reciprocal_rank_fusion(
    semantic_results: list[tuple[str, float]],
    keyword_results: list[tuple[str, float]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Combine search results using Reciprocal Rank Fusion.

    Args:
        semantic_results: List of (id, similarity_score) from vector search
        keyword_results: List of (id, bm25_score) from FTS5 search
        k: RRF constant (default 60)

    Returns:
        List of (id, rrf_score) sorted by score descending
    """
    scores: dict[str, float] = {}

    # Add semantic scores
    for rank, (memory_id, _) in enumerate(semantic_results, 1):
        scores[memory_id] = scores.get(memory_id, 0) + 1 / (k + rank)

    # Add keyword scores
    for rank, (memory_id, _) in enumerate(keyword_results, 1):
        scores[memory_id] = scores.get(memory_id, 0) + 1 / (k + rank)

    # Sort by combined score
    sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return sorted_results


def weighted_combination(
    semantic_score: float,
    keyword_score: float,
    keyword_weight: float = 0.3,
) -> float:
    """Combine scores using weighted linear combination.

    Args:
        semantic_score: Normalized semantic similarity (0-1)
        keyword_score: Normalized keyword score (0-1)
        keyword_weight: Weight for keyword score

    Returns:
        Combined score
    """
    semantic_weight = 1.0 - keyword_weight
    return semantic_weight * semantic_score + keyword_weight * keyword_score
