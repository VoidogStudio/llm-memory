"""Context building MCP tools."""

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from src.services.context_building_service import ContextBuildingService
from src.services.semantic_cache import SemanticCache
from src.tools import create_error_response


async def memory_context_build(
    service: ContextBuildingService,
    query: str,
    token_budget: int,
    top_k: int = 20,
    include_related: bool = True,
    max_depth: int = 2,
    auto_summarize: bool = True,
    min_similarity: float = 0.5,
    namespace: str | None = None,
    use_cache: bool = True,
    strategy: str = "relevance",
) -> dict[str, Any]:
    """Build optimal memory context within token budget.

    Args:
        service: Context building service instance
        query: Search query text
        token_budget: Maximum tokens for context (100-128000)
        top_k: Number of candidate memories (1-100)
        include_related: Include related memories via graph traversal
        max_depth: Maximum traversal depth for related memories (1-5)
        auto_summarize: Automatically summarize large memories
        min_similarity: Minimum similarity threshold (0.0-1.0)
        namespace: Target namespace (default: auto-detect)
        use_cache: Use semantic cache for results
        strategy: Memory selection strategy (relevance/recency/importance/graph)

    Returns:
        Context result with memories, token counts, and metadata
    """
    try:
        # Validate strategy
        valid_strategies = ["relevance", "recency", "importance", "graph"]
        if strategy not in valid_strategies:
            return create_error_response(
                message=f"Invalid strategy '{strategy}'. Must be one of: {', '.join(valid_strategies)}",
                error_type="ValidationError",
                details={"valid_strategies": valid_strategies},
            )

        # Build context
        result = await service.build_context(
            query=query,
            token_budget=token_budget,
            top_k=top_k,
            include_related=include_related,
            max_depth=max_depth,
            auto_summarize=auto_summarize,
            min_similarity=min_similarity,
            namespace=namespace,
            use_cache=use_cache,
            strategy=strategy,  # type: ignore
        )

        # Convert to dict
        return {
            "memories": [asdict(mem) for mem in result.memories],
            "total_tokens": result.total_tokens,
            "token_budget": result.token_budget,
            "memories_count": result.memories_count,
            "summarized_count": result.summarized_count,
            "related_count": result.related_count,
            "cache_hit": result.cache_hit,
        }

    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )
    except Exception as e:
        return create_error_response(
            message=f"Failed to build context: {str(e)}",
            error_type="RuntimeError",
        )


async def memory_cache_clear(
    cache: SemanticCache,
    pattern: str | None = None,
) -> dict[str, Any]:
    """Clear the semantic cache.

    Args:
        cache: Semantic cache instance
        pattern: Optional pattern to match cache entries (None = clear all)

    Returns:
        Number of cleared entries and timestamp
    """
    try:
        cleared_count = await cache.invalidate(pattern)

        return {
            "cleared_count": cleared_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        return create_error_response(
            message=f"Failed to clear cache: {str(e)}",
            error_type="RuntimeError",
        )


async def memory_cache_stats(cache: SemanticCache) -> dict[str, Any]:
    """Get semantic cache statistics.

    Args:
        cache: Semantic cache instance

    Returns:
        Cache statistics including hit rate, entry count, and memory usage
    """
    try:
        stats = cache.get_stats()

        return {
            "total_entries": stats.total_entries,
            "hit_count": stats.hit_count,
            "miss_count": stats.miss_count,
            "hit_rate": stats.hit_rate,
            "memory_usage_bytes": stats.memory_usage_bytes,
            "oldest_entry": stats.oldest_entry.isoformat() if stats.oldest_entry else None,
            "newest_entry": stats.newest_entry.isoformat() if stats.newest_entry else None,
        }

    except Exception as e:
        return create_error_response(
            message=f"Failed to get cache stats: {str(e)}",
            error_type="RuntimeError",
        )
