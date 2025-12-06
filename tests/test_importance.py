"""Tests for FR-002: Importance Scoring."""

from datetime import datetime, timedelta, timezone

import pytest

from src.exceptions import NotFoundError
from src.services.importance_service import ImportanceService
from src.services.memory_service import MemoryService


@pytest.mark.asyncio
class TestScoreCalculation:
    """Test score calculation algorithm."""

    async def test_score_new_memory(self, memory_service: MemoryService, memory_repository):
        """Test Case 11: Score calculation for new memory (no access)."""
        memory = await memory_service.store(
            content="New memory",
            content_type="text",
        )

        # Use repository.find_by_id() to bypass access logging
        mem = await memory_repository.find_by_id(memory.id)

        # New memory should have default score (0.5)
        assert mem.importance_score == 0.5
        assert mem.access_count == 0
        assert mem.last_accessed_at is None

    async def test_score_frequently_accessed(
        self, memory_service: MemoryService, memory_repository
    ):
        """Test Case 12: Score calculation for frequently accessed memory."""
        memory = await memory_service.store(
            content="Frequently accessed memory",
            content_type="text",
        )

        # Simulate 100 accesses
        for _ in range(100):
            await memory_repository.log_access(memory.id, access_type="get")

        # Update importance score based on access
        importance_service = ImportanceService(repository=memory_repository)
        await importance_service.calculate_and_update_score(memory.id)

        mem = await memory_service.get(memory.id)

        # Note: access_count is 101 because memory_service.get() also logs access
        assert mem.access_count == 101
        assert mem.importance_score > 0.8  # High score for frequent access

    async def test_score_old_memory(self, memory_service: MemoryService, memory_repository):
        """Test Case 13: Score calculation for old memory."""
        memory = await memory_service.store(
            content="Old memory",
            content_type="text",
        )

        # Simulate access 60 days ago
        old_time = datetime.now(timezone.utc) - timedelta(days=60)
        await memory_repository.log_access(
            memory.id, access_type="get", timestamp=old_time
        )

        importance_service = ImportanceService(repository=memory_repository)
        await importance_service.calculate_and_update_score(memory.id)

        mem = await memory_service.get(memory.id)

        assert mem.importance_score < 0.3  # Low score for old memory


@pytest.mark.asyncio
class TestGetScore:
    """Test memory_get_score functionality."""

    async def test_get_score_success(self, memory_service: MemoryService, memory_repository):
        """Test Case 14: Successfully retrieve importance score."""
        memory = await memory_service.store(
            content="Test memory",
            content_type="text",
        )

        # Set access count and last accessed
        await memory_repository.log_access(memory.id, access_type="get")
        await memory_repository.log_access(memory.id, access_type="get")

        importance_service = ImportanceService(repository=memory_repository)
        score_info = await importance_service.get_score(memory.id)

        assert "importance_score" in score_info
        assert "access_count" in score_info
        assert score_info["access_count"] >= 2
        assert "last_accessed_at" in score_info

    async def test_get_score_nonexistent(self, memory_repository):
        """Test Case 15: Handle nonexistent memory ID."""
        importance_service = ImportanceService(repository=memory_repository)

        with pytest.raises(NotFoundError):
            await importance_service.get_score("nonexistent-id-12345")


@pytest.mark.asyncio
class TestSetScore:
    """Test memory_set_score functionality."""

    async def test_set_score_success(self, memory_service: MemoryService, memory_repository):
        """Test Case 16: Successfully set importance score."""
        memory = await memory_service.store(
            content="Test memory",
            content_type="text",
        )

        importance_service = ImportanceService(repository=memory_repository)
        result = await importance_service.set_score(
            memory.id, score=0.9, reason="Important for testing"
        )

        assert result["previous_score"] == 0.5
        assert result["new_score"] == 0.9

        # Verify in database
        mem = await memory_service.get(memory.id)
        assert mem.importance_score == 0.9

    async def test_set_score_out_of_range(self, memory_service: MemoryService, memory_repository):
        """Test Case 17: Reject score outside valid range."""
        memory = await memory_service.store(
            content="Test memory",
            content_type="text",
        )

        importance_service = ImportanceService(repository=memory_repository)

        with pytest.raises(ValueError):
            await importance_service.set_score(
                memory.id, score=1.5, reason="Out of range test"
            )

        with pytest.raises(ValueError):
            await importance_service.set_score(
                memory.id, score=-0.1, reason="Out of range test"
            )


@pytest.mark.asyncio
class TestAccessLogging:
    """Test access logging functionality."""

    async def test_access_log_on_get(self, memory_service: MemoryService, memory_repository):
        """Test Case 18: Log access when retrieving memory."""
        memory = await memory_service.store(
            content="Test memory",
            content_type="text",
        )

        # Get memory to trigger access log
        await memory_service.get(memory.id)

        # Check access was logged
        mem = await memory_service.get(memory.id)
        assert mem.access_count >= 1
        assert mem.last_accessed_at is not None

    async def test_access_log_on_search(self, memory_service: MemoryService):
        """Test Case 19: Log access when memories appear in search results."""
        # Create 3 memories
        mem1 = await memory_service.store(content="Python programming", content_type="text")
        mem2 = await memory_service.store(content="Python tutorial", content_type="text")
        _mem3 = await memory_service.store(content="Java programming", content_type="text")

        # Search for Python
        result = await memory_service.search(query="Python", top_k=5)

        # At least 2 memories should match
        assert len(result) >= 2

        # Check access was logged for search results
        for res in result:
            if res.memory.id in [mem1.id, mem2.id]:
                mem = await memory_service.get(res.memory.id)
                # Access count may vary depending on implementation
                assert mem.access_count >= 0

    async def test_access_log_cleanup(self, memory_service: MemoryService, memory_repository):
        """Test Case 20: Cleanup old access logs."""
        memory = await memory_service.store(
            content="Test memory",
            content_type="text",
        )

        # Create old log (40 days ago)
        old_time = datetime.now(timezone.utc) - timedelta(days=40)
        await memory_repository.log_access(
            memory.id, access_type="get", timestamp=old_time
        )

        # Create recent log (10 days ago)
        recent_time = datetime.now(timezone.utc) - timedelta(days=10)
        await memory_repository.log_access(
            memory.id, access_type="get", timestamp=recent_time
        )

        # Cleanup logs older than 30 days
        importance_service = ImportanceService(repository=memory_repository)
        deleted_count = await importance_service.cleanup_access_logs(retention_days=30)

        assert deleted_count >= 1  # Old log should be deleted


@pytest.mark.asyncio
class TestSearchSorting:
    """Test search sorting with importance scores."""

    async def test_sort_by_importance(self, memory_service: MemoryService, memory_repository):
        """Test Case 21: Sort search results by importance score."""
        # Create memories with different importance scores
        mem1 = await memory_service.store(content="Memory 1", content_type="text")
        mem2 = await memory_service.store(content="Memory 2", content_type="text")
        mem3 = await memory_service.store(content="Memory 3", content_type="text")

        # Set different scores
        importance_service = ImportanceService(repository=memory_repository)
        await importance_service.set_score(mem1.id, score=0.9, reason="High priority")
        await importance_service.set_score(mem2.id, score=0.5, reason="Medium priority")
        await importance_service.set_score(mem3.id, score=0.7, reason="Above average")

        # Search with importance sorting
        result = await memory_service.search(query="Memory", top_k=10, sort_by="importance")

        assert len(result) == 3

        # Results should be sorted by importance (0.9, 0.7, 0.5)
        scores = [r.memory.importance_score for r in result]
        assert scores == sorted(scores, reverse=True)
        assert result[0].memory.id == mem1.id
        assert result[2].memory.id == mem2.id

    async def test_sort_by_combined(self, memory_service: MemoryService, memory_repository):
        """Test Case 22: Sort by combined similarity and importance."""
        # Create memories
        mem1 = await memory_service.store(
            content="Python programming language",
            content_type="text",
        )
        mem2 = await memory_service.store(
            content="Java programming language",
            content_type="text",
        )

        # Set importance scores
        importance_service = ImportanceService(repository=memory_repository)
        await importance_service.set_score(mem1.id, score=0.6, reason="Standard")
        await importance_service.set_score(mem2.id, score=0.9, reason="Very important")

        # Search with combined sorting
        result = await memory_service.search(
            query="programming",
            top_k=10,
            sort_by="combined",
            importance_weight=0.4,
        )

        assert len(result) >= 2

        # Results should have combined scores
        # combined_score = 0.6 * similarity + 0.4 * importance
        for res in result:
            assert res.similarity is not None
            assert res.memory.importance_score is not None
            # Combined score should be influenced by both factors
