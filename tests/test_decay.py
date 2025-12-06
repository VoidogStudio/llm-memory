"""Tests for Memory Decay feature (FR-001)."""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from llm_memory.db.database import Database
from llm_memory.db.repositories.memory_repository import MemoryRepository
from llm_memory.models.memory import Memory, MemoryTier
from llm_memory.services.decay_service import DecayService
from llm_memory.services.embedding_service import EmbeddingService


@pytest_asyncio.fixture
async def decay_service(memory_db: Database, memory_repository: MemoryRepository) -> DecayService:
    """Decay service fixture."""
    return DecayService(repository=memory_repository, db=memory_db)


@pytest_asyncio.fixture
async def sample_memories_for_decay(
    memory_repository: MemoryRepository, embedding_service: EmbeddingService
) -> list[Memory]:
    """Create sample memories with different importance scores and ages."""
    memories = []
    now = datetime.now(timezone.utc)

    # Memory A: Low importance, old (should be deleted)
    mem_a = Memory(
        content="Old unimportant memory A",
        agent_id=None,
        memory_tier=MemoryTier.LONG_TERM,
        importance_score=0.05,
    )
    mem_a = await memory_repository.create(
        mem_a,
        await embedding_service.generate("Old unimportant memory A"),
        use_transaction=False,
    )
    # Update created_at to 8 days ago
    await memory_repository.db.execute(
        "UPDATE memories SET created_at = ? WHERE id = ?",
        ((now - timedelta(days=8)).isoformat(), mem_a.id),
    )
    memories.append(mem_a)

    # Memory B: High importance, old (should NOT be deleted)
    mem_b = Memory(
        content="Old important memory B",
        agent_id=None,
        memory_tier=MemoryTier.LONG_TERM,
        importance_score=0.5,
    )
    mem_b = await memory_repository.create(
        mem_b,
        await embedding_service.generate("Old important memory B"),
        use_transaction=False,
    )
    await memory_repository.db.execute(
        "UPDATE memories SET created_at = ? WHERE id = ?",
        ((now - timedelta(days=8)).isoformat(), mem_b.id),
    )
    memories.append(mem_b)

    # Memory C: Low importance, new (should NOT be deleted - within grace period)
    mem_c = Memory(
        content="New unimportant memory C",
        agent_id=None,
        memory_tier=MemoryTier.LONG_TERM,
        importance_score=0.05,
    )
    mem_c = await memory_repository.create(
        mem_c,
        await embedding_service.generate("New unimportant memory C"),
        use_transaction=False,
    )
    await memory_repository.db.execute(
        "UPDATE memories SET created_at = ? WHERE id = ?",
        ((now - timedelta(days=3)).isoformat(), mem_c.id),
    )
    memories.append(mem_c)

    # Memory D: Low importance, old, with TTL (should NOT be deleted - TTL managed)
    mem_d = Memory(
        content="Old unimportant memory D with TTL",
        agent_id=None,
        memory_tier=MemoryTier.SHORT_TERM,
        importance_score=0.05,
        expires_at=now + timedelta(hours=1),
    )
    mem_d = await memory_repository.create(
        mem_d,
        await embedding_service.generate("Old unimportant memory D with TTL"),
        use_transaction=False,
    )
    await memory_repository.db.execute(
        "UPDATE memories SET created_at = ? WHERE id = ?",
        ((now - timedelta(days=8)).isoformat(), mem_d.id),
    )
    memories.append(mem_d)

    return memories


# DC-001: Decay設定の初期値確認
@pytest.mark.asyncio
async def test_decay_config_default_values(decay_service: DecayService) -> None:
    """Test DC-001: Decay configuration default values."""
    # When: Get status without any prior configuration
    status = await decay_service.status()

    # Then: Default configuration should be returned
    assert status["config"]["enabled"] is False
    assert status["config"]["threshold"] == 0.1
    assert status["config"]["grace_period_days"] == 7
    assert status["config"]["max_delete_per_run"] == 100
    assert status["config"]["auto_run_interval_hours"] == 24


# DC-002: Decay設定の更新
@pytest.mark.asyncio
async def test_decay_config_update(decay_service: DecayService) -> None:
    """Test DC-002: Update decay configuration."""
    # Given: Default configuration exists
    await decay_service.status()

    # When: Update configuration
    config = await decay_service.configure(threshold=0.2, grace_period_days=14)

    # Then: Configuration should be updated
    assert config.threshold == 0.2
    assert config.grace_period_days == 14
    # Other fields should remain default
    assert config.enabled is False
    assert config.max_delete_per_run == 100


# DC-003: Decay設定のバリデーションエラー
@pytest.mark.asyncio
async def test_decay_config_validation_error(decay_service: DecayService) -> None:
    """Test DC-003: Decay configuration validation errors."""
    # When/Then: Invalid threshold should raise ValueError
    with pytest.raises(ValueError, match="threshold must be between 0.0 and 1.0"):
        await decay_service.configure(threshold=1.5)

    with pytest.raises(ValueError, match="threshold must be between 0.0 and 1.0"):
        await decay_service.configure(threshold=-0.1)

    # Invalid grace_period_days
    with pytest.raises(ValueError, match="grace_period_days must be >= 1"):
        await decay_service.configure(grace_period_days=0)

    # Invalid max_delete_per_run
    with pytest.raises(ValueError, match="max_delete_per_run must be between 1 and 10000"):
        await decay_service.configure(max_delete_per_run=0)

    with pytest.raises(ValueError, match="max_delete_per_run must be between 1 and 10000"):
        await decay_service.configure(max_delete_per_run=15000)


# DC-004: Dry run による削除候補の確認
@pytest.mark.asyncio
async def test_decay_dry_run(
    decay_service: DecayService,
    sample_memories_for_decay: list[Memory],
) -> None:
    """Test DC-004: Dry run to identify deletion candidates."""
    # Given: Memories with different ages and importance scores
    mem_a, mem_b, mem_c, mem_d = sample_memories_for_decay

    # When: Run decay with dry_run=True
    result = await decay_service.run(
        threshold=0.1, grace_period_days=7, dry_run=True
    )

    # Then: Only memory A should be identified as candidate
    assert result.dry_run is True
    assert result.deleted_count == 1
    assert mem_a.id in result.deleted_ids
    # Memory B excluded (high importance)
    assert mem_b.id not in result.deleted_ids
    # Memory C excluded (within grace period)
    assert mem_c.id not in result.deleted_ids
    # Memory D excluded (has TTL)
    assert mem_d.id not in result.deleted_ids

    # Verify no actual deletion occurred
    cursor = await decay_service.db.execute("SELECT COUNT(*) as count FROM memories")
    row = await cursor.fetchone()
    assert row["count"] == 4


# DC-005: 実際の Decay 実行
@pytest.mark.asyncio
async def test_decay_run_actual_deletion(
    decay_service: DecayService,
    sample_memories_for_decay: list[Memory],
    memory_repository: MemoryRepository,
) -> None:
    """Test DC-005: Actual decay execution with deletion."""
    # Given: Memories with links and embeddings
    mem_a, mem_b, mem_c, mem_d = sample_memories_for_decay

    # When: Run decay with dry_run=False
    result = await decay_service.run(
        threshold=0.1, grace_period_days=7, dry_run=False, use_transaction=False
    )

    # Then: Memory A should be deleted
    assert result.dry_run is False
    assert result.deleted_count == 1
    assert mem_a.id in result.deleted_ids

    # Verify memory A is deleted
    deleted_memory = await memory_repository.find_by_id(mem_a.id)
    assert deleted_memory is None

    # Verify other memories still exist
    assert await memory_repository.find_by_id(mem_b.id) is not None
    assert await memory_repository.find_by_id(mem_c.id) is not None
    assert await memory_repository.find_by_id(mem_d.id) is not None

    # Verify decay log was created
    cursor = await decay_service.db.execute("SELECT COUNT(*) as count FROM decay_log")
    row = await cursor.fetchone()
    assert row["count"] == 1

    # Verify last_run_at was updated
    status = await decay_service.status()
    assert status["config"]["last_run_at"] is not None


# DC-006: Max delete による削除数制限
@pytest.mark.asyncio
async def test_decay_max_delete_limit(
    decay_service: DecayService,
    memory_repository: MemoryRepository,
    embedding_service: EmbeddingService,
) -> None:
    """Test DC-006: Max delete limit enforcement."""
    # Given: Create 150 low importance, old memories
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=8)

    for i in range(150):
        mem = Memory(
            content=f"Low importance memory {i}",
            agent_id=None,
            memory_tier=MemoryTier.LONG_TERM,
            importance_score=0.05,
        )
        mem = await memory_repository.create(
            mem,
            await embedding_service.generate(f"Low importance memory {i}"),
            use_transaction=False,
        )
        await memory_repository.db.execute(
            "UPDATE memories SET created_at = ? WHERE id = ?",
            (old_date.isoformat(), mem.id),
        )

    # When: Run decay with max_delete=50
    result = await decay_service.run(
        threshold=0.1, grace_period_days=7, max_delete=50, dry_run=False, use_transaction=False
    )

    # Then: Only 50 should be deleted
    assert result.deleted_count == 50
    assert len(result.deleted_ids) == 50

    # Verify 100 memories remain
    cursor = await decay_service.db.execute("SELECT COUNT(*) as count FROM memories")
    row = await cursor.fetchone()
    assert row["count"] == 100


# DC-007: TTL設定済みメモリの除外
@pytest.mark.asyncio
async def test_decay_excludes_ttl_memories(
    decay_service: DecayService,
    sample_memories_for_decay: list[Memory],
) -> None:
    """Test DC-007: Exclude memories with TTL from decay."""
    # Given: Memory D has TTL set
    mem_a, mem_b, mem_c, mem_d = sample_memories_for_decay

    # When: Run decay in dry run mode
    result = await decay_service.run(
        threshold=0.1, grace_period_days=7, dry_run=True
    )

    # Then: Memory D should not be in candidates (TTL managed)
    assert mem_d.id not in result.deleted_ids
    # Only memory A should be candidate
    assert result.deleted_count == 1
    assert mem_a.id in result.deleted_ids


# DC-008: Decay統計情報の取得
@pytest.mark.asyncio
async def test_decay_status_statistics(
    decay_service: DecayService,
    sample_memories_for_decay: list[Memory],
) -> None:
    """Test DC-008: Get decay statistics."""
    # Given: Run decay multiple times to create history
    await decay_service.run(threshold=0.1, grace_period_days=7, dry_run=False, use_transaction=False)
    await decay_service.run(threshold=0.15, grace_period_days=7, dry_run=False, use_transaction=False)

    # When: Get status
    status = await decay_service.status()

    # Then: Statistics should be present
    assert "statistics" in status
    stats = status["statistics"]

    assert "total_memories" in stats
    assert stats["total_memories"] >= 0

    assert "decay_candidates" in stats
    assert stats["decay_candidates"] >= 0

    assert "last_run" in stats
    assert stats["last_run"] is not None
    assert stats["last_run"]["deleted_count"] >= 0

    assert "total_deleted" in stats
    assert stats["total_deleted"] >= 1  # At least memory A was deleted
