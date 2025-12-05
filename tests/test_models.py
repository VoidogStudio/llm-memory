"""Tests for data models."""

import uuid
from datetime import datetime, timezone

import pytest

from llm_memory.models.agent import AccessLevel, Agent, Message, MessageStatus, MessageType, SharedContext
from llm_memory.models.knowledge import Chunk, Document
from llm_memory.models.memory import ContentType, Memory, MemoryCreate, MemoryTier, MemoryUpdate, SearchResult


class TestMemoryModels:
    """Test Memory model classes."""

    def test_memory_creation_with_defaults(self):
        """Test creating memory with default values."""
        memory = Memory(content="Test content")

        assert memory.content == "Test content"
        assert memory.content_type == ContentType.TEXT
        assert memory.memory_tier == MemoryTier.LONG_TERM
        assert memory.tags == []
        assert memory.metadata == {}
        assert memory.agent_id is None
        assert memory.expires_at is None
        assert isinstance(memory.id, str)
        assert isinstance(memory.created_at, datetime)
        assert isinstance(memory.updated_at, datetime)

    def test_memory_creation_with_custom_values(self):
        """Test creating memory with custom values."""
        now = datetime.now(timezone.utc)
        memory = Memory(
            id="custom-id",
            content="Code snippet",
            content_type=ContentType.CODE,
            memory_tier=MemoryTier.WORKING,
            tags=["python", "function"],
            metadata={"language": "python"},
            agent_id="agent-1",
            created_at=now,
            updated_at=now,
            expires_at=now,
        )

        assert memory.id == "custom-id"
        assert memory.content == "Code snippet"
        assert memory.content_type == ContentType.CODE
        assert memory.memory_tier == MemoryTier.WORKING
        assert memory.tags == ["python", "function"]
        assert memory.metadata == {"language": "python"}
        assert memory.agent_id == "agent-1"
        assert memory.expires_at == now

    def test_memory_create_model(self):
        """Test MemoryCreate model."""
        create_req = MemoryCreate(
            content="Test",
            content_type=ContentType.JSON,
            memory_tier=MemoryTier.SHORT_TERM,
            tags=["test"],
            metadata={"key": "value"},
            agent_id="agent-1",
            ttl_seconds=3600,
        )

        assert create_req.content == "Test"
        assert create_req.content_type == ContentType.JSON
        assert create_req.memory_tier == MemoryTier.SHORT_TERM
        assert create_req.tags == ["test"]
        assert create_req.metadata == {"key": "value"}
        assert create_req.agent_id == "agent-1"
        assert create_req.ttl_seconds == 3600

    def test_memory_update_model(self):
        """Test MemoryUpdate model with partial updates."""
        update_req = MemoryUpdate(
            content="Updated content",
            tags=["updated"],
        )

        assert update_req.content == "Updated content"
        assert update_req.tags == ["updated"]
        assert update_req.metadata is None
        assert update_req.memory_tier is None

    def test_search_result_model(self):
        """Test SearchResult model."""
        memory = Memory(content="Test")
        result = SearchResult(memory=memory, similarity=0.95)

        assert result.memory == memory
        assert result.similarity == 0.95

    def test_memory_tier_enum(self):
        """Test MemoryTier enum values."""
        assert MemoryTier.SHORT_TERM == "short_term"
        assert MemoryTier.LONG_TERM == "long_term"
        assert MemoryTier.WORKING == "working"

    def test_content_type_enum(self):
        """Test ContentType enum values."""
        assert ContentType.TEXT == "text"
        assert ContentType.IMAGE == "image"
        assert ContentType.CODE == "code"
        assert ContentType.JSON == "json"
        assert ContentType.YAML == "yaml"


class TestAgentModels:
    """Test Agent model classes."""

    def test_agent_creation(self):
        """Test creating an agent."""
        now = datetime.now(timezone.utc)
        agent = Agent(
            id="agent-1",
            name="Test Agent",
            description="A test agent",
            metadata={"role": "tester"},
            created_at=now,
            last_active_at=now,
        )

        assert agent.id == "agent-1"
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent"
        assert agent.metadata == {"role": "tester"}

    def test_message_creation(self):
        """Test creating a message."""
        now = datetime.now(timezone.utc)
        message = Message(
            id="msg-1",
            sender_id="agent-1",
            receiver_id="agent-2",
            content="Hello",
            message_type=MessageType.DIRECT,
            status=MessageStatus.PENDING,
            metadata={},
            created_at=now,
            read_at=None,
        )

        assert message.id == "msg-1"
        assert message.sender_id == "agent-1"
        assert message.receiver_id == "agent-2"
        assert message.content == "Hello"
        assert message.message_type == MessageType.DIRECT
        assert message.status == MessageStatus.PENDING

    def test_shared_context_creation(self):
        """Test creating shared context."""
        now = datetime.now(timezone.utc)
        context = SharedContext(
            id="ctx-1",
            key="shared-data",
            value={"data": "value"},
            owner_agent_id="agent-1",
            access_level=AccessLevel.PUBLIC,
            allowed_agents=[],
            created_at=now,
            updated_at=now,
        )

        assert context.id == "ctx-1"
        assert context.key == "shared-data"
        assert context.value == {"data": "value"}
        assert context.owner_agent_id == "agent-1"
        assert context.access_level == AccessLevel.PUBLIC


class TestKnowledgeModels:
    """Test Knowledge model classes."""

    def test_document_creation(self):
        """Test creating a document."""
        now = datetime.now(timezone.utc)
        doc = Document(
            id="doc-1",
            title="Test Document",
            source="https://example.com",
            category="test",
            version=1,
            metadata={"author": "tester"},
            created_at=now,
            updated_at=now,
        )

        assert doc.id == "doc-1"
        assert doc.title == "Test Document"
        assert doc.source == "https://example.com"
        assert doc.category == "test"
        assert doc.version == 1

    def test_chunk_creation(self):
        """Test creating a chunk."""
        chunk = Chunk(
            id="chunk-1",
            document_id="doc-1",
            content="This is a test chunk.",
            chunk_index=0,
            metadata={"length": 22},
        )

        assert chunk.id == "chunk-1"
        assert chunk.document_id == "doc-1"
        assert chunk.content == "This is a test chunk."
        assert chunk.chunk_index == 0
