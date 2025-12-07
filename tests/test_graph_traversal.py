"""Tests for graph traversal service."""

import pytest

from src.models.linking import LinkType
from src.services.graph_traversal_service import GraphTraversalService


@pytest.mark.asyncio
class TestBasicTraversal:
    """Test basic graph traversal functionality."""

    async def test_bfs_traversal(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test BFS traversal finds related memories at different depths."""
        # Create a graph: A -> B -> C
        a = await memory_service.store(content="Node A", tags=["graph"])
        b = await memory_service.store(content="Node B", tags=["graph"])
        c = await memory_service.store(content="Node C", tags=["graph"])

        await linking_service.create_link(a.id, b.id, link_type=LinkType.RELATED)
        await linking_service.create_link(b.id, c.id, link_type=LinkType.RELATED)

        # Execute traversal
        results = await graph_traversal_service.traverse(
            start_memory_id=a.id,
            max_depth=2,
        )

        # Verify results
        memory_ids = [r[0].id for r in results]
        assert b.id in memory_ids  # depth 1
        assert c.id in memory_ids  # depth 2

    async def test_traverse_returns_sorted_by_depth(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test results are sorted by depth (closer first)."""
        # Create graph: A -> [B, C], B -> D
        a = await memory_service.store(content="Root", tags=["test"])
        b = await memory_service.store(content="Level 1 - B", tags=["test"])
        c = await memory_service.store(content="Level 1 - C", tags=["test"])
        d = await memory_service.store(content="Level 2 - D", tags=["test"])

        await linking_service.create_link(a.id, b.id)
        await linking_service.create_link(a.id, c.id)
        await linking_service.create_link(b.id, d.id)

        results = await graph_traversal_service.traverse(
            start_memory_id=a.id,
            max_depth=3,
        )

        # Check depth ordering
        depths = [r[1].depth for r in results]
        assert depths == sorted(depths)  # Should be sorted

    async def test_traverse_nonexistent_memory_raises_error(
        self,
        graph_traversal_service: GraphTraversalService,
    ):
        """Test traversing from non-existent memory raises ValueError."""
        with pytest.raises(ValueError, match="Start memory not found"):
            await graph_traversal_service.traverse(
                start_memory_id="nonexistent-id",
                max_depth=2,
            )


@pytest.mark.asyncio
class TestCycleDetection:
    """Test cycle detection in graph traversal."""

    async def test_cycle_detection(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test cycle detection prevents infinite loops."""
        # Create cycle: A -> B -> C -> A
        a = await memory_service.store(content="Cycle A", tags=["cycle"])
        b = await memory_service.store(content="Cycle B", tags=["cycle"])
        c = await memory_service.store(content="Cycle C", tags=["cycle"])

        await linking_service.create_link(a.id, b.id)
        await linking_service.create_link(b.id, c.id)
        await linking_service.create_link(c.id, a.id)

        # Execute with high max_depth to test cycle handling
        results = await graph_traversal_service.traverse(
            start_memory_id=a.id,
            max_depth=10,
        )

        # Verify no duplicates (each node visited only once)
        memory_ids = [r[0].id for r in results]
        assert len(memory_ids) == len(set(memory_ids))

    async def test_self_loop_detection(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test self-loop detection."""
        # Create self-loop: A -> A
        # Note: linking_service may prevent self-loops
        a = await memory_service.store(content="Self loop", tags=["loop"])

        # Try to create self-loop (might raise ValueError)
        try:
            await linking_service.create_link(a.id, a.id)
        except ValueError:
            # Self-loops are prevented at linking layer
            pytest.skip("Self-loops are prevented by linking service")
            return

        results = await graph_traversal_service.traverse(
            start_memory_id=a.id,
            max_depth=3,
        )

        # Should not include self-loop (A is already visited)
        memory_ids = [r[0].id for r in results]
        assert a.id not in memory_ids


@pytest.mark.asyncio
class TestDepthControl:
    """Test max_depth parameter."""

    async def test_max_depth_limit(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test max_depth limits traversal depth."""
        # Create chain: A -> B -> C -> D
        a = await memory_service.store(content="A", tags=["chain"])
        b = await memory_service.store(content="B", tags=["chain"])
        c = await memory_service.store(content="C", tags=["chain"])
        d = await memory_service.store(content="D", tags=["chain"])

        await linking_service.create_link(a.id, b.id)
        await linking_service.create_link(b.id, c.id)
        await linking_service.create_link(c.id, d.id)

        # Traverse with max_depth=2
        results = await graph_traversal_service.traverse(
            start_memory_id=a.id,
            max_depth=2,
        )

        memory_ids = [r[0].id for r in results]
        assert b.id in memory_ids  # depth 1
        assert c.id in memory_ids  # depth 2
        assert d.id not in memory_ids  # depth 3, exceeds max_depth

    async def test_depth_zero_returns_empty(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test max_depth=0 returns empty results."""
        a = await memory_service.store(content="Root", tags=["test"])
        b = await memory_service.store(content="Child", tags=["test"])
        await linking_service.create_link(a.id, b.id)

        results = await graph_traversal_service.traverse(
            start_memory_id=a.id,
            max_depth=0,
        )

        assert len(results) == 0


@pytest.mark.asyncio
class TestMaxResultsLimit:
    """Test max_results parameter."""

    async def test_max_results_limit(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test max_results limits number of returned memories."""
        # Create many linked memories
        root = await memory_service.store(content="Root", tags=["root"])
        for i in range(20):
            child = await memory_service.store(content=f"Child {i}", tags=["child"])
            await linking_service.create_link(root.id, child.id)

        # Limit results to 5
        results = await graph_traversal_service.traverse(
            start_memory_id=root.id,
            max_results=5,
        )

        assert len(results) <= 5

    async def test_max_results_zero_returns_empty(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test max_results=0 returns empty results."""
        a = await memory_service.store(content="Root", tags=["test"])
        b = await memory_service.store(content="Child", tags=["test"])
        await linking_service.create_link(a.id, b.id)

        results = await graph_traversal_service.traverse(
            start_memory_id=a.id,
            max_results=0,
        )

        assert len(results) == 0


@pytest.mark.asyncio
class TestLinkTypeFiltering:
    """Test link type filtering."""

    async def test_link_type_filter(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test filtering by specific link types."""
        root = await memory_service.store(content="Root", tags=["root"])
        parent = await memory_service.store(content="Parent", tags=["parent"])
        sibling = await memory_service.store(content="Sibling", tags=["sibling"])

        await linking_service.create_link(root.id, parent.id, link_type=LinkType.PARENT)
        await linking_service.create_link(root.id, sibling.id, link_type=LinkType.RELATED)

        # Only follow PARENT links
        results = await graph_traversal_service.traverse(
            start_memory_id=root.id,
            link_types=["parent"],
        )

        memory_ids = [r[0].id for r in results]
        assert parent.id in memory_ids
        assert sibling.id not in memory_ids

    async def test_multiple_link_types_filter(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test filtering with multiple link types."""
        root = await memory_service.store(content="Root", tags=["root"])
        parent = await memory_service.store(content="Parent", tags=["parent"])
        child = await memory_service.store(content="Child", tags=["child"])
        similar = await memory_service.store(content="Similar", tags=["similar"])

        await linking_service.create_link(root.id, parent.id, link_type=LinkType.PARENT)
        await linking_service.create_link(root.id, child.id, link_type=LinkType.CHILD)
        await linking_service.create_link(root.id, similar.id, link_type=LinkType.SIMILAR)

        # Follow PARENT and CHILD links only
        results = await graph_traversal_service.traverse(
            start_memory_id=root.id,
            link_types=["parent", "child"],
        )

        memory_ids = [r[0].id for r in results]
        assert parent.id in memory_ids
        assert child.id in memory_ids
        assert similar.id not in memory_ids

    async def test_no_link_type_filter_follows_all(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test no filter follows all link types."""
        root = await memory_service.store(content="Root", tags=["root"])
        parent = await memory_service.store(content="Parent", tags=["parent"])
        similar = await memory_service.store(content="Similar", tags=["similar"])

        await linking_service.create_link(root.id, parent.id, link_type=LinkType.PARENT)
        await linking_service.create_link(root.id, similar.id, link_type=LinkType.SIMILAR)

        results = await graph_traversal_service.traverse(
            start_memory_id=root.id,
            link_types=None,  # No filter
        )

        memory_ids = [r[0].id for r in results]
        assert parent.id in memory_ids
        assert similar.id in memory_ids


@pytest.mark.asyncio
class TestBidirectionalTraversal:
    """Test bidirectional link traversal."""

    async def test_bidirectional_traversal(
        self,
        graph_traversal_service: GraphTraversalService,
        memory_service,
        linking_service,
    ):
        """Test traversal follows links in both directions."""
        # Create: A <- B -> C
        a = await memory_service.store(content="A", tags=["test"])
        b = await memory_service.store(content="B", tags=["test"])
        c = await memory_service.store(content="C", tags=["test"])

        await linking_service.create_link(b.id, a.id)  # B -> A
        await linking_service.create_link(b.id, c.id)  # B -> C

        # Start from B, should find both A and C
        results = await graph_traversal_service.traverse(
            start_memory_id=b.id,
            max_depth=1,
        )

        memory_ids = [r[0].id for r in results]
        assert a.id in memory_ids
        assert c.id in memory_ids
