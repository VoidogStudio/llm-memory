"""Tests for Dependency Tracking (FR-003)."""

import pytest
from src.exceptions import ValidationError
from src.models.dependency import NotificationType, DependencyAnalysis
from src.services.dependency_service import DependencyService


class TestDependencyAnalysis:
    """Test dependency analysis."""

    async def test_simple_dependency_analysis(
        self, memory_service, linking_service, dependency_service
    ):
        """DEP-001: Test simple dependency analysis."""
        # Given: A -> B with cascade_on_update
        a = await memory_service.store(content="Memory A")
        b = await memory_service.store(content="Memory B")
        await linking_service.create_link(
            a.id, b.id, cascade_on_update=True, cascade_on_delete=False
        )

        # When: Analyze update impact
        analysis = await dependency_service.analyze_impact(
            memory_id=a.id, cascade_type="update"
        )

        # Then: B is affected
        assert analysis.total_affected == 1
        assert len(analysis.affected_memories) == 1
        assert analysis.affected_memories[0].memory_id == b.id
        assert analysis.affected_memories[0].depth == 1

    async def test_deep_dependency_analysis(
        self, memory_service, linking_service, dependency_service
    ):
        """DEP-002: Test deep dependency analysis."""
        # Given: A -> B -> C -> D (all cascade_on_update)
        a = await memory_service.store(content="A")
        b = await memory_service.store(content="B")
        c = await memory_service.store(content="C")
        d = await memory_service.store(content="D")

        await linking_service.create_link(a.id, b.id, cascade_on_update=True)
        await linking_service.create_link(b.id, c.id, cascade_on_update=True)
        await linking_service.create_link(c.id, d.id, cascade_on_update=True)

        # When: Analyze with max_depth=5
        analysis = await dependency_service.analyze_impact(
            memory_id=a.id, cascade_type="update", max_depth=5
        )

        # Then: All 3 downstream memories affected
        assert analysis.total_affected == 3
        assert analysis.max_depth_reached == 3

        # Verify depths
        depths = {m.memory_id: m.depth for m in analysis.affected_memories}
        assert depths[b.id] == 1
        assert depths[c.id] == 2
        assert depths[d.id] == 3

    async def test_circular_dependency_detection(
        self, memory_service, linking_service, dependency_service
    ):
        """DEP-003: Test circular dependency detection."""
        # Given: A -> B -> C -> A (cycle)
        a = await memory_service.store(content="A")
        b = await memory_service.store(content="B")
        c = await memory_service.store(content="C")

        await linking_service.create_link(a.id, b.id, cascade_on_update=True)
        await linking_service.create_link(b.id, c.id, cascade_on_update=True)
        await linking_service.create_link(c.id, a.id, cascade_on_update=True)

        # When: Analyze dependencies
        analysis = await dependency_service.analyze_impact(
            memory_id=a.id, cascade_type="update"
        )

        # Then: Cycle detected
        assert analysis.has_cycles is True
        assert len(analysis.cycle_paths) > 0
        # Cycle should include all three memories
        cycle = analysis.cycle_paths[0]
        assert a.id in cycle
        assert b.id in cycle
        assert c.id in cycle

    async def test_non_cascade_link(
        self, memory_service, linking_service, dependency_service
    ):
        """DEP-004: Test non-cascading link."""
        # Given: A -> B with cascade_on_update=False
        a = await memory_service.store(content="A")
        b = await memory_service.store(content="B")
        await linking_service.create_link(
            a.id, b.id, cascade_on_update=False, cascade_on_delete=False
        )

        # When: Analyze update impact
        analysis = await dependency_service.analyze_impact(
            memory_id=a.id, cascade_type="update"
        )

        # Then: No affected memories
        assert analysis.total_affected == 0

    async def test_max_depth_limit(
        self, memory_service, linking_service, dependency_service
    ):
        """DEP-005: Test max_depth limit."""
        # Given: A -> B -> C -> D -> E (depth 4)
        memories = []
        for i in range(5):
            mem = await memory_service.store(content=f"Memory {i}")
            memories.append(mem)

        for i in range(4):
            await linking_service.create_link(
                memories[i].id, memories[i + 1].id, cascade_on_update=True
            )

        # When: Analyze with max_depth=2
        analysis = await dependency_service.analyze_impact(
            memory_id=memories[0].id, cascade_type="update", max_depth=2
        )

        # Then: Only 2 levels analyzed
        assert analysis.total_affected == 2  # B and C only
        assert analysis.max_depth_reached == 2

    async def test_branching_dependencies(
        self, memory_service, linking_service, dependency_service
    ):
        """DEP-006: Test branching dependencies."""
        # Given: A -> B, A -> C (A branches to 2)
        a = await memory_service.store(content="A")
        b = await memory_service.store(content="B")
        c = await memory_service.store(content="C")

        await linking_service.create_link(a.id, b.id, cascade_on_update=True)
        await linking_service.create_link(a.id, c.id, cascade_on_update=True)

        # When: Analyze dependencies
        analysis = await dependency_service.analyze_impact(
            memory_id=a.id, cascade_type="update"
        )

        # Then: Both B and C affected
        assert analysis.total_affected == 2
        affected_ids = {m.memory_id for m in analysis.affected_memories}
        assert affected_ids == {b.id, c.id}


class TestDependencyPropagation:
    """Test dependency propagation."""

    async def test_update_notification_propagation(
        self, memory_service, linking_service, dependency_service
    ):
        """DEP-007: Test update notification propagation."""
        # Given: A -> B -> C (cascade_on_update=True)
        a = await memory_service.store(content="A")
        b = await memory_service.store(content="B")
        c = await memory_service.store(content="C")

        await linking_service.create_link(a.id, b.id, cascade_on_update=True)
        await linking_service.create_link(b.id, c.id, cascade_on_update=True)

        # When: Propagate update notification
        result = await dependency_service.propagate_update(
            memory_id=a.id, notification_type=NotificationType.UPDATE
        )

        # Then: Notifications created for B and C
        assert result["notifications_created"] == 2
        affected_ids = set(result["affected_memory_ids"])
        assert affected_ids == {b.id, c.id}

    async def test_delete_notification_propagation(
        self, memory_service, linking_service, dependency_service
    ):
        """DEP-008: Test delete notification propagation."""
        # Given: A -> B with cascade_on_delete=True
        a = await memory_service.store(content="A")
        b = await memory_service.store(content="B")
        await linking_service.create_link(
            a.id, b.id, cascade_on_update=False, cascade_on_delete=True
        )

        # When: Propagate delete notification
        result = await dependency_service.propagate_update(
            memory_id=a.id, notification_type=NotificationType.DELETE
        )

        # Then: Delete notification created for B
        assert result["notifications_created"] == 1
        assert b.id in result["affected_memory_ids"]

    async def test_metadata_in_notification(
        self, memory_service, linking_service, dependency_service
    ):
        """DEP-009: Test metadata in notification."""
        # Given: A -> B (cascade_on_update=True)
        a = await memory_service.store(content="A")
        b = await memory_service.store(content="B")
        await linking_service.create_link(a.id, b.id, cascade_on_update=True)

        # When: Propagate with metadata
        result = await dependency_service.propagate_update(
            memory_id=a.id,
            notification_type=NotificationType.UPDATE,
            metadata={"reason": "content updated"},
        )

        # Then: Notification created with metadata
        assert result["notifications_created"] == 1

        # Verify metadata in pending notifications
        pending = await dependency_service.get_pending_notifications(target_memory_id=b.id)
        assert len(pending) > 0
        assert pending[0].metadata.get("reason") == "content updated"

    async def test_no_affected_propagation(self, memory_service, dependency_service):
        """DEP-010: Test propagation with no affected memories."""
        # Given: Isolated memory A
        a = await memory_service.store(content="A")

        # When: Propagate update
        result = await dependency_service.propagate_update(
            memory_id=a.id, notification_type=NotificationType.UPDATE
        )

        # Then: No notifications created
        assert result["affected_count"] == 0
        assert result["notifications_created"] == 0


class TestLinkExtensions:
    """Test extended link functionality."""

    async def test_cascade_parameters(self, memory_service, linking_service):
        """DEP-011: Test cascade parameters in link creation."""
        # Given: Two memories
        a = await memory_service.store(content="A")
        b = await memory_service.store(content="B")

        # When: Create link with cascade parameters
        link = await linking_service.create_link(
            source_id=a.id,
            target_id=b.id,
            cascade_on_update=True,
            cascade_on_delete=True,
            strength=0.8,
        )

        # Then: Link created with parameters
        assert link.cascade_on_update is True
        assert link.cascade_on_delete is True
        assert link.strength == 0.8

    async def test_strength_out_of_range(self, memory_service, linking_service):
        """DEP-012: Test strength parameter validation."""
        # Given: Two memories
        a = await memory_service.store(content="A")
        b = await memory_service.store(content="B")

        # When/Then: strength > 1.0 raises ValidationError
        with pytest.raises(ValidationError):
            await linking_service.create_link(
                source_id=a.id, target_id=b.id, strength=1.5
            )

    async def test_new_link_type(self, memory_service, linking_service):
        """DEP-013: Test new link type."""
        # Given: Two memories
        a = await memory_service.store(content="A")
        b = await memory_service.store(content="B")

        # When: Create depends_on link
        link = await linking_service.create_link(
            source_id=a.id, target_id=b.id, link_type="depends_on"
        )

        # Then: Link created with correct type
        assert link.link_type.value == "depends_on"


# Fixtures

@pytest.fixture
async def dependency_service(memory_db, memory_repository):
    """DependencyService instance for testing."""
    return DependencyService(
        memory_repository=memory_repository, db=memory_db
    )
