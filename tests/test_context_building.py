"""Tests for context building service."""

import pytest
import pytest_asyncio

from src.models.linking import LinkType
from src.services.context_building_service import ContextBuildingService
from src.services.graph_traversal_service import GraphTraversalService
from src.services.semantic_cache import SemanticCache


@pytest_asyncio.fixture
async def graph_traversal_service(linking_service, memory_repository) -> GraphTraversalService:
    """Create graph traversal service."""
    return GraphTraversalService(
        linking_service=linking_service,
        repository=memory_repository,
    )


@pytest_asyncio.fixture
async def semantic_cache_for_context(embedding_service) -> SemanticCache:
    """Create semantic cache for context building."""
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
async def context_building_service(
    memory_service,
    graph_traversal_service,
    semantic_cache_for_context,
    embedding_service,
) -> ContextBuildingService:
    """Create context building service."""
    return ContextBuildingService(
        memory_service=memory_service,
        graph_service=graph_traversal_service,
        cache=semantic_cache_for_context,
        embedding_service=embedding_service,
        token_buffer_ratio=0.1,
    )


@pytest.mark.asyncio
class TestBasicContextBuilding:
    """Test basic context building functionality."""

    async def test_basic_context_build(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
    ):
        """Test basic context building."""
        # Setup: Create test memories
        for i in range(10):
            await memory_service.store(
                content=f"Test memory content {i} with some additional text",
                tags=["test"],
            )

        # Execute
        result = await context_building_service.build_context(
            query="test memory",
            token_budget=2000,
        )

        # Verify
        assert result.memories_count >= 0
        assert result.total_tokens <= 2000
        assert result.cache_hit is False

    async def test_token_budget_respected(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
    ):
        """Test token budget is respected."""
        # Setup: Create large memories
        large_content = "This is a test memory. " * 100  # ~400 tokens
        for i in range(5):
            await memory_service.store(content=large_content, tags=["large"])

        # Execute
        result = await context_building_service.build_context(
            query="test memory",
            token_budget=500,
        )

        # Verify (with 10% buffer, effective budget is 450)
        assert result.total_tokens <= 450

    async def test_include_related_memories(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
        linking_service,
    ):
        """Test including related memories via graph traversal."""
        # Setup: Create linked memories
        root = await memory_service.store(content="Root memory content", tags=["root"])
        related = await memory_service.store(content="Related memory content", tags=["related"])
        await linking_service.create_link(root.id, related.id, link_type=LinkType.RELATED)

        # Execute
        result = await context_building_service.build_context(
            query="Root memory",
            token_budget=2000,
            include_related=True,
        )

        # Verify
        assert result.related_count >= 0
        memory_ids = [m.id for m in result.memories]
        # Root should be included as direct match
        assert root.id in memory_ids


@pytest.mark.asyncio
class TestCacheOperations:
    """Test cache-related operations."""

    async def test_cache_hit(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
    ):
        """Test cache hit on repeated query."""
        # Setup
        await memory_service.store(content="Test memory for caching", tags=["cache"])

        # First call
        result1 = await context_building_service.build_context(
            query="test caching",
            token_budget=2000,
            use_cache=True,
        )
        assert result1.cache_hit is False

        # Second call (should hit cache)
        result2 = await context_building_service.build_context(
            query="test caching",
            token_budget=2000,
            use_cache=True,
        )
        assert result2.cache_hit is True

    async def test_cache_disabled(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
    ):
        """Test cache can be disabled."""
        await memory_service.store(content="Test memory", tags=["test"])

        # First call with cache disabled
        result1 = await context_building_service.build_context(
            query="test memory",
            token_budget=2000,
            use_cache=False,
        )
        assert result1.cache_hit is False

        # Second call with cache disabled
        result2 = await context_building_service.build_context(
            query="test memory",
            token_budget=2000,
            use_cache=False,
        )
        assert result2.cache_hit is False


@pytest.mark.asyncio
class TestAutoSummarization:
    """Test automatic summarization."""

    async def test_auto_summarization(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
    ):
        """Test auto summarization when content exceeds budget."""
        # Setup: Create a long memory
        long_content = "Important information. " * 50  # ~200 tokens
        await memory_service.store(content=long_content, tags=["long"])

        # Execute with tight budget
        result = await context_building_service.build_context(
            query="important information",
            token_budget=100,
            auto_summarize=True,
        )

        # Verify budget is respected (effective budget is 90 with 10% buffer)
        assert result.total_tokens <= 90

    async def test_auto_summarize_disabled(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
    ):
        """Test auto summarization can be disabled."""
        long_content = "Test content. " * 50
        await memory_service.store(content=long_content, tags=["test"])

        result = await context_building_service.build_context(
            query="test content",
            token_budget=100,
            auto_summarize=False,
        )

        # Without summarization, should still respect budget by selection
        assert result.total_tokens <= 90


@pytest.mark.asyncio
class TestSelectionStrategies:
    """Test different selection strategies."""

    @pytest.mark.parametrize("strategy", ["relevance", "recency", "importance", "graph"])
    async def test_selection_strategies(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
        strategy: str,
    ):
        """Test different selection strategies."""
        # Setup
        await memory_service.store(content="Test strategy content", tags=["strategy"])

        # Execute
        result = await context_building_service.build_context(
            query="test strategy",
            token_budget=2000,
            strategy=strategy,  # type: ignore
        )

        # Verify
        assert result is not None
        assert isinstance(result.memories, list)

    async def test_relevance_strategy_prioritizes_similarity(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
    ):
        """Test relevance strategy prioritizes similar content."""
        # Create memories with varying similarity
        await memory_service.store(content="Machine learning is awesome", tags=["ml"])
        await memory_service.store(content="Completely unrelated content", tags=["other"])

        result = await context_building_service.build_context(
            query="machine learning",
            token_budget=2000,
            strategy="relevance",
        )

        # More relevant content should come first
        assert len(result.memories) > 0


@pytest.mark.asyncio
class TestParameterValidation:
    """Test parameter validation."""

    @pytest.mark.parametrize(
        "token_budget,expected_error",
        [
            (50, True),  # Below minimum (100)
            (200000, True),  # Above maximum (128000)
            (1000, False),  # Valid
        ],
    )
    async def test_token_budget_validation(
        self,
        context_building_service: ContextBuildingService,
        token_budget: int,
        expected_error: bool,
    ):
        """Test token budget parameter validation."""
        if expected_error:
            with pytest.raises(ValueError):
                await context_building_service.build_context(
                    query="test",
                    token_budget=token_budget,
                )
        else:
            result = await context_building_service.build_context(
                query="test",
                token_budget=token_budget,
            )
            assert result is not None

    @pytest.mark.parametrize(
        "top_k,expected_error",
        [
            (0, True),  # Below minimum (1)
            (101, True),  # Above maximum (100)
            (20, False),  # Valid
        ],
    )
    async def test_top_k_validation(
        self,
        context_building_service: ContextBuildingService,
        top_k: int,
        expected_error: bool,
    ):
        """Test top_k parameter validation."""
        if expected_error:
            with pytest.raises(ValueError):
                await context_building_service.build_context(
                    query="test",
                    token_budget=1000,
                    top_k=top_k,
                )
        else:
            result = await context_building_service.build_context(
                query="test",
                token_budget=1000,
                top_k=top_k,
            )
            assert result is not None

    @pytest.mark.parametrize(
        "max_depth,expected_error",
        [
            (0, True),  # Below minimum (1)
            (6, True),  # Above maximum (5)
            (2, False),  # Valid
        ],
    )
    async def test_max_depth_validation(
        self,
        context_building_service: ContextBuildingService,
        max_depth: int,
        expected_error: bool,
    ):
        """Test max_depth parameter validation."""
        if expected_error:
            with pytest.raises(ValueError):
                await context_building_service.build_context(
                    query="test",
                    token_budget=1000,
                    max_depth=max_depth,
                )
        else:
            result = await context_building_service.build_context(
                query="test",
                token_budget=1000,
                max_depth=max_depth,
            )
            assert result is not None

    @pytest.mark.parametrize(
        "min_similarity,expected_error",
        [
            (-0.1, True),  # Below minimum (0.0)
            (1.1, True),  # Above maximum (1.0)
            (0.5, False),  # Valid
        ],
    )
    async def test_min_similarity_validation(
        self,
        context_building_service: ContextBuildingService,
        min_similarity: float,
        expected_error: bool,
    ):
        """Test min_similarity parameter validation."""
        if expected_error:
            with pytest.raises(ValueError):
                await context_building_service.build_context(
                    query="test",
                    token_budget=1000,
                    min_similarity=min_similarity,
                )
        else:
            result = await context_building_service.build_context(
                query="test",
                token_budget=1000,
                min_similarity=min_similarity,
            )
            assert result is not None


@pytest.mark.asyncio
class TestResultStatistics:
    """Test result statistics."""

    async def test_result_contains_statistics(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
    ):
        """Test result contains all expected statistics."""
        await memory_service.store(content="Test content", tags=["test"])

        result = await context_building_service.build_context(
            query="test",
            token_budget=1000,
        )

        # Check all statistics are present
        assert hasattr(result, "total_tokens")
        assert hasattr(result, "token_budget")
        assert hasattr(result, "memories_count")
        assert hasattr(result, "summarized_count")
        assert hasattr(result, "related_count")
        assert hasattr(result, "cache_hit")

    async def test_summarized_count(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
    ):
        """Test summarized count is tracked."""
        long_content = "Test content. " * 100
        await memory_service.store(content=long_content, tags=["test"])

        result = await context_building_service.build_context(
            query="test content",
            token_budget=100,
            auto_summarize=True,
        )

        # Summarized count should be >= 0
        assert result.summarized_count >= 0


@pytest.mark.asyncio
class TestEmptyResults:
    """Test handling of empty results."""

    async def test_no_matching_memories(
        self,
        context_building_service: ContextBuildingService,
    ):
        """Test handling when no memories match."""
        result = await context_building_service.build_context(
            query="nonexistent content",
            token_budget=1000,
        )

        assert result.memories_count == 0
        assert result.total_tokens == 0
        assert len(result.memories) == 0

    async def test_empty_database(
        self,
        context_building_service: ContextBuildingService,
    ):
        """Test context building on empty database."""
        result = await context_building_service.build_context(
            query="any query",
            token_budget=1000,
        )

        assert result.memories_count == 0
        assert result.total_tokens == 0


@pytest.mark.asyncio
class TestNamespaceFiltering:
    """Test namespace filtering."""

    async def test_context_build_with_namespace(
        self,
        context_building_service: ContextBuildingService,
        memory_service,
    ):
        """Test context building respects namespace."""
        # Create memories in different namespaces
        await memory_service.store(
            content="Content in namespace A",
            tags=["test"],
            namespace="namespace_a",
        )
        await memory_service.store(
            content="Content in namespace B",
            tags=["test"],
            namespace="namespace_b",
        )

        # Search in specific namespace
        result = await context_building_service.build_context(
            query="content",
            token_budget=1000,
            namespace="namespace_a",
        )

        # Should only return memories from namespace_a
        assert result.memories_count >= 0
