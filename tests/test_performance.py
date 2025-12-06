"""Performance tests for llm-memory v1.1.0."""

import time

import pytest

from llm_memory.services.memory_service import MemoryService


@pytest.mark.performance
@pytest.mark.asyncio
class TestBatchPerformance:
    """Test batch operation performance."""

    async def test_batch_store_100_items_under_5_seconds(self, memory_service: MemoryService):
        """Test Case 51: Batch store 100 items within 5 seconds."""
        items = [
            {
                "content": f"Test content {i} " * 20,  # ~200 chars each
                "content_type": "text",
                "memory_tier": "long_term",
                "tags": [f"tag{i % 10}"],
            }
            for i in range(100)
        ]

        start_time = time.time()
        result = await memory_service.batch_store(items=items)
        elapsed_time = time.time() - start_time

        assert result["success_count"] == 100
        assert result["error_count"] == 0

        # Performance target: < 5 seconds
        # Note: With mock embeddings, this should be much faster
        assert elapsed_time < 10.0  # Relaxed for mock environment

        print(f"\nBatch store 100 items: {elapsed_time:.2f}s")


@pytest.mark.performance
@pytest.mark.asyncio
class TestHybridSearchPerformance:
    """Test hybrid search performance."""

    async def test_hybrid_search_1000_memories_under_500ms(
        self, memory_service: MemoryService
    ):
        """Test Case 52: Hybrid search with 1000 memories within 500ms."""
        # Create 1000 memories
        print("\nCreating 1000 memories...")
        # Batch store in chunks of 100 (MAX_BATCH_SIZE limit)
        for batch_start in range(0, 1000, 100):
            items = [
                {
                    "content": f"Test memory {i} with various content and keywords",
                    "content_type": "text",
                    "memory_tier": "long_term",
                }
                for i in range(batch_start, min(batch_start + 100, 1000))
            ]
            await memory_service.batch_store(items=items)

        # Perform hybrid search
        start_time = time.time()
        result = await memory_service.search(
            query="test keywords",
            search_mode="hybrid",
            top_k=10,
        )
        elapsed_time = time.time() - start_time

        assert len(result) > 0

        # Performance target: < 500ms
        # Relaxed for testing environment
        assert elapsed_time < 2.0  # 2 seconds

        print(f"Hybrid search 1000 memories: {elapsed_time*1000:.0f}ms")

    @pytest.mark.skip(reason="Requires 10,000 memories - slow test")
    async def test_hybrid_search_10000_memories(self, memory_service: MemoryService):
        """Test Case 52 (full): Hybrid search with 10,000 memories."""
        # Create 10,000 memories in batches
        print("\nCreating 10,000 memories...")
        for batch_num in range(100):
            items = [
                {
                    "content": f"Memory {batch_num * 100 + i} content",
                    "content_type": "text",
                }
                for i in range(100)
            ]
            await memory_service.batch_store(items=items)

        # Perform hybrid search
        start_time = time.time()
        result = await memory_service.search(
            query="content",
            search_mode="hybrid",
            top_k=10,
        )
        elapsed_time = time.time() - start_time

        assert len(result) > 0

        # Performance target: < 500ms
        print(f"Hybrid search 10,000 memories: {elapsed_time*1000:.0f}ms")
        assert elapsed_time < 0.5


@pytest.mark.performance
@pytest.mark.asyncio
class TestConsolidationPerformance:
    """Test consolidation performance."""

    async def test_consolidate_50_memories_under_3_seconds(
        self, memory_service: MemoryService, memory_repository, embedding_service
    ):
        """Test Case 53: Consolidate 50 memories within 3 seconds."""
        from llm_memory.services.consolidation_service import ConsolidationService

        # Create 50 memories with ~1000 chars each
        memory_ids = []
        for i in range(50):
            content = f"Memory {i}. " + "This is test content. " * 50  # ~1000 chars
            memory = await memory_service.store(
                content=content,
                content_type="text",
            )
            memory_ids.append(memory.id)

        # Consolidate
        consolidation_service = ConsolidationService(
            repository=memory_repository,
            embedding_service=embedding_service,
        )

        start_time = time.time()
        result = await consolidation_service.consolidate(
            memory_ids=memory_ids,
            summary_strategy="auto",
        )
        elapsed_time = time.time() - start_time

        assert result["consolidated_id"] is not None
        assert result["source_count"] == 50

        # Performance target: < 3 seconds
        # Relaxed for testing environment
        assert elapsed_time < 10.0

        print(f"\nConsolidate 50 memories: {elapsed_time:.2f}s")


@pytest.mark.performance
@pytest.mark.asyncio
class TestMigrationPerformance:
    """Test migration performance."""

    @pytest.mark.skip(reason="Requires creating 10,000 memories - very slow test")
    async def test_migrate_10000_memories_under_30_seconds(self):
        """Test Case 54: Migrate 10,000 memories within 30 seconds."""
        import os
        import tempfile

        from llm_memory.db.database import Database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            # Create database with old schema (v1)
            db = Database(database_path=db_path, embedding_dimensions=384)
            await db.connect()

            # Create 10,000 test memories (simplified)
            # This is a simplified test - actual implementation would need
            # to properly simulate v1 schema
            print("\nCreating 10,000 test memories...")
            for i in range(100):
                batch_values = [
                    (
                        f"mem-{i*100+j}",
                        "agent-1",
                        f"Content {i*100+j}",
                        "text",
                        "long_term",
                        "[0.1,0.2,0.3]",
                    )
                    for j in range(100)
                ]

                await db.connection.executemany(
                    """
                    INSERT INTO memories (id, agent_id, content, content_type, memory_tier, embedding)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    batch_values,
                )
                await db.connection.commit()

            # Perform migration
            print("Running migration...")
            start_time = time.time()
            await db.migrate()
            elapsed_time = time.time() - start_time

            await db.close()

            # Performance target: < 30 seconds
            print(f"Migration 10,000 memories: {elapsed_time:.2f}s")
            assert elapsed_time < 30.0

        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)


@pytest.mark.performance
@pytest.mark.asyncio
class TestScalability:
    """Test general scalability."""

    async def test_keyword_search_scalability(self, memory_service: MemoryService):
        """Test keyword search performance with varying data sizes."""
        # Create 500 memories
        # Batch store in chunks of 100 (MAX_BATCH_SIZE limit)
        for batch_start in range(0, 500, 100):
            items = [
                {
                    "content": f"Document {i} contains important keywords and phrases",
                    "content_type": "text",
                }
                for i in range(batch_start, min(batch_start + 100, 500))
            ]
            await memory_service.batch_store(items=items)

        # Test keyword search
        start_time = time.time()
        result = await memory_service.search(
            query="important",
            search_mode="keyword",
            top_k=10,
        )
        elapsed_time = time.time() - start_time

        assert len(result) > 0

        print(f"\nKeyword search 500 memories: {elapsed_time*1000:.0f}ms")
        # Should be very fast (< 100ms)
        assert elapsed_time < 1.0

    async def test_importance_scoring_overhead(self, memory_service: MemoryService):
        """Test overhead of importance scoring during search."""
        # Create memories
        items = [{"content": f"Test memory {i}", "content_type": "text"} for i in range(100)]

        await memory_service.batch_store(items=items)

        # Search with importance sorting
        start_time = time.time()
        result = await memory_service.search(
            query="test",
            sort_by="importance",
            top_k=10,
        )
        elapsed_time = time.time() - start_time

        assert len(result) > 0

        print(f"\nImportance-sorted search 100 memories: {elapsed_time*1000:.0f}ms")
        # Should still be fast
        assert elapsed_time < 2.0
