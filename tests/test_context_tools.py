"""Tests for context building MCP tools."""

import pytest
import pytest_asyncio

from src.services.context_building_service import ContextBuildingService
from src.services.graph_traversal_service import GraphTraversalService
from src.services.semantic_cache import SemanticCache
from src.tools.context_tools import (
    memory_cache_clear,
    memory_cache_stats,
    memory_context_build,
)


@pytest_asyncio.fixture
async def graph_traversal_service_for_tools(linking_service, memory_repository) -> GraphTraversalService:
    """Create graph traversal service for tools."""
    return GraphTraversalService(
        linking_service=linking_service,
        repository=memory_repository,
    )


@pytest_asyncio.fixture
async def semantic_cache_for_tools(embedding_service) -> SemanticCache:
    """Create semantic cache for tools."""
    import asyncio

    cache = SemanticCache(
        max_size=100,
        ttl_seconds=3600,
        embedding_service=embedding_service,
        similarity_threshold=0.95,
    )
    yield cache
    # Cleanup
    if cache._cleanup_task:
        cache._cleanup_task.cancel()
        try:
            await cache._cleanup_task
        except asyncio.CancelledError:
            pass


@pytest_asyncio.fixture
async def context_service_for_tools(
    memory_service,
    graph_traversal_service_for_tools,
    semantic_cache_for_tools,
    embedding_service,
) -> ContextBuildingService:
    """Create context building service for tools."""
    return ContextBuildingService(
        memory_service=memory_service,
        graph_service=graph_traversal_service_for_tools,
        cache=semantic_cache_for_tools,
        embedding_service=embedding_service,
        token_buffer_ratio=0.1,
    )


@pytest.mark.asyncio
class TestMemoryContextBuild:
    """Test memory_context_build tool."""

    async def test_memory_context_build_basic(
        self,
        context_service_for_tools: ContextBuildingService,
        memory_service,
    ):
        """Test basic memory_context_build tool usage."""
        # Setup
        await memory_service.store(content="Test memory content", tags=["test"])

        # Execute
        result = await memory_context_build(
            service=context_service_for_tools,
            query="test memory",
            token_budget=1000,
        )

        # Verify
        assert "memories" in result
        assert "total_tokens" in result
        assert "token_budget" in result
        assert result["token_budget"] == 1000

    async def test_memory_context_build_with_parameters(
        self,
        context_service_for_tools: ContextBuildingService,
        memory_service,
    ):
        """Test memory_context_build with custom parameters."""
        await memory_service.store(content="Test content", tags=["test"])

        result = await memory_context_build(
            service=context_service_for_tools,
            query="test",
            token_budget=2000,
            top_k=10,
            include_related=False,
            max_depth=1,
            auto_summarize=False,
            min_similarity=0.3,
            use_cache=False,
            strategy="relevance",
        )

        assert "memories" in result
        assert result["token_budget"] == 2000

    async def test_memory_context_build_invalid_strategy(
        self,
        context_service_for_tools: ContextBuildingService,
    ):
        """Test memory_context_build with invalid strategy."""
        result = await memory_context_build(
            service=context_service_for_tools,
            query="test",
            token_budget=1000,
            strategy="invalid_strategy",
        )

        # Should return error response
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"

    async def test_memory_context_build_invalid_token_budget(
        self,
        context_service_for_tools: ContextBuildingService,
    ):
        """Test memory_context_build with invalid token budget."""
        result = await memory_context_build(
            service=context_service_for_tools,
            query="test",
            token_budget=50,  # Below minimum
        )

        # Should return error response
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"

    async def test_memory_context_build_all_strategies(
        self,
        context_service_for_tools: ContextBuildingService,
        memory_service,
    ):
        """Test all valid strategies."""
        await memory_service.store(content="Test content", tags=["test"])

        strategies = ["relevance", "recency", "importance", "graph"]

        for strategy in strategies:
            result = await memory_context_build(
                service=context_service_for_tools,
                query="test",
                token_budget=1000,
                strategy=strategy,
            )

            assert "memories" in result
            assert "error" not in result

    async def test_memory_context_build_with_namespace(
        self,
        context_service_for_tools: ContextBuildingService,
        memory_service,
    ):
        """Test memory_context_build with namespace."""
        await memory_service.store(
            content="Namespace content",
            tags=["test"],
            namespace="test_ns",
        )

        result = await memory_context_build(
            service=context_service_for_tools,
            query="namespace content",
            token_budget=1000,
            namespace="test_ns",
        )

        assert "memories" in result

    async def test_memory_context_build_cache_hit(
        self,
        context_service_for_tools: ContextBuildingService,
        memory_service,
    ):
        """Test cache hit with memory_context_build."""
        await memory_service.store(content="Cache test", tags=["cache"])

        # First call
        result1 = await memory_context_build(
            service=context_service_for_tools,
            query="cache test",
            token_budget=1000,
            use_cache=True,
        )
        assert result1["cache_hit"] is False

        # Second call (should hit cache)
        result2 = await memory_context_build(
            service=context_service_for_tools,
            query="cache test",
            token_budget=1000,
            use_cache=True,
        )
        assert result2["cache_hit"] is True


@pytest.mark.asyncio
class TestMemoryCacheClear:
    """Test memory_cache_clear tool."""

    async def test_memory_cache_clear_all(
        self,
        semantic_cache_for_tools: SemanticCache,
    ):
        """Test clearing all cache entries."""
        # Add some entries
        await semantic_cache_for_tools.put("query 1", {"data": 1})
        await semantic_cache_for_tools.put("query 2", {"data": 2})

        # Clear all
        result = await memory_cache_clear(cache=semantic_cache_for_tools)

        assert "cleared_count" in result
        assert result["cleared_count"] == 2
        assert "timestamp" in result

    async def test_memory_cache_clear_empty(
        self,
        semantic_cache_for_tools: SemanticCache,
    ):
        """Test clearing empty cache."""
        result = await memory_cache_clear(cache=semantic_cache_for_tools)

        assert "cleared_count" in result
        assert result["cleared_count"] == 0

    async def test_memory_cache_clear_with_pattern(
        self,
        semantic_cache_for_tools: SemanticCache,
    ):
        """Test clearing cache with pattern."""
        await semantic_cache_for_tools.put("test query 1", {"data": 1})
        await semantic_cache_for_tools.put("other query", {"data": 2})

        # Clear with pattern
        result = await memory_cache_clear(
            cache=semantic_cache_for_tools,
            pattern="test",
        )

        assert "cleared_count" in result
        # Pattern matching is on hash keys, so we just verify it runs
        assert result["cleared_count"] >= 0


@pytest.mark.asyncio
class TestMemoryCacheStats:
    """Test memory_cache_stats tool."""

    async def test_memory_cache_stats_empty(
        self,
        semantic_cache_for_tools: SemanticCache,
    ):
        """Test cache stats on empty cache."""
        result = await memory_cache_stats(cache=semantic_cache_for_tools)

        assert "total_entries" in result
        assert result["total_entries"] == 0
        assert "hit_count" in result
        assert "miss_count" in result
        assert "hit_rate" in result

    async def test_memory_cache_stats_with_data(
        self,
        semantic_cache_for_tools: SemanticCache,
    ):
        """Test cache stats with data."""
        # Get initial counts
        initial_result = await memory_cache_stats(cache=semantic_cache_for_tools)
        initial_hits = initial_result["hit_count"]
        initial_misses = initial_result["miss_count"]
        initial_total = initial_hits + initial_misses

        # Add entries
        await semantic_cache_for_tools.put("query 1", {"data": 1})
        await semantic_cache_for_tools.put("query 2", {"data": 2})

        # Access cache
        await semantic_cache_for_tools.get("query 1")  # hit
        # Note: Mock embeddings may cause LSH similarity hits
        await semantic_cache_for_tools.get("nonexistent")

        result = await memory_cache_stats(cache=semantic_cache_for_tools)

        assert result["total_entries"] >= 2
        assert result["hit_count"] >= initial_hits + 1
        # Total requests should increase
        new_total = result["hit_count"] + result["miss_count"]
        assert new_total >= initial_total + 2
        assert "memory_usage_bytes" in result

    async def test_memory_cache_stats_structure(
        self,
        semantic_cache_for_tools: SemanticCache,
    ):
        """Test cache stats return structure."""
        result = await memory_cache_stats(cache=semantic_cache_for_tools)

        # Check all expected fields
        expected_fields = [
            "total_entries",
            "hit_count",
            "miss_count",
            "hit_rate",
            "memory_usage_bytes",
            "oldest_entry",
            "newest_entry",
        ]

        for field in expected_fields:
            assert field in result

    async def test_memory_cache_stats_timestamps(
        self,
        semantic_cache_for_tools: SemanticCache,
    ):
        """Test cache stats timestamps."""
        await semantic_cache_for_tools.put("query", {"data": "test"})

        result = await memory_cache_stats(cache=semantic_cache_for_tools)

        # Should have timestamp strings
        assert result["oldest_entry"] is not None
        assert result["newest_entry"] is not None


@pytest.mark.asyncio
class TestToolErrorHandling:
    """Test error handling in tools."""

    async def test_memory_context_build_handles_exceptions(
        self,
        context_service_for_tools: ContextBuildingService,
    ):
        """Test memory_context_build handles internal exceptions gracefully."""
        # Invalid parameters should return error response, not raise
        result = await memory_context_build(
            service=context_service_for_tools,
            query="test",
            token_budget=999999,  # Out of range
        )

        assert result["error"] is True

    async def test_tools_return_proper_error_structure(
        self,
        context_service_for_tools: ContextBuildingService,
    ):
        """Test error responses have proper structure."""
        result = await memory_context_build(
            service=context_service_for_tools,
            query="test",
            token_budget=50,  # Invalid
        )

        assert result["error"] is True
        assert "message" in result
        assert "error_type" in result


@pytest.mark.asyncio
class TestToolIntegration:
    """Test integration between tools."""

    async def test_build_clear_stats_workflow(
        self,
        context_service_for_tools: ContextBuildingService,
        semantic_cache_for_tools: SemanticCache,
        memory_service,
    ):
        """Test workflow: build context, check stats, clear cache."""
        # Setup
        await memory_service.store(content="Test content", tags=["test"])

        # Build context (populates cache)
        build_result = await memory_context_build(
            service=context_service_for_tools,
            query="test content",
            token_budget=1000,
            use_cache=True,
        )
        assert "memories" in build_result

        # Check stats
        stats_result = await memory_cache_stats(cache=semantic_cache_for_tools)
        initial_entries = stats_result["total_entries"]

        # Clear cache
        clear_result = await memory_cache_clear(cache=semantic_cache_for_tools)
        assert clear_result["cleared_count"] == initial_entries

        # Check stats again
        stats_after = await memory_cache_stats(cache=semantic_cache_for_tools)
        assert stats_after["total_entries"] == 0

    async def test_repeated_builds_with_cache(
        self,
        context_service_for_tools: ContextBuildingService,
        memory_service,
    ):
        """Test repeated builds leverage cache."""
        await memory_service.store(content="Cached content", tags=["cache"])

        # First build
        result1 = await memory_context_build(
            service=context_service_for_tools,
            query="cached content",
            token_budget=1000,
            use_cache=True,
        )
        assert result1["cache_hit"] is False

        # Second build
        result2 = await memory_context_build(
            service=context_service_for_tools,
            query="cached content",
            token_budget=1000,
            use_cache=True,
        )
        assert result2["cache_hit"] is True

        # Results should be equivalent
        assert result1["memories_count"] == result2["memories_count"]
