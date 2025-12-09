"""Service for dependency tracking and propagation."""

import json
from datetime import datetime, timezone
from typing import Any

from src.db.database import Database
from src.db.repositories.memory_repository import MemoryRepository
from src.exceptions import NotFoundError, ValidationError
from src.models.dependency import (
    AffectedMemory,
    DependencyAnalysis,
    DependencyNotification,
    NotificationType,
)
from src.models.linking import LinkType


class DependencyService:
    """Service for dependency tracking and impact analysis."""

    DEFAULT_MAX_DEPTH = 5

    def __init__(
        self,
        memory_repository: MemoryRepository,
        db: Database,
    ) -> None:
        """Initialize dependency service.

        Args:
            memory_repository: Memory repository
            db: Database instance
        """
        self.memory_repository = memory_repository
        self.db = db

    async def analyze_impact(
        self,
        memory_id: str,
        cascade_type: str = "update",
        max_depth: int = 5,
    ) -> DependencyAnalysis:
        """Analyze dependency impact for a memory.

        Args:
            memory_id: Source memory ID
            cascade_type: Type of cascade ("update" | "delete")
            max_depth: Maximum traversal depth (1-10)

        Returns:
            DependencyAnalysis result

        Raises:
            NotFoundError: If memory not found
            ValidationError: If cascade_type or max_depth invalid
        """
        if cascade_type not in ("update", "delete"):
            raise ValidationError(
                f"Invalid cascade_type: {cascade_type}. Must be 'update' or 'delete'."
            )

        if not 1 <= max_depth <= 10:
            raise ValidationError("max_depth must be between 1 and 10")

        # Check memory exists
        memory = await self.memory_repository.find_by_id(memory_id)
        if not memory:
            raise NotFoundError(f"Memory not found: {memory_id}")

        # Initialize traversal state
        visited: set[str] = set()
        affected: list[AffectedMemory] = []
        cycles: list[list[str]] = []

        # Start traversal
        await self._traverse_dependencies(
            current_id=memory_id,
            depth=0,
            max_depth=max_depth,
            cascade_type=cascade_type,
            visited=visited,
            path=[],
            affected=affected,
            cycles=cycles,
        )

        # Exclude source memory from affected list (only include dependencies)
        affected = [a for a in affected if a.memory_id != memory_id]

        # Sort cycles by length (longest first) to prioritize complete cycles
        cycles.sort(key=len, reverse=True)

        return DependencyAnalysis(
            source_memory_id=memory_id,
            affected_memories=affected,
            total_affected=len(affected),
            max_depth_reached=max(
                (a.depth for a in affected), default=0
            ),
            has_cycles=len(cycles) > 0,
            cycle_paths=cycles,
        )

    async def _traverse_dependencies(
        self,
        current_id: str,
        depth: int,
        max_depth: int,
        cascade_type: str,
        visited: set[str],
        path: list[str],
        affected: list[AffectedMemory],
        cycles: list[list[str]],
    ) -> None:
        """Recursively traverse dependency graph.

        Args:
            current_id: Current memory ID
            depth: Current depth
            max_depth: Maximum depth
            cascade_type: Type of cascade
            visited: Set of visited memory IDs
            path: Current path for cycle detection
            affected: List to accumulate affected memories
            cycles: List to accumulate detected cycles
        """
        # Depth limit check first
        if depth >= max_depth:
            return

        # Cycle detection: check if current_id is already in the path
        # This must happen FIRST to detect cycles before the visited check
        if current_id in path:
            cycle_start = path.index(current_id)
            cycle = path[cycle_start:] + [current_id]
            cycles.append(cycle)
            return

        # Skip if already visited (avoid duplicate processing)
        # We skip this check for nodes in the current path (handled above)
        # to ensure we can detect cycles
        if current_id in visited:
            return

        visited.add(current_id)

        # Build current path for recursion
        current_path = path + [current_id]

        # Get outgoing links with cascade enabled
        # Use explicit if-else instead of f-string for better security
        if cascade_type == "update":
            query = """
                SELECT target_id, link_type, strength
                FROM memory_links
                WHERE source_id = ? AND cascade_on_update = 1
            """
        else:  # cascade_type == "delete"
            query = """
                SELECT target_id, link_type, strength
                FROM memory_links
                WHERE source_id = ? AND cascade_on_delete = 1
            """

        cursor = await self.db.execute(query, (current_id,))
        links = await cursor.fetchall()

        # Traverse each dependent link
        for link in links:
            target_id = link[0]
            link_type_str = link[1]
            strength = link[2]

            # Convert link_type string to enum
            try:
                link_type = LinkType(link_type_str)
            except ValueError:
                link_type = LinkType.RELATED

            # Add to affected list (even if already visited, to track all dependencies)
            if target_id not in visited:
                affected.append(
                    AffectedMemory(
                        memory_id=target_id,
                        depth=depth + 1,
                        link_type=link_type,
                        cascade_type=cascade_type,
                        strength=strength,
                    )
                )

            # Recurse with updated path
            await self._traverse_dependencies(
                current_id=target_id,
                depth=depth + 1,
                max_depth=max_depth,
                cascade_type=cascade_type,
                visited=visited,
                path=current_path,
                affected=affected,
                cycles=cycles,
            )

    async def propagate_update(
        self,
        memory_id: str,
        notification_type: str | NotificationType = "update",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Propagate change notifications to dependent memories.

        Args:
            memory_id: Source memory ID
            notification_type: Type of notification ("update" | "delete" | "stale") or NotificationType enum
            metadata: Additional context

        Returns:
            Dict with affected_count, notifications_created, and affected_memory_ids

        Raises:
            NotFoundError: If memory not found
            ValidationError: If notification_type invalid
        """
        # Convert NotificationType enum to string if needed
        if isinstance(notification_type, NotificationType):
            notification_type = notification_type.value

        if notification_type not in ("update", "delete", "stale"):
            raise ValidationError(
                f"Invalid notification_type: {notification_type}. "
                "Must be 'update', 'delete', or 'stale'."
            )

        # Check memory exists
        memory = await self.memory_repository.find_by_id(memory_id)
        if not memory:
            raise NotFoundError(f"Memory not found: {memory_id}")

        # Analyze impact (read-only, no transaction needed)
        cascade_type = "delete" if notification_type == "delete" else "update"
        analysis = await self.analyze_impact(
            memory_id, cascade_type=cascade_type
        )

        # Create notifications
        notifications_created = 0
        affected_memory_ids = []

        if analysis.affected_memories:
            for affected in analysis.affected_memories:
                notification = DependencyNotification(
                    source_memory_id=memory_id,
                    target_memory_id=affected.memory_id,
                    notification_type=NotificationType(notification_type),
                    metadata=metadata or {},
                )

                await self.db.execute(
                    """
                    INSERT INTO dependency_notifications (
                        id, source_memory_id, target_memory_id,
                        notification_type, metadata, created_at, processed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        notification.id,
                        notification.source_memory_id,
                        notification.target_memory_id,
                        notification.notification_type.value,
                        json.dumps(notification.metadata),
                        notification.created_at.isoformat(),
                        None,
                    ),
                )
                notifications_created += 1
                affected_memory_ids.append(affected.memory_id)

            # Commit all inserts at once
            await self.db.commit()

        return {
            "affected_count": analysis.total_affected,
            "notifications_created": notifications_created,
            "affected_memory_ids": affected_memory_ids,
        }

    async def get_pending_notifications(
        self, target_memory_id: str
    ) -> list[DependencyNotification]:
        """Get pending notifications for a target memory.

        Args:
            target_memory_id: Target memory ID

        Returns:
            List of pending notifications
        """
        cursor = await self.db.execute(
            """
            SELECT id, source_memory_id, target_memory_id,
                   notification_type, metadata, created_at, processed_at
            FROM dependency_notifications
            WHERE target_memory_id = ? AND processed_at IS NULL
            ORDER BY created_at ASC
            """,
            (target_memory_id,),
        )
        rows = await cursor.fetchall()

        notifications = []
        for row in rows:
            row_dict = dict(row)
            notification = DependencyNotification(
                id=row_dict["id"],
                source_memory_id=row_dict["source_memory_id"],
                target_memory_id=row_dict["target_memory_id"],
                notification_type=NotificationType(row_dict["notification_type"]),
                metadata=json.loads(row_dict["metadata"]),  # Database schema guarantees non-null default '{}'
                created_at=datetime.fromisoformat(row_dict["created_at"]),
                processed_at=None,
            )
            notifications.append(notification)

        return notifications

    async def mark_notification_processed(
        self, notification_id: str
    ) -> None:
        """Mark a notification as processed.

        Args:
            notification_id: Notification ID
        """
        await self.db.execute(
            """
            UPDATE dependency_notifications
            SET processed_at = ?
            WHERE id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), notification_id),
        )
        await self.db.commit()
