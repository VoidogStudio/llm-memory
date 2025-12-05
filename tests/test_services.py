"""Tests for service layer."""

import asyncio
from datetime import datetime, timezone

import pytest

from llm_memory.models.memory import ContentType, MemoryTier
from llm_memory.services.agent_service import AgentService
from llm_memory.services.embedding_service import EmbeddingService
from llm_memory.services.knowledge_service import KnowledgeService
from llm_memory.services.memory_service import MemoryService


class TestEmbeddingService:
    """Test EmbeddingService."""

    @pytest.mark.asyncio
    async def test_generate_embedding(self, embedding_service: EmbeddingService):
        """Test generating a single embedding."""
        embedding = await embedding_service.generate("Test text")

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(v, float) for v in embedding)

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings(self, embedding_service: EmbeddingService):
        """Test generating batch embeddings."""
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = await embedding_service.generate_batch(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)

    @pytest.mark.asyncio
    async def test_get_dimensions(self, embedding_service: EmbeddingService):
        """Test getting embedding dimensions."""
        dims = embedding_service.dimensions()

        assert dims == 384


class TestMemoryService:
    """Test MemoryService."""

    @pytest.mark.asyncio
    async def test_store_basic_memory(self, memory_service: MemoryService):
        """Test storing a basic memory."""
        memory = await memory_service.store(
            content="This is a test memory",
            content_type=ContentType.TEXT,
            memory_tier=MemoryTier.LONG_TERM,
            tags=["test", "unit"],
        )

        assert memory.content == "This is a test memory"
        assert memory.content_type == ContentType.TEXT
        assert memory.memory_tier == MemoryTier.LONG_TERM
        assert memory.tags == ["test", "unit"]
        assert isinstance(memory.id, str)
        assert memory.expires_at is None

    @pytest.mark.asyncio
    async def test_store_memory_with_ttl(self, memory_service: MemoryService):
        """Test storing memory with TTL."""
        memory = await memory_service.store(
            content="Short term memory",
            memory_tier=MemoryTier.SHORT_TERM,
            ttl_seconds=3600,
        )

        assert memory.expires_at is not None
        assert memory.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_get_memory_by_id(self, memory_service: MemoryService):
        """Test retrieving memory by ID."""
        # Store memory
        stored = await memory_service.store(content="Test content")

        # Retrieve memory
        retrieved = await memory_service.get(stored.id)

        assert retrieved is not None
        assert retrieved.id == stored.id
        assert retrieved.content == "Test content"

    @pytest.mark.asyncio
    async def test_get_nonexistent_memory(self, memory_service: MemoryService):
        """Test retrieving non-existent memory returns None."""
        result = await memory_service.get("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_memory(self, memory_service: MemoryService):
        """Test updating memory."""
        # Store memory
        memory = await memory_service.store(content="Original content")

        # Wait a bit to ensure timestamp difference
        await asyncio.sleep(0.01)

        # Update memory
        updated = await memory_service.update(
            memory.id,
            content="Updated content",
            tags=["updated"],
        )

        assert updated is not None
        assert updated.content == "Updated content"
        assert updated.tags == ["updated"]
        assert updated.updated_at > memory.updated_at

    @pytest.mark.asyncio
    async def test_delete_memory(self, memory_service: MemoryService):
        """Test deleting memory."""
        # Store memory
        memory = await memory_service.store(content="To be deleted")

        # Delete memory
        deleted = await memory_service.delete(memory.id)

        assert len(deleted) > 0
        assert memory.id in deleted

        # Verify deletion
        result = await memory_service.get(memory.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_memories(self, memory_service: MemoryService):
        """Test listing memories."""
        # Store multiple memories
        await memory_service.store(content="Memory 1", memory_tier=MemoryTier.LONG_TERM)
        await memory_service.store(content="Memory 2", memory_tier=MemoryTier.SHORT_TERM)
        await memory_service.store(content="Memory 3", memory_tier=MemoryTier.WORKING)

        # List all memories
        memories, total = await memory_service.list_memories()

        assert len(memories) >= 3
        assert total >= 3

    @pytest.mark.asyncio
    async def test_list_memories_filtered_by_tier(self, memory_service: MemoryService):
        """Test listing memories filtered by tier."""
        # Store memories
        await memory_service.store(content="Long term", memory_tier=MemoryTier.LONG_TERM)
        await memory_service.store(content="Short term", memory_tier=MemoryTier.SHORT_TERM)

        # List only long-term memories
        memories, total = await memory_service.list_memories(memory_tier=MemoryTier.LONG_TERM)

        assert all(m.memory_tier == MemoryTier.LONG_TERM for m in memories)

    @pytest.mark.asyncio
    async def test_search_memories(self, memory_service: MemoryService):
        """Test searching memories."""
        # Store some memories
        await memory_service.store(content="Python is a programming language")
        await memory_service.store(content="JavaScript runs in browsers")
        await memory_service.store(content="The weather is sunny today")

        # Search
        results = await memory_service.search(query="programming", top_k=5)

        assert len(results) > 0
        assert all(hasattr(r, "similarity") for r in results)
        assert all(hasattr(r, "memory") for r in results)

    @pytest.mark.asyncio
    async def test_cleanup_expired_memories(self, memory_service: MemoryService):
        """Test cleaning up expired memories."""
        # Store expired memory (TTL of 1 second)
        memory = await memory_service.store(
            content="Expiring memory",
            memory_tier=MemoryTier.SHORT_TERM,
            ttl_seconds=1,
        )

        # Wait for expiration
        await asyncio.sleep(2)

        # Cleanup
        count = await memory_service.cleanup_expired()

        assert count >= 1

        # Verify memory is gone
        result = await memory_service.get(memory.id)
        assert result is None


class TestAgentService:
    """Test AgentService."""

    @pytest.mark.asyncio
    async def test_register_agent(self, agent_service: AgentService):
        """Test registering an agent."""
        agent = await agent_service.register(
            agent_id="test-agent",
            name="Test Agent",
            description="A test agent",
        )

        assert agent.id == "test-agent"
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent"

    @pytest.mark.asyncio
    async def test_get_agent(self, agent_service: AgentService):
        """Test getting an agent."""
        # Register agent
        await agent_service.register(agent_id="agent-1", name="Agent 1")

        # Get agent
        agent = await agent_service.repository.find_by_id("agent-1")

        assert agent is not None
        assert agent.id == "agent-1"
        assert agent.name == "Agent 1"

    @pytest.mark.asyncio
    async def test_send_direct_message(self, agent_service: AgentService):
        """Test sending a direct message."""
        # Register agents
        await agent_service.register(agent_id="sender", name="Sender")
        await agent_service.register(agent_id="receiver", name="Receiver")

        # Send message
        message = await agent_service.send_message(
            sender_id="sender",
            receiver_id="receiver",
            content="Hello!",
        )

        assert message.sender_id == "sender"
        assert message.receiver_id == "receiver"
        assert message.content == "Hello!"

    @pytest.mark.asyncio
    async def test_receive_messages(self, agent_service: AgentService):
        """Test receiving messages."""
        # Register agents
        await agent_service.register(agent_id="sender", name="Sender")
        await agent_service.register(agent_id="receiver", name="Receiver")

        # Send message
        await agent_service.send_message(
            sender_id="sender",
            receiver_id="receiver",
            content="Test message",
        )

        # Receive messages
        messages = await agent_service.receive_messages(agent_id="receiver")

        assert len(messages) >= 1
        assert any(m.content == "Test message" for m in messages)

    @pytest.mark.asyncio
    async def test_share_context(self, agent_service: AgentService):
        """Test sharing context."""
        # Register agent
        await agent_service.register(agent_id="agent-1", name="Agent 1")

        # Share context
        context = await agent_service.share_context(
            key="test-key",
            value={"data": "value"},
            agent_id="agent-1",
        )

        assert context.key == "test-key"
        assert context.value == {"data": "value"}
        assert context.owner_agent_id == "agent-1"

    @pytest.mark.asyncio
    async def test_read_context(self, agent_service: AgentService):
        """Test reading shared context."""
        # Register agents
        await agent_service.register(agent_id="owner", name="Owner")
        await agent_service.register(agent_id="reader", name="Reader")

        # Share context
        await agent_service.share_context(
            key="shared-data",
            value={"info": "test"},
            agent_id="owner",
        )

        # Read context
        context = await agent_service.read_context(key="shared-data", agent_id="reader")

        assert context is not None
        assert context.value == {"info": "test"}
        assert context.owner_agent_id == "owner"


class TestKnowledgeService:
    """Test KnowledgeService."""

    @pytest.mark.asyncio
    async def test_import_document(self, knowledge_service: KnowledgeService):
        """Test importing a document."""
        long_content = "Python is a programming language. " * 50

        result = await knowledge_service.import_document(
            title="Python Guide",
            content=long_content,
            category="programming",
            chunk_size=500,
            chunk_overlap=50,
        )

        assert result.document_id is not None
        assert result.chunks_created > 0

    @pytest.mark.asyncio
    async def test_query_knowledge(self, knowledge_service: KnowledgeService):
        """Test querying knowledge base."""
        # Import document
        await knowledge_service.import_document(
            title="Python Tutorial",
            content="Python is a high-level programming language. It supports OOP.",
            category="programming",
        )

        # Query
        results = await knowledge_service.query(query="programming language", top_k=5)

        assert len(results) > 0
        assert all(hasattr(r, "similarity") for r in results)
        assert all(hasattr(r, "chunk") for r in results)

    @pytest.mark.asyncio
    async def test_get_document(self, knowledge_service: KnowledgeService):
        """Test getting a document."""
        # Import document
        result = await knowledge_service.import_document(
            title="Test Doc",
            content="Test content here.",
        )

        # Get document
        doc = await knowledge_service.get_document(result.document_id)

        assert doc is not None
        assert doc.title == "Test Doc"

    @pytest.mark.asyncio
    async def test_delete_document(self, knowledge_service: KnowledgeService):
        """Test deleting a document."""
        # Import document
        result = await knowledge_service.import_document(
            title="To Delete",
            content="This will be deleted.",
        )

        # Delete document
        deleted = await knowledge_service.delete_document(result.document_id)

        assert deleted is True

        # Verify deletion
        doc = await knowledge_service.get_document(result.document_id)
        assert doc is None
