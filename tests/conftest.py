"""Pytest configuration and fixtures for llm-memory tests."""

import asyncio
import os
import tempfile
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

# Use pysqlite3 if available (Python 3.14+ compatibility)
try:
    import pysqlite3 as sqlite3  # noqa: F401
except ImportError:
    pass

import aiosqlite
import pytest
import pytest_asyncio

# Configure aiosqlite to use pysqlite3 if available
try:
    import pysqlite3  # noqa: F401

    aiosqlite.core.sqlite3 = pysqlite3
except ImportError:
    pass

from llm_memory.config.settings import Settings
from llm_memory.db.database import Database
from llm_memory.db.repositories.agent_repository import AgentRepository
from llm_memory.db.repositories.knowledge_repository import KnowledgeRepository
from llm_memory.db.repositories.memory_repository import MemoryRepository
from llm_memory.embeddings.base import EmbeddingProvider
from llm_memory.services.agent_service import AgentService
from llm_memory.services.decay_service import DecayService
from llm_memory.services.embedding_service import EmbeddingService
from llm_memory.services.export_import_service import ExportImportService
from llm_memory.services.knowledge_service import KnowledgeService
from llm_memory.services.linking_service import LinkingService
from llm_memory.services.memory_service import MemoryService
from llm_memory.services.namespace_service import NamespaceService


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Test configuration settings."""
    return Settings(
        database_path=":memory:",
        embedding_provider="local",
        embedding_model="all-MiniLM-L6-v2",
        embedding_dimensions=384,
        short_term_ttl_seconds=3600,
        embedding_batch_size=32,
        search_default_top_k=10,
        log_level="INFO",
    )


@pytest_asyncio.fixture
async def temp_db_path() -> AsyncIterator[str]:
    """Create temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest_asyncio.fixture
async def memory_db() -> AsyncIterator[Database]:
    """In-memory database for fast tests."""
    db = Database(database_path=":memory:", embedding_dimensions=384)
    await db.connect()
    await db.migrate()

    yield db

    await db.close()


@pytest_asyncio.fixture
async def temp_db(temp_db_path: str) -> AsyncIterator[Database]:
    """Temporary file-based database."""
    db = Database(database_path=temp_db_path, embedding_dimensions=384)
    await db.connect()
    await db.migrate()

    yield db

    await db.close()


@pytest.fixture
def mock_embedding_provider() -> EmbeddingProvider:
    """Mock embedding provider for fast tests."""
    mock = AsyncMock(spec=EmbeddingProvider)
    mock.embed.return_value = [0.1] * 384

    # Make embed_batch return the same number of embeddings as input texts
    async def embed_batch_side_effect(texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]

    mock.embed_batch.side_effect = embed_batch_side_effect
    mock.dimensions.return_value = 384
    return mock


@pytest_asyncio.fixture
async def embedding_service(mock_embedding_provider: EmbeddingProvider) -> EmbeddingService:
    """Embedding service with mock provider."""
    return EmbeddingService(provider=mock_embedding_provider)


@pytest_asyncio.fixture
async def memory_repository(memory_db: Database) -> MemoryRepository:
    """Memory repository."""
    return MemoryRepository(db=memory_db)


@pytest_asyncio.fixture
async def agent_repository(memory_db: Database) -> AgentRepository:
    """Agent repository."""
    return AgentRepository(db=memory_db)


@pytest_asyncio.fixture
async def knowledge_repository(memory_db: Database) -> KnowledgeRepository:
    """Knowledge repository."""
    return KnowledgeRepository(db=memory_db)


@pytest_asyncio.fixture
async def namespace_service(test_settings: Settings) -> NamespaceService:
    """Namespace service."""
    return NamespaceService(settings=test_settings)


@pytest_asyncio.fixture
async def memory_service(
    memory_repository: MemoryRepository,
    embedding_service: EmbeddingService,
    namespace_service: NamespaceService,
) -> MemoryService:
    """Memory service."""
    return MemoryService(
        repository=memory_repository,
        embedding_service=embedding_service,
        namespace_service=namespace_service,
    )


@pytest_asyncio.fixture
async def agent_service(agent_repository: AgentRepository) -> AgentService:
    """Agent service."""
    return AgentService(repository=agent_repository)


@pytest_asyncio.fixture
async def knowledge_service(
    knowledge_repository: KnowledgeRepository, embedding_service: EmbeddingService
) -> KnowledgeService:
    """Knowledge service."""
    return KnowledgeService(
        repository=knowledge_repository, embedding_service=embedding_service
    )


@pytest_asyncio.fixture
async def decay_service(memory_db: Database, memory_repository: MemoryRepository) -> DecayService:
    """Decay service."""
    return DecayService(repository=memory_repository, db=memory_db)


@pytest_asyncio.fixture
async def linking_service(
    memory_db: Database, memory_repository: MemoryRepository
) -> LinkingService:
    """Linking service."""
    return LinkingService(repository=memory_repository, db=memory_db)


@pytest_asyncio.fixture
async def export_import_service(
    memory_db: Database,
    memory_repository: MemoryRepository,
    knowledge_repository: KnowledgeRepository,
    agent_repository: AgentRepository,
    embedding_service: EmbeddingService,
) -> ExportImportService:
    """Export/Import service."""
    from pathlib import Path

    return ExportImportService(
        memory_repository=memory_repository,
        knowledge_repository=knowledge_repository,
        agent_repository=agent_repository,
        db=memory_db,
        embedding_service=embedding_service,
        allowed_paths=[Path(tempfile.gettempdir())],
    )


# Helper functions for tests


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (0-1)
    """
    import math

    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)
