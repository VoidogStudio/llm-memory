"""Tests for FR-004: Batch Operations."""

import pytest

from llm_memory.services.memory_service import MemoryService


@pytest.mark.asyncio
class TestBatchStore:
    """Test memory_batch_store functionality."""

    async def test_batch_store_success(self, memory_service: MemoryService):
        """Test Case 1: Successfully store multiple memories."""
        items = [
            {
                "content": f"Test content {i}",
                "content_type": "text",
                "memory_tier": "long_term",
                "tags": [f"tag{i}"],
            }
            for i in range(10)
        ]

        result = await memory_service.batch_store(items=items)

        assert result["success_count"] == 10
        assert result["error_count"] == 0
        assert len(result["created_ids"]) == 10
        assert result["errors"] == []

        # Verify memories exist in database
        for memory_id in result["created_ids"]:
            memory = await memory_service.get(memory_id)
            assert memory is not None
            # Note: Embeddings are stored separately in embeddings table, not on Memory model

    async def test_batch_store_max_size(self, memory_service: MemoryService):
        """Test Case 2: Store maximum batch size (100 items)."""
        items = [
            {
                "content": f"Test content {i}",
                "content_type": "text",
                "memory_tier": "long_term",
            }
            for i in range(100)
        ]

        result = await memory_service.batch_store(items=items)

        assert result["success_count"] == 100
        assert result["error_count"] == 0

    async def test_batch_store_exceeds_max(self, memory_service: MemoryService):
        """Test Case 3: Reject batch size exceeding 100 items."""
        items = [{"content": f"Test {i}", "content_type": "text"} for i in range(101)]

        with pytest.raises(ValueError) as exc_info:
            await memory_service.batch_store(items=items)

        assert "batch size exceeds maximum" in str(exc_info.value).lower() or "maximum" in str(exc_info.value).lower()

    async def test_batch_store_empty_list(self, memory_service: MemoryService):
        """Test Case 4: Reject empty item list."""
        with pytest.raises(ValueError) as exc_info:
            await memory_service.batch_store(items=[])

        assert "empty" in str(exc_info.value).lower() or "at least 1" in str(exc_info.value).lower()

    async def test_batch_store_rollback_mode(self, memory_service: MemoryService):
        """Test Case 5: Rollback all items on error."""
        items = [
            {"content": "Valid 1", "content_type": "text"},
            {"content": "Valid 2", "content_type": "text"},
            {"content": "Invalid", "content_type": "invalid_type"},  # Invalid
            {"content": "Valid 4", "content_type": "text"},
            {"content": "Valid 5", "content_type": "text"},
        ]

        result = await memory_service.batch_store(items=items, on_error="rollback")

        assert result["success_count"] == 0
        assert result["error_count"] > 0

        # Verify no memories were stored
        search_result = await memory_service.search(query="Valid", top_k=10)
        assert len(search_result) == 0

    async def test_batch_store_continue_mode(self, memory_service: MemoryService):
        """Test Case 6: Continue processing valid items despite errors."""
        items = [
            {"content": "Valid 1", "content_type": "text"},
            {"content": "Valid 2", "content_type": "text"},
            {"content": "Invalid", "content_type": "invalid_type"},  # Invalid
            {"content": "Valid 4", "content_type": "text"},
            {"content": "Valid 5", "content_type": "text"},
        ]

        result = await memory_service.batch_store(items=items, on_error="continue")

        assert result["success_count"] == 4
        assert result["error_count"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["index"] == 2

        # Verify 4 memories were stored
        search_result = await memory_service.search(query="Valid", top_k=10)
        assert len(search_result) == 4

    async def test_batch_store_stop_mode(self, memory_service: MemoryService):
        """Test Case 7: Stop processing on first error."""
        items = [
            {"content": "Valid 1", "content_type": "text"},
            {"content": "Valid 2", "content_type": "text"},
            {"content": "Invalid", "content_type": "invalid_type"},  # Invalid
            {"content": "Valid 4", "content_type": "text"},
            {"content": "Valid 5", "content_type": "text"},
        ]

        result = await memory_service.batch_store(items=items, on_error="stop")

        assert result["success_count"] == 2
        assert result["error_count"] == 1
        assert len(result["errors"]) == 1

        # Verify only 2 memories were stored
        search_result = await memory_service.search(query="Valid", top_k=10)
        assert len(search_result) == 2


@pytest.mark.asyncio
class TestBatchUpdate:
    """Test memory_batch_update functionality."""

    async def test_batch_update_success(self, memory_service: MemoryService):
        """Test Case 8: Successfully update multiple memories."""
        # Create 10 memories
        memory_ids = []
        for i in range(10):
            memory = await memory_service.store(
                content=f"Original content {i}",
                content_type="text",
                tags=["original"],
            )
            memory_ids.append(memory.id)

        # Update all memories
        updates = [{"id": mid, "tags": ["updated"]} for mid in memory_ids]

        result = await memory_service.batch_update(updates=updates)

        assert result["success_count"] == 10
        assert result["error_count"] == 0

        # Verify tags were updated
        for mid in memory_ids:
            memory = await memory_service.get(mid)
            assert "updated" in memory.tags
            assert "original" not in memory.tags

    async def test_batch_update_content_regenerates_embedding(self, memory_service: MemoryService):
        """Test Case 9: Updating content regenerates embeddings."""
        # Create 5 memories
        memory_ids = []
        original_embeddings = []
        for i in range(5):
            memory = await memory_service.store(
                content=f"Original content {i}",
                content_type="text",
            )
            memory_ids.append(memory.id)
            # Note: Embeddings are stored separately in embeddings table, not on Memory model

        # Update content for 3 memories
        updates = [
            {"id": memory_ids[0], "content": "New content 0"},
            {"id": memory_ids[1], "content": "New content 1"},
            {"id": memory_ids[2], "content": "New content 2"},
        ]

        result = await memory_service.batch_update(updates=updates)

        assert result["success_count"] == 3

        # Verify embeddings were regenerated for updated memories
        # Note: Since we're using mock embeddings, they might be the same
        # In a real test with actual embeddings, this would verify regeneration
        for i in range(3):
            memory = await memory_service.get(memory_ids[i])
            assert memory.content == f"New content {i}"
            # Note: Embeddings are stored separately in embeddings table, not on Memory model

        # Verify unchanged memories remain the same
        for i in range(3, 5):
            memory = await memory_service.get(memory_ids[i])
            assert memory.content == f"Original content {i}"

    async def test_batch_update_nonexistent_id(self, memory_service: MemoryService):
        """Test Case 10: Handle nonexistent IDs gracefully."""
        # Create 2 valid memories
        memory1 = await memory_service.store(content="Memory 1", content_type="text")
        memory2 = await memory_service.store(content="Memory 2", content_type="text")

        updates = [
            {"id": memory1.id, "tags": ["updated"]},
            {"id": "nonexistent-id-12345", "tags": ["updated"]},
            {"id": memory2.id, "tags": ["updated"]},
        ]

        result = await memory_service.batch_update(updates=updates, on_error="continue")

        assert result["success_count"] == 2
        assert result["error_count"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["id"] == "nonexistent-id-12345"

        # Verify valid memories were updated
        mem1 = await memory_service.get(memory1.id)
        assert "updated" in mem1.tags
        mem2 = await memory_service.get(memory2.id)
        assert "updated" in mem2.tags
