"""Integration tests for llm-memory MCP tools and workflows."""

from datetime import datetime, timedelta, timezone

import pytest

from llm_memory.models.agent import AccessLevel, MessageType
from llm_memory.models.memory import ContentType, MemoryTier


class TestMCPToolFlow:
    """End-to-end MCP tool flow tests."""

    @pytest.mark.asyncio
    async def test_memory_store_search_flow(self, memory_service):
        """Test store -> search -> get flow."""
        # Store memory
        memory = await memory_service.store(
            content="Python programming language tutorial",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.LONG_TERM,
            tags=["python", "tutorial"],
        )
        assert memory.id is not None

        # Search for it
        results = await memory_service.search(
            query="Python", top_k=5, min_similarity=0.0
        )
        assert len(results) > 0
        assert results[0].memory.id == memory.id

        # Get by ID
        retrieved = await memory_service.get(memory.id)
        assert retrieved is not None
        assert retrieved.content == "Python programming language tutorial"

    @pytest.mark.asyncio
    async def test_memory_crud_flow(self, memory_service):
        """Test complete CRUD flow."""
        # Create
        memory = await memory_service.store(
            content="Initial content",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.SHORT_TERM,
            tags=["test"],
        )
        assert memory.id is not None

        # Read
        retrieved = await memory_service.get(memory.id)
        assert retrieved.tags == ["test"]

        # Update
        updated = await memory_service.update(
            memory_id=memory.id, tags=["updated"]
        )
        assert updated.tags == ["updated"]

        # Delete
        deleted_ids = await memory_service.delete(memory_id=memory.id)
        assert memory.id in deleted_ids

        # Verify deletion
        deleted = await memory_service.get(memory.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_knowledge_import_query_flow(self, knowledge_service):
        """Test document import -> query flow."""
        # Import document
        document, chunk_count = await knowledge_service.import_document(
            title="Python Tutorial",
            content="Python is a versatile programming language. " * 50,
            category="programming",
            chunk_size=500,
            chunk_overlap=50,
        )
        assert document.id is not None
        assert chunk_count > 0

        # Query knowledge base
        results = await knowledge_service.query(
            query="programming language", top_k=5
        )
        assert len(results) > 0
        assert results[0].document.id == document.id


class TestVectorSearchAccuracy:
    """Vector search accuracy tests."""

    @pytest.mark.asyncio
    async def test_semantic_similarity_ranking(self, memory_service):
        """Test similarity ranking order."""
        # Store semantically different memories with very distinct content
        await memory_service.store(
            content="Python programming language features and syntax tutorial",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.LONG_TERM,
        )
        await memory_service.store(
            content="JavaScript runs in web browsers for frontend development",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.LONG_TERM,
        )
        await memory_service.store(
            content="The weather is sunny today with clear skies",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.LONG_TERM,
        )

        # Search with relevant query
        results = await memory_service.search(
            query="Python programming language", top_k=3, min_similarity=0.0
        )

        # Verify results are returned and sorted by similarity in descending order
        assert len(results) > 0
        for i in range(len(results) - 1):
            assert results[i].similarity >= results[i + 1].similarity

    @pytest.mark.asyncio
    async def test_search_with_filters(self, memory_service):
        """Test search with tier and tag filters."""
        # Store memories in different tiers
        await memory_service.store(
            content="Short term memory",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.SHORT_TERM,
            tags=["short"],
        )
        long_term = await memory_service.store(
            content="Long term memory",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.LONG_TERM,
            tags=["long"],
        )

        # Search with tier filter
        results = await memory_service.search(
            query="memory",
            memory_tier=MemoryTier.LONG_TERM,
            top_k=10,
            min_similarity=0.0,
        )
        assert all(r.memory.memory_tier == MemoryTier.LONG_TERM for r in results)
        assert len(results) == 1
        assert results[0].memory.id == long_term.id

    @pytest.mark.asyncio
    async def test_min_similarity_threshold(self, memory_service):
        """Test minimum similarity threshold filtering."""
        await memory_service.store(
            content="Python programming",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.LONG_TERM,
        )

        # Search with high threshold (should return fewer results)
        high_threshold_results = await memory_service.search(
            query="Python", top_k=10, min_similarity=0.9
        )

        # Search with low threshold (should return more results)
        low_threshold_results = await memory_service.search(
            query="Python", top_k=10, min_similarity=0.1
        )

        assert len(low_threshold_results) >= len(high_threshold_results)


class TestTTLCleanupIntegration:
    """TTL cleanup integration tests."""

    @pytest.mark.asyncio
    async def test_expired_memory_cleanup(self, memory_service):
        """Test expired memory deletion."""
        # Store memory with very short TTL
        memory = await memory_service.store(
            content="Expiring content",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.SHORT_TERM,
            ttl_seconds=1,
        )
        assert memory.expires_at is not None

        # Manually set expires_at to past
        past_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        await memory_service.repository.update(memory.id, {"expires_at": past_time.isoformat()})

        # Run cleanup
        count = await memory_service.cleanup_expired()
        assert count >= 1

        # Verify memory is gone
        retrieved = await memory_service.get(memory.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_non_expired_memory_preserved(self, memory_service):
        """Test non-expired memories are kept."""
        # Store memory with long TTL
        memory = await memory_service.store(
            content="Long lasting content",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.SHORT_TERM,
            ttl_seconds=3600,
        )

        # Run cleanup
        await memory_service.cleanup_expired()

        # Verify memory still exists
        retrieved = await memory_service.get(memory.id)
        assert retrieved is not None
        assert retrieved.content == "Long lasting content"

    @pytest.mark.asyncio
    async def test_cleanup_with_mixed_memories(self, memory_service):
        """Test cleanup with mixed expiration states."""
        # Expired memories
        past_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        for i in range(3):
            mem = await memory_service.store(
                content=f"Expired {i}",
                content_type=ContentType.TEXT,
                memory_tier=MemoryTier.SHORT_TERM,
                ttl_seconds=1,
            )
            await memory_service.repository.update(mem.id, {"expires_at": past_time.isoformat()})

        # Non-expired with TTL
        for i in range(2):
            await memory_service.store(
                content=f"Active {i}",
                content_type=ContentType.TEXT,
                memory_tier=MemoryTier.SHORT_TERM,
                ttl_seconds=3600,
            )

        # No TTL
        for i in range(2):
            await memory_service.store(
                content=f"Permanent {i}",
                content_type=ContentType.TEXT,
                memory_tier=MemoryTier.LONG_TERM,
            )

        # Run cleanup
        count = await memory_service.cleanup_expired()
        assert count == 3

        # Verify 4 memories remain
        all_memories, total = await memory_service.list_memories(limit=100)
        assert total == 4


class TestMultiTierMemoryFlow:
    """Multi-tier memory transition tests."""

    @pytest.mark.asyncio
    async def test_tier_promotion(self, memory_service):
        """Test promotion from short_term to long_term."""
        # Create in short_term
        memory = await memory_service.store(
            content="Promoted memory",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.SHORT_TERM,
        )
        assert memory.memory_tier == MemoryTier.SHORT_TERM

        # Promote to long_term
        updated = await memory_service.update(
            memory_id=memory.id, memory_tier=MemoryTier.LONG_TERM
        )
        assert updated.memory_tier == MemoryTier.LONG_TERM

    @pytest.mark.asyncio
    async def test_tier_demotion(self, memory_service):
        """Test demotion from long_term to working."""
        # Create in long_term
        memory = await memory_service.store(
            content="Demoted memory",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.LONG_TERM,
        )

        # Demote to working
        updated = await memory_service.update(
            memory_id=memory.id, memory_tier=MemoryTier.WORKING
        )
        assert updated.memory_tier == MemoryTier.WORKING

    @pytest.mark.asyncio
    async def test_tier_specific_search(self, memory_service):
        """Test tier-specific search."""
        # Create memories in different tiers
        await memory_service.store(
            content="Short term data",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.SHORT_TERM,
        )
        long_mem = await memory_service.store(
            content="Long term data",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.LONG_TERM,
        )
        await memory_service.store(
            content="Working data",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.WORKING,
        )

        # Search only long_term
        results = await memory_service.search(
            query="data",
            memory_tier=MemoryTier.LONG_TERM,
            top_k=10,
            min_similarity=0.0,
        )
        assert len(results) == 1
        assert results[0].memory.id == long_mem.id


class TestAgentCommunication:
    """Agent communication tests."""

    @pytest.mark.asyncio
    async def test_direct_message_flow(self, agent_service):
        """Test direct message send and receive."""
        # Register agents
        sender = await agent_service.register("sender", "Sender Agent")
        receiver = await agent_service.register("receiver", "Receiver Agent")

        # Send message
        message = await agent_service.send_message(
            sender_id=sender.id,
            content="Hello receiver",
            receiver_id=receiver.id,
            message_type=MessageType.DIRECT,
        )
        assert message.id is not None

        # Receive messages
        messages = await agent_service.receive_messages(
            agent_id=receiver.id, mark_as_read=False
        )
        assert len(messages) == 1
        assert messages[0].content == "Hello receiver"

    @pytest.mark.asyncio
    async def test_broadcast_message(self, agent_service):
        """Test broadcast message."""
        # Register agents
        await agent_service.register("broadcaster", "Broadcaster")
        await agent_service.register("listener1", "Listener 1")
        await agent_service.register("listener2", "Listener 2")

        # Send broadcast
        message = await agent_service.send_message(
            sender_id="broadcaster",
            content="Broadcast message",
            receiver_id=None,
            message_type=MessageType.BROADCAST,
        )
        assert message.receiver_id is None

    @pytest.mark.asyncio
    async def test_context_sharing(self, agent_service):
        """Test context sharing with access control."""
        # Register agents
        owner = await agent_service.register("owner", "Owner")
        allowed = await agent_service.register("allowed", "Allowed")
        denied = await agent_service.register("denied", "Denied")

        # Share context with restricted access
        context = await agent_service.share_context(
            key="restricted_data",
            value={"secret": "value"},
            agent_id=owner.id,
            access_level=AccessLevel.RESTRICTED,
            allowed_agents=[allowed.id],
        )
        assert context.key == "restricted_data"

        # Owner can read
        owner_read = await agent_service.read_context("restricted_data", owner.id)
        assert owner_read is not None

        # Allowed can read
        allowed_read = await agent_service.read_context("restricted_data", allowed.id)
        assert allowed_read is not None

        # Denied cannot read
        denied_read = await agent_service.read_context("restricted_data", denied.id)
        assert denied_read is None


class TestErrorHandling:
    """Error handling tests."""

    @pytest.mark.asyncio
    async def test_invalid_memory_tier_error(self):
        """Test invalid memory_tier returns error."""
        from unittest.mock import MagicMock

        from llm_memory.tools.memory_tools import memory_store

        service = MagicMock()
        result = await memory_store(
            service=service,
            content="Test",
            memory_tier="invalid_tier",
        )
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
        assert "invalid_tier" in result["message"]

    @pytest.mark.asyncio
    async def test_empty_content_error(self):
        """Test empty content returns error."""
        from unittest.mock import MagicMock

        from llm_memory.tools.memory_tools import memory_store

        service = MagicMock()
        result = await memory_store(
            service=service,
            content="",
        )
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
        assert "empty" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_not_found_error(self, memory_service):
        """Test not found returns error."""
        from llm_memory.tools.memory_tools import memory_get

        result = await memory_get(
            service=memory_service,
            id="non-existent-id",
        )
        assert result["error"] is True
        assert result["error_type"] == "NotFoundError"
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_error_response_structure(self):
        """Test error response structure is consistent."""
        from llm_memory.tools import create_error_response

        result = create_error_response(
            message="Test error",
            error_type="TestError",
            details={"key": "value"},
        )

        # Verify required fields
        assert "error" in result
        assert "message" in result
        assert "error_type" in result
        assert "timestamp" in result

        # Verify values
        assert result["error"] is True
        assert result["message"] == "Test error"
        assert result["error_type"] == "TestError"
        assert result["details"]["key"] == "value"

        # Verify timestamp is ISO 8601
        datetime.fromisoformat(result["timestamp"])
