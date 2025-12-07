"""Graph traversal service for collecting related memories via BFS."""

from collections import deque
from dataclasses import dataclass

from src.db.repositories.memory_repository import MemoryRepository
from src.models.memory import Memory
from src.services.linking_service import LinkingService


@dataclass
class TraversalNode:
    """Node in graph traversal."""

    memory_id: str
    depth: int
    link_type: str | None
    path: list[str]


class GraphTraversalService:
    """Service for graph traversal of memory links using BFS."""

    def __init__(
        self,
        linking_service: LinkingService,
        repository: MemoryRepository,
    ) -> None:
        """Initialize graph traversal service.

        Args:
            linking_service: Linking service for getting memory links
            repository: Memory repository for fetching memories
        """
        self.linking_service = linking_service
        self.repository = repository

    async def traverse(
        self,
        start_memory_id: str,
        max_depth: int = 3,
        max_results: int = 50,
        link_types: list[str] | None = None,
    ) -> list[tuple[Memory, TraversalNode]]:
        """Traverse memory graph using BFS to collect related memories.

        Args:
            start_memory_id: Starting memory ID
            max_depth: Maximum traversal depth
            max_results: Maximum number of results to return
            link_types: Filter by specific link types (None = all types)

        Returns:
            List of (Memory, TraversalNode) tuples sorted by depth

        Raises:
            ValueError: If start memory does not exist
        """
        # Verify start memory exists
        start_memory = await self.repository.find_by_id(start_memory_id)
        if not start_memory:
            raise ValueError(f"Start memory not found: {start_memory_id}")

        # Initialize BFS queue and visited set
        queue: deque[TraversalNode] = deque()
        visited: set[str] = {start_memory_id}
        results: list[tuple[Memory, TraversalNode]] = []

        # Add starting node
        start_node = TraversalNode(
            memory_id=start_memory_id,
            depth=0,
            link_type=None,
            path=[start_memory_id],
        )
        queue.append(start_node)

        # BFS traversal
        while queue and len(results) < max_results:
            current = queue.popleft()

            # Skip if depth exceeds max_depth
            if current.depth >= max_depth:
                continue

            # Get linked memories
            linked = await self._get_linked_memories(current.memory_id, link_types)

            for target_id, link_type in linked:
                # Skip if already visited (cycle detection)
                if target_id in visited:
                    continue

                # Mark as visited
                visited.add(target_id)

                # Create traversal node
                node = TraversalNode(
                    memory_id=target_id,
                    depth=current.depth + 1,
                    link_type=link_type,
                    path=current.path + [target_id],
                )

                # Fetch memory
                memory = await self.repository.find_by_id(target_id)
                if memory:
                    results.append((memory, node))

                    # Add to queue for further traversal if not at max depth
                    if current.depth + 1 < max_depth:
                        queue.append(node)

                # Stop if we've reached max_results
                if len(results) >= max_results:
                    break

        # Sort by depth (closer memories first)
        results.sort(key=lambda x: x[1].depth)

        return results

    async def _get_linked_memories(
        self,
        memory_id: str,
        link_types: list[str] | None,
    ) -> list[tuple[str, str]]:
        """Get linked memory IDs for a given memory.

        Args:
            memory_id: Source memory ID
            link_types: Filter by specific link types (None = all types)

        Returns:
            List of (target_id, link_type) tuples
        """
        # Get all links (both directions)
        links_data = await self.linking_service.get_links(
            memory_id=memory_id,
            direction="both",
        )

        linked_memories: list[tuple[str, str]] = []

        for link in links_data["links"]:
            link_type = link["link_type"]

            # Apply link type filter
            if link_types and link_type not in link_types:
                continue

            # Determine target_id based on direction
            if link["source_id"] == memory_id:
                target_id = link["target_id"]
            else:
                target_id = link["source_id"]

            linked_memories.append((target_id, link_type))

        return linked_memories
