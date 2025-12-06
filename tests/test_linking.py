"""Tests for Memory Linking feature (FR-002)."""

import pytest
import pytest_asyncio

from src.db.database import Database
from src.db.repositories.memory_repository import MemoryRepository
from src.models.linking import LinkType
from src.models.memory import Memory, MemoryTier
from src.services.embedding_service import EmbeddingService
from src.services.linking_service import LinkingService


@pytest_asyncio.fixture
async def linking_service(memory_db: Database, memory_repository: MemoryRepository) -> LinkingService:
    """Linking service fixture."""
    return LinkingService(repository=memory_repository, db=memory_db)


@pytest_asyncio.fixture
async def sample_memories_for_linking(
    memory_repository: MemoryRepository, embedding_service: EmbeddingService
) -> list[Memory]:
    """Create sample memories for linking tests."""
    memories = []

    for i in range(5):
        mem = Memory(
            content=f"Test memory {chr(65 + i)}",  # A, B, C, D, E
            agent_id=None,
            memory_tier=MemoryTier.LONG_TERM,
            importance_score=0.5,
        )
        mem = await memory_repository.create(
            mem,
            await embedding_service.generate(f"Test memory {chr(65 + i)}"),
        )
        memories.append(mem)

    return memories


# LK-001: 基本的なリンク作成
@pytest.mark.asyncio
async def test_basic_link_creation(
    linking_service: LinkingService,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-001: Basic link creation."""
    # Given: Two memories exist
    mem_a, mem_b = sample_memories_for_linking[0], sample_memories_for_linking[1]

    # When: Create link between them
    link = await linking_service.create_link(
        source_id=mem_a.id, target_id=mem_b.id, link_type=LinkType.RELATED, bidirectional=False
    )

    # Then: Link should be created with correct properties
    assert link.id is not None
    assert link.source_id == mem_a.id
    assert link.target_id == mem_b.id
    assert link.link_type == LinkType.RELATED
    assert link.created_at is not None


# LK-002: 双方向リンクの自動作成
@pytest.mark.asyncio
async def test_bidirectional_link_creation(
    linking_service: LinkingService,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-002: Bidirectional link automatic creation."""
    # Given: Two memories exist
    mem_a, mem_b = sample_memories_for_linking[0], sample_memories_for_linking[1]

    # When: Create bidirectional link
    link = await linking_service.create_link(
        source_id=mem_a.id,
        target_id=mem_b.id,
        link_type=LinkType.RELATED,
        bidirectional=True,
    )

    # Then: Both directions should exist
    # Check A -> B link
    cursor = await linking_service.db.execute(
        "SELECT * FROM memory_links WHERE source_id = ? AND target_id = ?",
        (mem_a.id, mem_b.id),
    )
    row_ab = await cursor.fetchone()
    assert row_ab is not None
    assert row_ab["link_type"] == LinkType.RELATED.value

    # Check B -> A link
    cursor = await linking_service.db.execute(
        "SELECT * FROM memory_links WHERE source_id = ? AND target_id = ?",
        (mem_b.id, mem_a.id),
    )
    row_ba = await cursor.fetchone()
    assert row_ba is not None
    assert row_ba["link_type"] == LinkType.RELATED.value


# LK-003: Parent/Child リンクの反転
@pytest.mark.asyncio
async def test_parent_child_link_reversal(
    linking_service: LinkingService,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-003: Parent/Child link type reversal."""
    # Given: Two memories (parent and child)
    mem_parent, mem_child = sample_memories_for_linking[0], sample_memories_for_linking[1]

    # When: Create parent link with bidirectional=True
    await linking_service.create_link(
        source_id=mem_parent.id,
        target_id=mem_child.id,
        link_type=LinkType.PARENT,
        bidirectional=True,
    )

    # Then: Parent -> Child link should be PARENT
    cursor = await linking_service.db.execute(
        "SELECT link_type FROM memory_links WHERE source_id = ? AND target_id = ?",
        (mem_parent.id, mem_child.id),
    )
    row_parent = await cursor.fetchone()
    assert row_parent["link_type"] == LinkType.PARENT.value

    # And: Child -> Parent link should be CHILD (reversed)
    cursor = await linking_service.db.execute(
        "SELECT link_type FROM memory_links WHERE source_id = ? AND target_id = ?",
        (mem_child.id, mem_parent.id),
    )
    row_child = await cursor.fetchone()
    assert row_child["link_type"] == LinkType.CHILD.value


# LK-004: 自己参照リンクの禁止
@pytest.mark.asyncio
async def test_self_referencing_link_rejected(
    linking_service: LinkingService,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-004: Self-referencing link is rejected."""
    # Given: A memory exists
    mem_a = sample_memories_for_linking[0]

    # When/Then: Attempting self-reference should raise ValueError
    with pytest.raises(ValueError, match="Cannot create link to self"):
        await linking_service.create_link(
            source_id=mem_a.id, target_id=mem_a.id
        )


# LK-005: 存在しないメモリへのリンク
@pytest.mark.asyncio
async def test_link_to_nonexistent_memory(
    linking_service: LinkingService,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-005: Link to non-existent memory raises error."""
    # Given: Memory A exists, but target does not
    mem_a = sample_memories_for_linking[0]

    # When/Then: Linking to non-existent target should raise RuntimeError
    with pytest.raises(RuntimeError, match="Target memory not found"):
        await linking_service.create_link(
            source_id=mem_a.id, target_id="non-existent-id"
        )

    # When/Then: Linking from non-existent source should raise RuntimeError
    with pytest.raises(RuntimeError, match="Source memory not found"):
        await linking_service.create_link(
            source_id="non-existent-id", target_id=mem_a.id
        )


# LK-006: 重複リンクの禁止
@pytest.mark.asyncio
async def test_duplicate_link_rejected(
    linking_service: LinkingService,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-006: Duplicate link is rejected."""
    # Given: Link A -> B (related) already exists
    mem_a, mem_b = sample_memories_for_linking[0], sample_memories_for_linking[1]
    await linking_service.create_link(
        source_id=mem_a.id,
        target_id=mem_b.id,
        link_type=LinkType.RELATED,
        bidirectional=False,
    )

    # When/Then: Creating same link again should raise error
    with pytest.raises(Exception):  # ConflictError or sqlite3.IntegrityError
        await linking_service.create_link(
            source_id=mem_a.id,
            target_id=mem_b.id,
            link_type=LinkType.RELATED,
            bidirectional=False,
        )


# LK-007: 異なるタイプのリンク許可
@pytest.mark.asyncio
async def test_different_link_types_allowed(
    linking_service: LinkingService,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-007: Different link types between same memories are allowed."""
    # Given: Link A -> B (related) exists
    mem_a, mem_b = sample_memories_for_linking[0], sample_memories_for_linking[1]
    await linking_service.create_link(
        source_id=mem_a.id,
        target_id=mem_b.id,
        link_type=LinkType.RELATED,
        bidirectional=False,
    )

    # When: Create link with different type (similar)
    link2 = await linking_service.create_link(
        source_id=mem_a.id,
        target_id=mem_b.id,
        link_type=LinkType.SIMILAR,
        bidirectional=False,
    )

    # Then: Second link should be created successfully
    assert link2.link_type == LinkType.SIMILAR

    # Verify both links exist
    cursor = await linking_service.db.execute(
        "SELECT COUNT(*) as count FROM memory_links WHERE source_id = ? AND target_id = ?",
        (mem_a.id, mem_b.id),
    )
    row = await cursor.fetchone()
    assert row["count"] == 2


# LK-008: リンクの削除
@pytest.mark.asyncio
async def test_link_deletion(
    linking_service: LinkingService,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-008: Link deletion."""
    # Given: Bidirectional link A <-> B exists
    mem_a, mem_b = sample_memories_for_linking[0], sample_memories_for_linking[1]
    await linking_service.create_link(
        source_id=mem_a.id,
        target_id=mem_b.id,
        link_type=LinkType.RELATED,
        bidirectional=True,
    )

    # When: Delete link
    result = await linking_service.delete_link(source_id=mem_a.id, target_id=mem_b.id)

    # Then: Both directions should be deleted
    assert result["deleted_count"] == 2

    # Verify no links remain
    cursor = await linking_service.db.execute(
        "SELECT COUNT(*) as count FROM memory_links WHERE (source_id = ? AND target_id = ?) OR (source_id = ? AND target_id = ?)",
        (mem_a.id, mem_b.id, mem_b.id, mem_a.id),
    )
    row = await cursor.fetchone()
    assert row["count"] == 0


# LK-009: 特定タイプのリンク削除
@pytest.mark.asyncio
async def test_link_deletion_by_type(
    linking_service: LinkingService,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-009: Delete links by specific type."""
    # Given: Multiple link types between A and B
    mem_a, mem_b = sample_memories_for_linking[0], sample_memories_for_linking[1]
    await linking_service.create_link(
        source_id=mem_a.id,
        target_id=mem_b.id,
        link_type=LinkType.RELATED,
        bidirectional=True,
    )
    await linking_service.create_link(
        source_id=mem_a.id,
        target_id=mem_b.id,
        link_type=LinkType.SIMILAR,
        bidirectional=True,
    )

    # When: Delete only RELATED links
    result = await linking_service.delete_link(
        source_id=mem_a.id, target_id=mem_b.id, link_type=LinkType.RELATED
    )

    # Then: Only RELATED links should be deleted (2 directions)
    assert result["deleted_count"] == 2

    # Verify SIMILAR links still exist
    cursor = await linking_service.db.execute(
        "SELECT COUNT(*) as count FROM memory_links WHERE (source_id = ? AND target_id = ?) OR (source_id = ? AND target_id = ?)",
        (mem_a.id, mem_b.id, mem_b.id, mem_a.id),
    )
    row = await cursor.fetchone()
    assert row["count"] == 2  # Both SIMILAR links remain


# LK-010: リンク一覧の取得
@pytest.mark.asyncio
async def test_get_links(
    linking_service: LinkingService,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-010: Get all links for a memory."""
    # Given: Memory A has multiple links
    mem_a, mem_b, mem_c, mem_d = sample_memories_for_linking[:4]
    # A -> B (related)
    await linking_service.create_link(
        source_id=mem_a.id, target_id=mem_b.id, link_type=LinkType.RELATED, bidirectional=False
    )
    # A -> C (parent)
    await linking_service.create_link(
        source_id=mem_a.id, target_id=mem_c.id, link_type=LinkType.PARENT, bidirectional=False
    )
    # D -> A (similar)
    await linking_service.create_link(
        source_id=mem_d.id, target_id=mem_a.id, link_type=LinkType.SIMILAR, bidirectional=False
    )

    # When: Get all links for memory A
    result = await linking_service.get_links(memory_id=mem_a.id)

    # Then: All 3 links should be returned (default direction="both")
    assert result["total"] == 3
    assert len(result["links"]) == 3
    assert result["memory_id"] == mem_a.id


# LK-011: 方向によるフィルタリング
@pytest.mark.asyncio
async def test_get_links_by_direction(
    linking_service: LinkingService,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-011: Filter links by direction."""
    # Given: Memory A has both outgoing and incoming links
    mem_a, mem_b, mem_c = sample_memories_for_linking[:3]
    # A -> B (outgoing)
    await linking_service.create_link(
        source_id=mem_a.id, target_id=mem_b.id, bidirectional=False
    )
    # C -> A (incoming)
    await linking_service.create_link(
        source_id=mem_c.id, target_id=mem_a.id, bidirectional=False
    )

    # When: Get outgoing links only
    result_outgoing = await linking_service.get_links(
        memory_id=mem_a.id, direction="outgoing"
    )

    # Then: Only A -> B should be returned
    assert result_outgoing["total"] == 1
    assert result_outgoing["links"][0]["target_id"] == mem_b.id

    # When: Get incoming links only
    result_incoming = await linking_service.get_links(
        memory_id=mem_a.id, direction="incoming"
    )

    # Then: Only C -> A should be returned
    assert result_incoming["total"] == 1
    assert result_incoming["links"][0]["source_id"] == mem_c.id


# LK-012: CASCADE DELETE の確認
@pytest.mark.asyncio
async def test_cascade_delete_on_memory_deletion(
    linking_service: LinkingService,
    memory_repository: MemoryRepository,
    sample_memories_for_linking: list[Memory],
) -> None:
    """Test LK-012: CASCADE DELETE when memory is deleted."""
    # Given: Memory A has links to B and C
    mem_a, mem_b, mem_c = sample_memories_for_linking[:3]
    await linking_service.create_link(
        source_id=mem_a.id, target_id=mem_b.id, bidirectional=False
    )
    await linking_service.create_link(
        source_id=mem_a.id, target_id=mem_c.id, bidirectional=False
    )

    # Verify links exist
    cursor = await linking_service.db.execute(
        "SELECT COUNT(*) as count FROM memory_links WHERE source_id = ?",
        (mem_a.id,),
    )
    row = await cursor.fetchone()
    assert row["count"] == 2

    # When: Delete memory A
    await memory_repository.delete(mem_a.id)

    # Then: All links involving A should be automatically deleted (CASCADE)
    cursor = await linking_service.db.execute(
        "SELECT COUNT(*) as count FROM memory_links WHERE source_id = ? OR target_id = ?",
        (mem_a.id, mem_a.id),
    )
    row = await cursor.fetchone()
    assert row["count"] == 0

    # And: Memories B and C should still exist
    assert await memory_repository.find_by_id(mem_b.id) is not None
    assert await memory_repository.find_by_id(mem_c.id) is not None
