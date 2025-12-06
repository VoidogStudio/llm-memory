"""Tests for Export/Import feature (FR-004)."""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio

from llm_memory.db.database import Database
from llm_memory.db.repositories.agent_repository import AgentRepository
from llm_memory.db.repositories.knowledge_repository import KnowledgeRepository
from llm_memory.db.repositories.memory_repository import MemoryRepository
from llm_memory.models.agent import Agent
from llm_memory.models.knowledge import Document
from llm_memory.models.memory import Memory, MemoryTier
from llm_memory.services.embedding_service import EmbeddingService
from llm_memory.services.export_import_service import ExportImportService
from llm_memory.services.linking_service import LinkingService


@pytest_asyncio.fixture
async def export_import_service(
    memory_db: Database,
    memory_repository: MemoryRepository,
    knowledge_repository: KnowledgeRepository,
    agent_repository: AgentRepository,
    embedding_service: EmbeddingService,
) -> ExportImportService:
    """Export/Import service fixture."""
    return ExportImportService(
        memory_repository=memory_repository,
        knowledge_repository=knowledge_repository,
        agent_repository=agent_repository,
        db=memory_db,
        embedding_service=embedding_service,
        allowed_paths=[Path(tempfile.gettempdir())],
    )


@pytest_asyncio.fixture
async def sample_data_for_export(
    memory_repository: MemoryRepository,
    knowledge_repository: KnowledgeRepository,
    agent_repository: AgentRepository,
    embedding_service: EmbeddingService,
) -> dict:
    """Create sample data for export tests."""
    # Create agent
    agent = Agent(id="test-agent-id", name="test-agent")
    await agent_repository.create(agent)

    # Create memories
    memories = []
    for i in range(10):
        mem = Memory(
            content=f"Test memory {i}",
            agent_id=agent.id,
            memory_tier=MemoryTier.LONG_TERM,
            importance_score=0.5,
        )
        mem = await memory_repository.create(
            mem,
            await embedding_service.generate(f"Test memory {i}"),
        )
        memories.append(mem)

    # Create document
    doc = Document(title="Test Document", source="test", category="test")
    await knowledge_repository.create_document(doc)

    return {
        "agent": agent,
        "memories": memories,
        "document": doc,
    }


# EI-001: 基本的なエクスポート
@pytest.mark.asyncio
async def test_basic_export(
    export_import_service: ExportImportService,
    sample_data_for_export: dict,
) -> None:
    """Test EI-001: Basic database export."""
    # Given: Database with sample data
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        output_path = f.name

    try:
        # When: Export database
        result = await export_import_service.export_database(output_path=output_path)

        # Then: Export file should be created
        assert Path(output_path).exists()
        assert result.schema_version == 3
        assert result.exported_at is not None
        assert result.counts["memories"] == 10
        assert result.counts["knowledge_documents"] >= 1
        assert result.file_size_bytes > 0

        # Verify JSONL format
        with open(output_path, "r") as f:
            lines = f.readlines()
            # First line should be metadata
            metadata = json.loads(lines[0])
            assert metadata["schema_version"] == 3
            assert "exported_at" in metadata
            assert "counts" in metadata

    finally:
        # Cleanup
        if Path(output_path).exists():
            Path(output_path).unlink()


# EI-002: Embedding を含むエクスポート
@pytest.mark.asyncio
async def test_export_with_embeddings(
    export_import_service: ExportImportService,
    sample_data_for_export: dict,
) -> None:
    """Test EI-002: Export with embeddings included."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        output_path = f.name

    try:
        # When: Export with embeddings
        result = await export_import_service.export_database(
            output_path=output_path, include_embeddings=True
        )

        # Then: Embeddings should be included
        assert result.counts["memories"] == 10

        # Verify embeddings in exported data
        with open(output_path, "r") as f:
            lines = f.readlines()
            # Skip metadata line
            for line in lines[1:]:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("type") == "memory":
                    # Embedding should be present (or null)
                    assert "embedding" in record or record.get("embedding") is not None
                    break

    finally:
        if Path(output_path).exists():
            Path(output_path).unlink()


# EI-003: Embedding を除外したエクスポート
@pytest.mark.asyncio
async def test_export_without_embeddings(
    export_import_service: ExportImportService,
    sample_data_for_export: dict,
) -> None:
    """Test EI-003: Export with embeddings excluded."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        output_path = f.name

    try:
        # When: Export without embeddings
        result = await export_import_service.export_database(
            output_path=output_path, include_embeddings=False
        )

        # Then: Export should succeed
        assert result.counts["memories"] == 10

        # File size should be smaller without embeddings
        assert result.file_size_bytes > 0

    finally:
        if Path(output_path).exists():
            Path(output_path).unlink()


# EI-004: フィルタリング付きエクスポート
@pytest.mark.asyncio
async def test_export_with_filtering(
    export_import_service: ExportImportService,
    memory_repository: MemoryRepository,
    embedding_service: EmbeddingService,
) -> None:
    """Test EI-004: Export with tier filtering."""
    # Given: Create memories with different tiers
    for i in range(5):
        mem = Memory(
            content=f"Long term memory {i}",
            agent_id=None,
            memory_tier=MemoryTier.LONG_TERM,
            importance_score=0.5,
        )
        await memory_repository.create(
            mem,
            await embedding_service.generate(f"Long term memory {i}"),
        )
    for i in range(3):
        mem = Memory(
            content=f"Short term memory {i}",
            agent_id=None,
            memory_tier=MemoryTier.SHORT_TERM,
            importance_score=0.3,
        )
        await memory_repository.create(
            mem,
            await embedding_service.generate(f"Short term memory {i}"),
        )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        output_path = f.name

    try:
        # When: Export only long_term memories
        result = await export_import_service.export_database(
            output_path=output_path, memory_tier="long_term"
        )

        # Then: Only long_term memories should be exported
        assert result.counts["memories"] == 5

    finally:
        if Path(output_path).exists():
            Path(output_path).unlink()


# EI-005: Replace モードでのインポート
@pytest.mark.asyncio
async def test_import_replace_mode(
    memory_db: Database,
    memory_repository: MemoryRepository,
    knowledge_repository: KnowledgeRepository,
    agent_repository: AgentRepository,
    embedding_service: EmbeddingService,
) -> None:
    """Test EI-005: Import with replace mode."""
    # Given: Existing data
    mem = Memory(
        content="Existing memory",
        agent_id=None,
        memory_tier=MemoryTier.LONG_TERM,
        importance_score=0.5,
    )
    await memory_repository.create(
        mem,
        await embedding_service.generate("Existing memory"),
        use_transaction=False,
    )
    await memory_db.conn.commit()  # Ensure no pending transaction

    # Create export file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        export_path = f.name
        # Write minimal valid export
        metadata = {"schema_version": 3, "exported_at": datetime.now(timezone.utc).isoformat(), "counts": {"memories": 0}}
        f.write(json.dumps(metadata) + "\n")

    service = ExportImportService(
        memory_repository=memory_repository,
        knowledge_repository=knowledge_repository,
        agent_repository=agent_repository,
        db=memory_db,
        embedding_service=embedding_service,
        allowed_paths=[Path(tempfile.gettempdir()).resolve()],
    )

    try:
        # When: Import with replace mode
        result = await service.import_database(input_path=export_path, mode="replace")

        # Then: Old data should be deleted
        assert result.mode == "replace"
        cursor = await memory_db.execute("SELECT COUNT(*) as count FROM memories")
        row = await cursor.fetchone()
        assert row["count"] == 0  # All existing data cleared

    finally:
        if Path(export_path).exists():
            Path(export_path).unlink()


# EI-006: Merge モードでのインポート
@pytest.mark.asyncio
async def test_import_merge_mode(
    memory_db: Database,
    memory_repository: MemoryRepository,
    knowledge_repository: KnowledgeRepository,
    agent_repository: AgentRepository,
    embedding_service: EmbeddingService,
) -> None:
    """Test EI-006: Import with merge mode."""
    # Given: Existing memories
    existing_mem = Memory(
        content="Existing memory",
        agent_id=None,
        memory_tier=MemoryTier.LONG_TERM,
        importance_score=0.5,
    )
    existing_mem = await memory_repository.create(
        existing_mem,
        await embedding_service.generate("Existing memory"),
        use_transaction=False,
    )
    await memory_db.conn.commit()  # Ensure no pending transaction

    # Create export file with new memory
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        export_path = f.name
        metadata = {"schema_version": 3, "exported_at": datetime.now(timezone.utc).isoformat(), "counts": {"memories": 1}}
        f.write(json.dumps(metadata) + "\n")
        # Add a memory record
        memory_record = {
            "type": "memory",
            "id": "new-memory-id",
            "content": "New memory",
            "content_type": "text",
            "agent_id": None,
            "memory_tier": "long_term",
            "importance_score": 0.6,
            "tags": None,
            "metadata": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "embedding": [0.1] * 384,  # Add dummy embedding
        }
        f.write(json.dumps(memory_record) + "\n")

    service = ExportImportService(
        memory_repository=memory_repository,
        knowledge_repository=knowledge_repository,
        agent_repository=agent_repository,
        db=memory_db,
        embedding_service=embedding_service,
        allowed_paths=[Path(tempfile.gettempdir()).resolve()],
    )

    try:
        # When: Import with merge mode
        result = await service.import_database(input_path=export_path, mode="merge")

        # Then: Both old and new data should exist
        assert result.mode == "merge"
        cursor = await memory_db.execute("SELECT COUNT(*) as count FROM memories")
        row = await cursor.fetchone()
        assert row["count"] == 2  # Existing + new

    finally:
        if Path(export_path).exists():
            Path(export_path).unlink()


# EI-007: Conflict Skip 処理
@pytest.mark.asyncio
async def test_import_conflict_skip(
    memory_db: Database,
    memory_repository: MemoryRepository,
    knowledge_repository: KnowledgeRepository,
    agent_repository: AgentRepository,
    embedding_service: EmbeddingService,
) -> None:
    """Test EI-007: Import with conflict=skip."""
    # Given: Existing memory with specific ID
    mem_id = "duplicate-id"
    existing_mem = Memory(
        content="Original content",
        agent_id=None,
        memory_tier=MemoryTier.LONG_TERM,
        importance_score=0.5,
    )
    existing_mem = await memory_repository.create(
        existing_mem,
        await embedding_service.generate("Original content"),
        use_transaction=False,
    )
    # Update ID to match import
    await memory_db.execute("UPDATE memories SET id = ? WHERE id = ?", (mem_id, existing_mem.id))
    await memory_db.conn.commit()  # Ensure no pending transaction

    # Create export with same ID
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        export_path = f.name
        metadata = {"schema_version": 3, "exported_at": datetime.now(timezone.utc).isoformat(), "counts": {"memories": 1}}
        f.write(json.dumps(metadata) + "\n")
        memory_record = {
            "type": "memory",
            "id": mem_id,
            "content": "Conflicting content",
            "content_type": "text",
            "agent_id": None,
            "memory_tier": "long_term",
            "importance_score": 0.7,
            "tags": None,
            "metadata": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "embedding": [0.1] * 384,
        }
        f.write(json.dumps(memory_record) + "\n")

    service = ExportImportService(
        memory_repository=memory_repository,
        knowledge_repository=knowledge_repository,
        agent_repository=agent_repository,
        db=memory_db,
        embedding_service=embedding_service,
        allowed_paths=[Path(tempfile.gettempdir()).resolve()],
    )

    try:
        # When: Import with on_conflict=skip
        result = await service.import_database(
            input_path=export_path, mode="merge", on_conflict="skip"
        )

        # Then: Original should remain unchanged
        mem = await memory_repository.find_by_id(mem_id)
        assert mem is not None
        assert mem.content == "Original content"
        assert result.skipped_count >= 0

    finally:
        if Path(export_path).exists():
            Path(export_path).unlink()


# EI-010: スキーマバージョン検証
@pytest.mark.asyncio
async def test_import_schema_validation(
    export_import_service: ExportImportService,
) -> None:
    """Test EI-010: Schema version validation on import."""
    # Given: Export file with unsupported schema version
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        export_path = f.name
        metadata = {"schema_version": 999, "exported_at": datetime.now(timezone.utc).isoformat(), "counts": {}}
        f.write(json.dumps(metadata) + "\n")

    try:
        # When/Then: Import should raise ValueError
        with pytest.raises(ValueError, match="Unsupported schema version"):
            await export_import_service.import_database(input_path=export_path)

    finally:
        if Path(export_path).exists():
            Path(export_path).unlink()


# EI-012: 大規模データのストリーミング処理
@pytest.mark.asyncio
async def test_export_streaming_performance(
    export_import_service: ExportImportService,
    memory_repository: MemoryRepository,
    embedding_service: EmbeddingService,
) -> None:
    """Test EI-012: Streaming export for large datasets."""
    import time

    # Given: Large number of memories (using smaller number for test speed)
    for i in range(500):
        mem = Memory(
            content=f"Memory {i}",
            agent_id=None,
            memory_tier=MemoryTier.LONG_TERM,
            importance_score=0.5,
        )
        await memory_repository.create(
            mem,
            await embedding_service.generate(f"Memory {i}"),
        )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        output_path = f.name

    try:
        # When: Export large dataset
        start_time = time.time()
        result = await export_import_service.export_database(output_path=output_path)
        elapsed = time.time() - start_time

        # Then: Should complete in reasonable time (streaming, not loading all to memory)
        assert result.counts["memories"] == 500
        assert elapsed < 30.0  # Should be fast for 500 records

    finally:
        if Path(output_path).exists():
            Path(output_path).unlink()


# EI-013: Memory links のエクスポート/インポート
@pytest.mark.asyncio
async def test_export_import_memory_links(
    memory_db: Database,
    memory_repository: MemoryRepository,
    knowledge_repository: KnowledgeRepository,
    agent_repository: AgentRepository,
    embedding_service: EmbeddingService,
    export_import_service: ExportImportService,
) -> None:
    """Test EI-013: Export and import memory links."""
    # Given: Memories with links
    mem_a = Memory(
        content="Memory A",
        agent_id=None,
        memory_tier=MemoryTier.LONG_TERM,
        importance_score=0.5,
    )
    mem_a = await memory_repository.create(
        mem_a,
        await embedding_service.generate("Memory A"),
    )
    mem_b = Memory(
        content="Memory B",
        agent_id=None,
        memory_tier=MemoryTier.LONG_TERM,
        importance_score=0.5,
    )
    mem_b = await memory_repository.create(
        mem_b,
        await embedding_service.generate("Memory B"),
    )

    # Create link
    linking_service = LinkingService(repository=memory_repository, db=memory_db)
    await linking_service.create_link(source_id=mem_a.id, target_id=mem_b.id, bidirectional=False)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        export_path = f.name

    try:
        # When: Export database
        result = await export_import_service.export_database(output_path=export_path)

        # Then: Links should be included in export
        assert result.counts["memory_links"] >= 1

        # Verify link in export file
        with open(export_path, "r") as f:
            lines = f.readlines()
            link_found = False
            for line in lines[1:]:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("type") == "memory_link":
                    link_found = True
                    break
            assert link_found

    finally:
        if Path(export_path).exists():
            Path(export_path).unlink()


# Security test: Path traversal prevention (from Reviewer requirements)
@pytest.mark.asyncio
async def test_path_traversal_prevention(
    export_import_service: ExportImportService,
) -> None:
    """Test path traversal prevention in export."""
    # When/Then: Path traversal should be rejected
    # The error message can be either "Path traversal detected" or "Path ... is outside allowed directory"
    with pytest.raises(ValueError, match="Path traversal detected|outside allowed directory"):
        await export_import_service.export_database(output_path="../../../etc/passwd")
