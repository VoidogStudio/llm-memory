"""Service for managing memory links."""

import json

from src.db.database import Database
from src.db.repositories.memory_repository import MemoryRepository
from src.exceptions import ValidationError
from src.models.linking import LinkType, MemoryLink


class LinkingService:
    """Service for managing memory links."""

    # Link type reverse mapping
    REVERSE_TYPES: dict[LinkType, LinkType] = {
        LinkType.PARENT: LinkType.CHILD,
        LinkType.CHILD: LinkType.PARENT,
        LinkType.RELATED: LinkType.RELATED,
        LinkType.SIMILAR: LinkType.SIMILAR,
        LinkType.REFERENCE: LinkType.REFERENCE,
        LinkType.DEPENDS_ON: LinkType.DERIVED_FROM,  # v1.7.0
        LinkType.DERIVED_FROM: LinkType.DEPENDS_ON,  # v1.7.0
    }

    def __init__(self, repository: MemoryRepository, db: Database) -> None:
        """Initialize linking service.

        Args:
            repository: Memory repository
            db: Database instance
        """
        self.repository = repository
        self.db = db

    async def create_link(
        self,
        source_id: str,
        target_id: str,
        link_type: LinkType = LinkType.RELATED,
        bidirectional: bool = True,
        metadata: dict | None = None,
        use_transaction: bool = True,
        cascade_on_update: bool = False,  # v1.7.0
        cascade_on_delete: bool = False,  # v1.7.0
        strength: float = 1.0,  # v1.7.0
    ) -> MemoryLink:
        """Create a link between two memories.

        Args:
            source_id: Source memory ID
            target_id: Target memory ID
            link_type: Type of link
            bidirectional: If True, create reverse link
            metadata: Optional metadata
            use_transaction: If True, wrap operations in explicit transaction
            cascade_on_update: Propagate update notifications (v1.7.0)
            cascade_on_delete: Propagate delete notifications (v1.7.0)
            strength: Link strength 0.0-1.0 (v1.7.0)

        Returns:
            Created MemoryLink

        Raises:
            ValueError: If source_id == target_id or invalid strength
            RuntimeError: If source or target memory not found
        """
        # Validate not self-referencing
        if source_id == target_id:
            raise ValueError("Cannot create link to self")

        # Validate strength (v1.7.0)
        if not 0.0 <= strength <= 1.0:
            raise ValidationError(f"strength must be between 0.0 and 1.0, got {strength}")

        # Verify both memories exist
        source = await self.repository.find_by_id(source_id)
        if not source:
            raise RuntimeError(f"Source memory not found: {source_id}")

        target = await self.repository.find_by_id(target_id)
        if not target:
            raise RuntimeError(f"Target memory not found: {target_id}")

        # Create link
        link = MemoryLink(
            source_id=source_id,
            target_id=target_id,
            link_type=link_type,
            metadata=metadata or {},
            cascade_on_update=cascade_on_update,  # v1.7.0
            cascade_on_delete=cascade_on_delete,  # v1.7.0
            strength=strength,  # v1.7.0
        )

        async def _do_insert() -> None:
            """Insert link(s) into database."""
            # Insert primary link
            await self.db.execute(
                """
                INSERT INTO memory_links (
                    id, source_id, target_id, link_type, metadata, created_at,
                    cascade_on_update, cascade_on_delete, strength
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    link.id,
                    link.source_id,
                    link.target_id,
                    link.link_type.value,
                    json.dumps(link.metadata),
                    link.created_at.isoformat(),
                    1 if link.cascade_on_update else 0,  # v1.7.0
                    1 if link.cascade_on_delete else 0,  # v1.7.0
                    link.strength,  # v1.7.0
                ),
            )

            # Insert reverse link if bidirectional
            if bidirectional:
                reverse_type = self.REVERSE_TYPES[link_type]
                reverse_link = MemoryLink(
                    source_id=target_id,
                    target_id=source_id,
                    link_type=reverse_type,
                    metadata=metadata or {},
                    cascade_on_update=cascade_on_update,  # v1.7.0
                    cascade_on_delete=cascade_on_delete,  # v1.7.0
                    strength=strength,  # v1.7.0
                )
                await self.db.execute(
                    """
                    INSERT INTO memory_links (
                        id, source_id, target_id, link_type, metadata, created_at,
                        cascade_on_update, cascade_on_delete, strength
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        reverse_link.id,
                        reverse_link.source_id,
                        reverse_link.target_id,
                        reverse_link.link_type.value,
                        json.dumps(reverse_link.metadata),
                        reverse_link.created_at.isoformat(),
                        1 if reverse_link.cascade_on_update else 0,  # v1.7.0
                        1 if reverse_link.cascade_on_delete else 0,  # v1.7.0
                        reverse_link.strength,  # v1.7.0
                    ),
                )

        if use_transaction:
            async with self.db.transaction():
                await _do_insert()
        else:
            await _do_insert()

        return link

    async def delete_link(
        self,
        source_id: str,
        target_id: str,
        link_type: LinkType | None = None,
        use_transaction: bool = True,
    ) -> dict:
        """Delete link(s) between two memories.

        Args:
            source_id: Source memory ID
            target_id: Target memory ID
            link_type: Specific type to delete (None = all types)
            use_transaction: If True, wrap operations in explicit transaction

        Returns:
            Dict with deleted_count, source_id, target_id, link_type
        """
        # Build parameterized query
        if link_type:
            sql = """
                DELETE FROM memory_links
                WHERE (source_id = ? AND target_id = ? AND link_type = ?)
                   OR (source_id = ? AND target_id = ? AND link_type = ?)
            """
            params = (source_id, target_id, link_type.value, target_id, source_id, link_type.value)
        else:
            sql = """
                DELETE FROM memory_links
                WHERE (source_id = ? AND target_id = ?)
                   OR (source_id = ? AND target_id = ?)
            """
            params = (source_id, target_id, target_id, source_id)

        async def _do_delete() -> int:
            """Execute delete query."""
            cursor = await self.db.execute(sql, params)
            return cursor.rowcount or 0

        if use_transaction:
            async with self.db.transaction():
                deleted_count = await _do_delete()
        else:
            deleted_count = await _do_delete()

        return {
            "deleted_count": deleted_count,
            "source_id": source_id,
            "target_id": target_id,
            "link_type": link_type.value if link_type else None,
        }

    async def get_links(
        self,
        memory_id: str,
        link_type: LinkType | None = None,
        direction: str = "both",
    ) -> dict:
        """Get links for a memory.

        Args:
            memory_id: Memory ID
            link_type: Filter by type
            direction: Link direction filter ("outgoing" | "incoming" | "both")

        Returns:
            Dict with memory_id, links (list of dicts), and total count
        """
        # Build parameterized query based on direction and link_type
        if direction == "outgoing":
            if link_type:
                sql = "SELECT * FROM memory_links WHERE source_id = ? AND link_type = ?"
                params = (memory_id, link_type.value)
            else:
                sql = "SELECT * FROM memory_links WHERE source_id = ?"
                params = (memory_id,)
        elif direction == "incoming":
            if link_type:
                sql = "SELECT * FROM memory_links WHERE target_id = ? AND link_type = ?"
                params = (memory_id, link_type.value)
            else:
                sql = "SELECT * FROM memory_links WHERE target_id = ?"
                params = (memory_id,)
        else:  # "both"
            if link_type:
                sql = "SELECT * FROM memory_links WHERE (source_id = ? OR target_id = ?) AND link_type = ?"
                params = (memory_id, memory_id, link_type.value)
            else:
                sql = "SELECT * FROM memory_links WHERE (source_id = ? OR target_id = ?)"
                params = (memory_id, memory_id)

        cursor = await self.db.execute(sql, params)
        rows = await cursor.fetchall()

        links = []
        for row in rows:
            link_dict = {
                "id": row["id"],
                "source_id": row["source_id"],
                "target_id": row["target_id"],
                "link_type": row["link_type"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "created_at": row["created_at"],
            }
            links.append(link_dict)

        return {
            "memory_id": memory_id,
            "links": links,
            "total": len(links),
        }
