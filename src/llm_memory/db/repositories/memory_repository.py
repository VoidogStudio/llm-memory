"""Memory repository for database operations."""

import json
from datetime import datetime, timezone
from typing import Any

from llm_memory.db.database import Database
from llm_memory.models.memory import Memory, MemoryTier, SearchResult


class MemoryRepository:
    """Repository for memory operations."""

    def __init__(self, db: Database) -> None:
        """Initialize repository.

        Args:
            db: Database instance
        """
        self.db = db

    async def create(self, memory: Memory, embedding: list[float]) -> Memory:
        """Create a new memory entry with embedding.

        Args:
            memory: Memory object to create
            embedding: Embedding vector

        Returns:
            Created memory object
        """
        async with self.db.transaction():
            # Insert memory
            await self.db.execute(
                """
                INSERT INTO memories (
                    id, content, content_type, memory_tier, tags, metadata,
                    agent_id, created_at, updated_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.id,
                    memory.content,
                    memory.content_type.value,
                    memory.memory_tier.value,
                    json.dumps(memory.tags),
                    json.dumps(memory.metadata),
                    memory.agent_id,
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat(),
                    memory.expires_at.isoformat() if memory.expires_at else None,
                ),
            )

            # Insert embedding
            embedding_str = json.dumps(embedding)
            await self.db.execute(
                "INSERT INTO embeddings (memory_id, embedding) VALUES (?, ?)",
                (memory.id, embedding_str),
            )

        return memory

    async def find_by_id(self, memory_id: str) -> Memory | None:
        """Find memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Memory object or None if not found
        """
        cursor = await self.db.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_memory(row)

    async def update(self, memory_id: str, updates: dict[str, Any]) -> Memory | None:
        """Update memory entry.

        Args:
            memory_id: Memory ID
            updates: Fields to update

        Returns:
            Updated memory or None if not found
        """
        # Whitelist of allowed columns to prevent SQL injection
        allowed_columns = {"content", "tags", "metadata", "memory_tier", "expires_at"}

        # Build update query
        set_clauses = []
        params = []

        if "content" in updates:
            if "content" not in allowed_columns:
                raise ValueError("Invalid column: content")
            set_clauses.append("content = ?")
            params.append(updates["content"])

        if "tags" in updates:
            if "tags" not in allowed_columns:
                raise ValueError("Invalid column: tags")
            set_clauses.append("tags = ?")
            params.append(json.dumps(updates["tags"]))

        if "metadata" in updates:
            if "metadata" not in allowed_columns:
                raise ValueError("Invalid column: metadata")
            set_clauses.append("metadata = ?")
            params.append(json.dumps(updates["metadata"]))

        if "memory_tier" in updates:
            if "memory_tier" not in allowed_columns:
                raise ValueError("Invalid column: memory_tier")
            set_clauses.append("memory_tier = ?")
            params.append(updates["memory_tier"].value)

        if "expires_at" in updates:
            if "expires_at" not in allowed_columns:
                raise ValueError("Invalid column: expires_at")
            set_clauses.append("expires_at = ?")
            params.append(updates["expires_at"])

        if not set_clauses:
            return await self.find_by_id(memory_id)

        set_clauses.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(memory_id)

        async with self.db.transaction():
            await self.db.execute(
                f"UPDATE memories SET {', '.join(set_clauses)} WHERE id = ?", tuple(params)
            )

            # If content updated, update embedding (handled by service layer)

        return await self.find_by_id(memory_id)

    async def update_embedding(self, memory_id: str, embedding: list[float]) -> None:
        """Update embedding for a memory.

        Args:
            memory_id: Memory ID
            embedding: New embedding vector
        """
        embedding_str = json.dumps(embedding)
        await self.db.execute(
            "UPDATE embeddings SET embedding = ? WHERE memory_id = ?",
            (embedding_str, memory_id),
        )
        await self.db.commit()

    async def delete(self, memory_id: str) -> bool:
        """Delete memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            True if deleted, False if not found
        """
        async with self.db.transaction():
            # Delete embedding first
            await self.db.execute("DELETE FROM embeddings WHERE memory_id = ?", (memory_id,))

            # Delete memory
            cursor = await self.db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

        return cursor.rowcount > 0

    async def delete_many(
        self,
        ids: list[str] | None = None,
        memory_tier: MemoryTier | None = None,
        older_than: datetime | None = None,
    ) -> list[str]:
        """Delete multiple memories by criteria.

        Args:
            ids: List of memory IDs
            memory_tier: Memory tier filter
            older_than: Delete memories older than this

        Returns:
            List of deleted memory IDs
        """
        # Build WHERE clause
        where_clauses = []
        params: list[Any] = []

        if ids:
            placeholders = ",".join("?" * len(ids))
            where_clauses.append(f"id IN ({placeholders})")
            params.extend(ids)

        if memory_tier:
            where_clauses.append("memory_tier = ?")
            params.append(memory_tier.value)

        if older_than:
            where_clauses.append("created_at < ?")
            params.append(older_than.isoformat())

        if not where_clauses:
            return []

        where_clause = " AND ".join(where_clauses)

        # Get IDs to delete
        cursor = await self.db.execute(
            f"SELECT id FROM memories WHERE {where_clause}", tuple(params)
        )
        rows = await cursor.fetchall()
        deleted_ids = [row[0] for row in rows]

        if not deleted_ids:
            return []

        # Delete embeddings and memories
        # Validate that deleted_ids is a list of strings to prevent injection
        if not all(isinstance(id, str) for id in deleted_ids):
            raise ValueError("All IDs must be strings")

        async with self.db.transaction():
            placeholders = ",".join("?" * len(deleted_ids))
            await self.db.execute(
                f"DELETE FROM embeddings WHERE memory_id IN ({placeholders})",
                tuple(deleted_ids),
            )
            await self.db.execute(
                f"DELETE FROM memories WHERE id IN ({placeholders})", tuple(deleted_ids)
            )

        return deleted_ids

    async def find_by_filters(
        self,
        memory_tier: MemoryTier | None = None,
        tags: list[str] | None = None,
        content_type: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Memory], int]:
        """Find memories by filters with pagination.

        Args:
            memory_tier: Memory tier filter
            tags: Tags filter (AND condition)
            content_type: Content type filter
            created_after: Created after datetime
            created_before: Created before datetime
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (memories list, total count)
        """
        # Build WHERE clause
        where_clauses = []
        params: list[Any] = []

        if memory_tier:
            where_clauses.append("memory_tier = ?")
            params.append(memory_tier.value)

        if content_type:
            where_clauses.append("content_type = ?")
            params.append(content_type)

        if created_after:
            where_clauses.append("created_at >= ?")
            params.append(created_after.isoformat())

        if created_before:
            where_clauses.append("created_at <= ?")
            params.append(created_before.isoformat())

        if tags:
            # Check if all tags are present
            for tag in tags:
                where_clauses.append(
                    "EXISTS (SELECT 1 FROM json_each(tags) WHERE value = ?)"
                )
                params.append(tag)

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_cursor = await self.db.execute(
            f"SELECT COUNT(*) FROM memories WHERE {where_clause}", tuple(params)
        )
        count_row = await count_cursor.fetchone()
        total = count_row[0] if count_row else 0

        # Get memories
        cursor = await self.db.execute(
            f"""
            SELECT * FROM memories
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        )
        rows = await cursor.fetchall()

        memories = [self._row_to_memory(row) for row in rows]

        return memories, total

    async def vector_search(
        self,
        embedding: list[float],
        top_k: int,
        memory_tier: MemoryTier | None = None,
        tags: list[str] | None = None,
        content_type: str | None = None,
    ) -> list[SearchResult]:
        """Perform vector similarity search.

        Args:
            embedding: Query embedding vector
            top_k: Number of results to return
            memory_tier: Memory tier filter
            tags: Tags filter
            content_type: Content type filter

        Returns:
            List of search results with similarity scores
        """
        # Build WHERE clause for filters
        where_clauses = ["e.memory_id = m.id"]
        params: list[Any] = [json.dumps(embedding)]

        if memory_tier:
            where_clauses.append("m.memory_tier = ?")
            params.append(memory_tier.value)

        if content_type:
            where_clauses.append("m.content_type = ?")
            params.append(content_type)

        if tags:
            for tag in tags:
                where_clauses.append(
                    "EXISTS (SELECT 1 FROM json_each(m.tags) WHERE value = ?)"
                )
                params.append(tag)

        where_clause = " AND ".join(where_clauses)

        # Perform vector search
        # The WHERE clause is built from validated enum values and parameterized queries
        # sqlite-vec requires LIMIT in the subquery for knn searches
        cursor = await self.db.execute(
            f"""
            SELECT
                m.*,
                1 - distance as similarity
            FROM (
                SELECT embedding, memory_id, distance
                FROM embeddings
                WHERE embedding MATCH ?
                ORDER BY distance
                LIMIT ?
            ) e
            JOIN memories m ON {where_clause}
            ORDER BY distance
            """,
            tuple([params[0], top_k] + params[1:]),
        )

        rows = await cursor.fetchall()

        results = []
        for row in rows:
            memory = self._row_to_memory(row)
            # Get similarity from last column
            similarity = float(row[-1])
            results.append(SearchResult(memory=memory, similarity=similarity))

        return results

    async def cleanup_expired(self) -> int:
        """Delete expired memories.

        Returns:
            Number of deleted memories
        """
        now = datetime.now(timezone.utc).isoformat()

        # Get expired IDs
        cursor = await self.db.execute(
            "SELECT id FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,),
        )
        rows = await cursor.fetchall()
        expired_ids = [row[0] for row in rows]

        if not expired_ids:
            return 0

        # Validate IDs to prevent injection
        if not all(isinstance(id, str) for id in expired_ids):
            raise ValueError("All IDs must be strings")

        # Delete them
        async with self.db.transaction():
            placeholders = ",".join("?" * len(expired_ids))
            await self.db.execute(
                f"DELETE FROM embeddings WHERE memory_id IN ({placeholders})",
                tuple(expired_ids),
            )
            await self.db.execute(
                f"DELETE FROM memories WHERE id IN ({placeholders})", tuple(expired_ids)
            )

        return len(expired_ids)

    def _row_to_memory(self, row: Any) -> Memory:
        """Convert database row to Memory object.

        Args:
            row: Database row

        Returns:
            Memory object
        """
        return Memory(
            id=row["id"],
            content=row["content"],
            content_type=row["content_type"],
            memory_tier=row["memory_tier"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            agent_id=row["agent_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            expires_at=(
                datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
            ),
        )
