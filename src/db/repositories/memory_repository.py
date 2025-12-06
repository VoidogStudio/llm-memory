"""Memory repository for database operations."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from src.db.database import Database
from src.models.memory import Memory, MemoryTier, SearchResult


class MemoryRepository:
    """Repository for memory operations."""

    def __init__(self, db: Database) -> None:
        """Initialize repository.

        Args:
            db: Database instance
        """
        self.db = db

    async def create(
        self, memory: Memory, embedding: list[float], use_transaction: bool = True
    ) -> Memory:
        """Create a new memory entry with embedding.

        Args:
            memory: Memory object to create
            embedding: Embedding vector
            use_transaction: Whether to wrap in transaction (False for batch operations)

        Returns:
            Created memory object
        """
        if use_transaction:
            async with self.db.transaction():
                await self._insert_memory_and_embedding(memory, embedding)
        else:
            await self._insert_memory_and_embedding(memory, embedding)

        return memory

    async def _insert_memory_and_embedding(
        self, memory: Memory, embedding: list[float]
    ) -> None:
        """Internal method to insert memory and embedding without transaction.

        Args:
            memory: Memory object to create
            embedding: Embedding vector
        """
        # Insert memory
        await self.db.execute(
            """
            INSERT INTO memories (
                id, content, content_type, memory_tier, tags, metadata,
                agent_id, created_at, updated_at, expires_at,
                importance_score, access_count, last_accessed_at, consolidated_from,
                namespace
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                memory.importance_score,
                memory.access_count,
                (
                    memory.last_accessed_at.isoformat()
                    if memory.last_accessed_at
                    else None
                ),
                (
                    json.dumps(memory.consolidated_from)
                    if memory.consolidated_from
                    else None
                ),
                memory.namespace,
            ),
        )

        # Insert embedding
        embedding_str = json.dumps(embedding)
        await self.db.execute(
            "INSERT INTO embeddings (memory_id, embedding) VALUES (?, ?)",
            (memory.id, embedding_str),
        )

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

    async def update(self, memory_id: str, updates: dict[str, Any], use_transaction: bool = True) -> Memory | None:
        """Update memory entry.

        Args:
            memory_id: Memory ID
            updates: Fields to update
            use_transaction: Whether to wrap in transaction (default True)

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

        if use_transaction:
            async with self.db.transaction():
                await self.db.execute(
                    f"UPDATE memories SET {', '.join(set_clauses)} WHERE id = ?", tuple(params)
                )

                # If content updated, update embedding (handled by service layer)
        else:
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

    async def delete(self, memory_id: str, use_transaction: bool = True) -> bool:
        """Delete memory by ID.

        Args:
            memory_id: Memory ID
            use_transaction: Whether to wrap in transaction (default True)

        Returns:
            True if deleted, False if not found
        """
        if use_transaction:
            async with self.db.transaction():
                # Delete embedding first
                await self.db.execute("DELETE FROM embeddings WHERE memory_id = ?", (memory_id,))

                # Delete memory
                cursor = await self.db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

            return cursor.rowcount > 0
        else:
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
        namespace: str | None = None,
        search_scope: str = "current",
    ) -> list[SearchResult]:
        """Perform vector similarity search.

        Args:
            embedding: Query embedding vector
            top_k: Number of results to return
            memory_tier: Memory tier filter
            tags: Tags filter
            content_type: Content type filter
            namespace: Target namespace filter
            search_scope: Search scope (current/shared/all)

        Returns:
            List of search results with similarity scores
        """
        # Build WHERE clause and parameters using safe construction
        # Always include base join condition
        where_clauses = ["e.memory_id = m.id"]
        filter_params: list[Any] = []

        # Add namespace filtering based on search_scope
        if namespace and search_scope == "current":
            where_clauses.append("m.namespace = ?")
            filter_params.append(namespace)
        elif namespace and search_scope == "shared":
            where_clauses.append("m.namespace IN (?, 'shared')")
            filter_params.append(namespace)
        # search_scope == "all": no namespace filter

        if memory_tier:
            where_clauses.append("m.memory_tier = ?")
            filter_params.append(memory_tier.value)

        if content_type:
            where_clauses.append("m.content_type = ?")
            filter_params.append(content_type)

        if tags:
            for tag in tags:
                where_clauses.append(
                    "EXISTS (SELECT 1 FROM json_each(m.tags) WHERE value = ?)"
                )
                filter_params.append(tag)

        where_clause = " AND ".join(where_clauses)

        # Perform vector search with fully parameterized query
        # sqlite-vec requires LIMIT in the subquery for knn searches
        # Note: sqlite-vec cosine distance ranges from 0 to 2
        # (0 = identical, 2 = opposite direction)
        # Convert to similarity: 1 - distance/2 gives range 0 to 1
        cursor = await self.db.execute(
            f"""
            SELECT
                m.*,
                (1.0 - distance / 2.0) as similarity
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
            tuple([json.dumps(embedding), top_k] + filter_params),
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
        # Convert Row to dict to support .get() method
        row_dict = dict(row)

        return Memory(
            id=row_dict["id"],
            content=row_dict["content"],
            content_type=row_dict["content_type"],
            memory_tier=row_dict["memory_tier"],
            tags=json.loads(row_dict["tags"]) if row_dict["tags"] else [],
            metadata=json.loads(row_dict["metadata"]) if row_dict["metadata"] else {},
            agent_id=row_dict["agent_id"],
            created_at=datetime.fromisoformat(row_dict["created_at"]),
            updated_at=datetime.fromisoformat(row_dict["updated_at"]),
            expires_at=(
                datetime.fromisoformat(row_dict["expires_at"])
                if row_dict["expires_at"]
                else None
            ),
            importance_score=row_dict.get("importance_score", 0.5),
            access_count=row_dict.get("access_count", 0),
            last_accessed_at=(
                datetime.fromisoformat(row_dict["last_accessed_at"])
                if row_dict.get("last_accessed_at")
                else None
            ),
            consolidated_from=(
                json.loads(row_dict["consolidated_from"])
                if row_dict.get("consolidated_from")
                else None
            ),
            namespace=row_dict.get("namespace", "default"),
        )

    async def log_access(
        self,
        memory_id: str,
        access_type: str,
        timestamp: datetime | None = None,
    ) -> None:
        """Log memory access with rate limiting to prevent log flooding.

        Rate limiting: Only logs if no entry exists for this memory within the last 60 seconds.
        This prevents DoS attacks via access log flooding while maintaining useful analytics.

        Also updates access_count and last_accessed_at on the memory.

        Args:
            memory_id: Memory ID
            access_type: 'get' or 'search'
            timestamp: Optional timestamp for testing (defaults to current time)
        """
        import uuid

        now = timestamp if timestamp else datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # Rate limiting: Check if there's a recent log entry (within 60 seconds)
        one_minute_ago = (now - timedelta(seconds=60)).isoformat()

        cursor = await self.db.execute(
            """
            SELECT 1 FROM memory_access_log
            WHERE memory_id = ? AND access_type = ? AND accessed_at > ?
            LIMIT 1
            """,
            (memory_id, access_type, one_minute_ago),
        )
        recent_log = await cursor.fetchone()

        # Only insert if no recent log exists (rate limiting)
        if recent_log is None:
            log_id = str(uuid.uuid4())
            await self.db.execute(
                """
                INSERT INTO memory_access_log (id, memory_id, accessed_at, access_type)
                VALUES (?, ?, ?, ?)
                """,
                (log_id, memory_id, now_iso, access_type),
            )
            await self.db.commit()

        # Always update access_count and last_accessed_at on the memory
        await self.db.execute(
            """
            UPDATE memories
            SET access_count = access_count + 1, last_accessed_at = ?
            WHERE id = ?
            """,
            (now_iso, memory_id),
        )
        await self.db.commit()

    async def update_importance(
        self,
        memory_id: str,
        score: float,
        access_count: int | None = None,
        last_accessed_at: datetime | None = None,
    ) -> None:
        """Update importance score fields.

        Args:
            memory_id: Memory ID
            score: New importance score
            access_count: Optional access count update
            last_accessed_at: Optional last access time update
        """
        updates = ["importance_score = ?"]
        params: list[Any] = [score]

        if access_count is not None:
            updates.append("access_count = ?")
            params.append(access_count)

        if last_accessed_at is not None:
            updates.append("last_accessed_at = ?")
            params.append(last_accessed_at.isoformat())

        params.append(memory_id)

        await self.db.execute(
            f"UPDATE memories SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        await self.db.commit()

    async def get_access_stats(self, memory_id: str) -> dict:
        """Get access statistics for a memory.

        Args:
            memory_id: Memory ID

        Returns:
            {access_count, last_accessed_at, importance_score, created_at}

        Raises:
            NotFoundError: If memory doesn't exist
        """
        from src.exceptions import NotFoundError

        cursor = await self.db.execute(
            """
            SELECT access_count, last_accessed_at, importance_score, created_at
            FROM memories WHERE id = ?
            """,
            (memory_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise NotFoundError(f"Memory not found: {memory_id}")

        return {
            "access_count": row[0] or 0,
            "last_accessed_at": (
                datetime.fromisoformat(row[1]) if row[1] else None
            ),
            "importance_score": row[2] or 0.5,
            "created_at": datetime.fromisoformat(row[3]),
        }

    async def cleanup_access_logs(self, older_than: datetime) -> int:
        """Delete access logs older than specified datetime.

        Args:
            older_than: Delete logs before this time

        Returns:
            Number of deleted entries
        """
        cursor = await self.db.execute(
            "DELETE FROM memory_access_log WHERE accessed_at < ?",
            (older_than.isoformat(),),
        )
        await self.db.commit()
        return cursor.rowcount

    async def keyword_search(
        self,
        query: str,
        top_k: int,
        memory_tier: MemoryTier | None = None,
        tags: list[str] | None = None,
        content_type: str | None = None,
        namespace: str | None = None,
        search_scope: str = "current",
    ) -> list[tuple[str, float]]:
        """Perform FTS5 keyword search.

        Args:
            query: Tokenized search query
            top_k: Maximum results
            memory_tier: Optional tier filter
            tags: Optional tags filter
            content_type: Optional content type filter
            namespace: Target namespace filter
            search_scope: Search scope (current/shared/all)

        Returns:
            List of (memory_id, bm25_score) tuples
        """
        # Build WHERE clause and parameters using safe construction
        # Always include base join condition (use content_id from FTS table)
        where_clauses = ["mf.content_id = m.id"]
        filter_params: list[Any] = []

        # Add namespace filtering based on search_scope
        if namespace and search_scope == "current":
            where_clauses.append("m.namespace = ?")
            filter_params.append(namespace)
        elif namespace and search_scope == "shared":
            where_clauses.append("m.namespace IN (?, 'shared')")
            filter_params.append(namespace)
        # search_scope == "all": no namespace filter

        if memory_tier:
            where_clauses.append("m.memory_tier = ?")
            # Handle both Enum and string values
            tier_value = (
                memory_tier.value if isinstance(memory_tier, MemoryTier) else memory_tier
            )
            filter_params.append(tier_value)

        if content_type:
            where_clauses.append("m.content_type = ?")
            filter_params.append(content_type)

        if tags:
            for tag in tags:
                where_clauses.append(
                    "EXISTS (SELECT 1 FROM json_each(m.tags) WHERE value = ?)"
                )
                filter_params.append(tag)

        where_clause = " AND ".join(where_clauses)

        # Perform FTS5 search with fully parameterized query
        cursor = await self.db.execute(
            f"""
            SELECT
                m.id,
                bm25(memories_fts) as score
            FROM memories_fts mf
            JOIN memories m ON {where_clause}
            WHERE mf.content MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            tuple(filter_params + [query, top_k]),
        )

        rows = await cursor.fetchall()
        return [(row[0], float(row[1])) for row in rows]

    async def hybrid_search(
        self,
        query: str,
        embedding: list[float],
        top_k: int,
        keyword_weight: float = 0.3,
        memory_tier: MemoryTier | None = None,
        tags: list[str] | None = None,
        content_type: str | None = None,
        namespace: str | None = None,
        search_scope: str = "current",
    ) -> list[SearchResult]:
        """Perform hybrid search (semantic + keyword).

        Args:
            query: Search query text
            embedding: Query embedding vector
            top_k: Maximum results
            keyword_weight: Weight for keyword scores in combination
            memory_tier: Optional tier filter
            tags: Optional tags filter
            content_type: Optional content type filter
            namespace: Target namespace filter
            search_scope: Search scope (current/shared/all)

        Returns:
            List of SearchResult with combined scores
        """
        from src.utils.rrf import reciprocal_rank_fusion

        # Perform semantic search
        semantic_results = await self.vector_search(
            embedding=embedding,
            top_k=top_k * 2,
            memory_tier=memory_tier,
            tags=tags,
            content_type=content_type,
            namespace=namespace,
            search_scope=search_scope,
        )

        # Perform keyword search
        keyword_tuples = await self.keyword_search(
            query=query,
            top_k=top_k * 2,
            memory_tier=memory_tier,
            tags=tags,
            content_type=content_type,
            namespace=namespace,
            search_scope=search_scope,
        )

        # Convert to format for RRF
        semantic_tuples = [(r.memory.id, r.similarity) for r in semantic_results]

        # Combine using RRF
        combined = reciprocal_rank_fusion(semantic_tuples, keyword_tuples)

        # Get top_k results and fetch full memory objects
        results = []
        for memory_id, rrf_score in combined[:top_k]:
            # Find memory in semantic results
            memory_obj = None
            semantic_score = 0.0
            for sr in semantic_results:
                if sr.memory.id == memory_id:
                    memory_obj = sr.memory
                    semantic_score = sr.similarity
                    break

            # If not in semantic, fetch it
            if memory_obj is None:
                memory_obj = await self.find_by_id(memory_id)
                if memory_obj is None:
                    continue

            # Find keyword score
            keyword_score = 0.0
            for kid, kscore in keyword_tuples:
                if kid == memory_id:
                    keyword_score = abs(kscore)  # BM25 can be negative
                    break

            results.append(
                SearchResult(
                    memory=memory_obj,
                    similarity=semantic_score,
                    keyword_score=keyword_score,
                    combined_score=rrf_score,
                )
            )

        return results

    async def find_similar_memories(
        self,
        memory_id: str,
        top_k: int,
        min_similarity: float,
        namespace: str | None,
        search_scope: str,
        exclude_linked: bool,
    ) -> list[SearchResult]:
        """Find memories similar to a specified memory.

        Args:
            memory_id: Base memory ID
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            namespace: Target namespace
            search_scope: Search scope (current/shared/all)
            exclude_linked: Exclude already linked memories

        Returns:
            List of similar memories with similarity scores
        """
        # Get base memory embedding
        cursor = await self.db.execute(
            "SELECT vec_to_json(embedding) FROM embeddings WHERE memory_id = ?", (memory_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return []

        embedding = json.loads(row[0])

        # Search for similar memories
        results = await self.vector_search(
            embedding=embedding,
            top_k=top_k + 1,  # +1 to account for self
            namespace=namespace,
            search_scope=search_scope,
        )

        # Filter out self and below threshold
        filtered = [
            r
            for r in results
            if r.memory.id != memory_id and r.similarity >= min_similarity
        ]

        return filtered[:top_k]

    async def find_duplicates(
        self,
        namespace: str,
        similarity_threshold: float = 0.95,
        limit: int = 1000,
        use_lsh: bool = True,
    ) -> list[dict[str, Any]]:
        """Find duplicate memory groups.

        Args:
            namespace: Target namespace
            similarity_threshold: Similarity threshold for duplicates
            limit: Maximum memories to process
            use_lsh: Use LSH optimization

        Returns:
            List of duplicate groups
        """
        if use_lsh:
            from src.services.lsh_index import LSH_AVAILABLE, LSHIndex

            if not LSH_AVAILABLE:
                use_lsh = False

        # Get memories from namespace
        cursor = await self.db.execute(
            """
            SELECT id FROM memories
            WHERE namespace = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (namespace, limit),
        )
        rows = await cursor.fetchall()
        memory_ids = [row[0] for row in rows]

        if not memory_ids:
            return []

        # Build LSH index if requested
        lsh_index = None
        if use_lsh:
            from src.services.lsh_index import LSHIndex

            lsh_index = LSHIndex()
            await lsh_index.build_index(self, namespace=namespace)

        # Find duplicates
        duplicate_groups = []
        processed = set()

        for memory_id in memory_ids:
            if memory_id in processed:
                continue

            # Get embedding
            cursor = await self.db.execute(
                "SELECT vec_to_json(embedding) FROM embeddings WHERE memory_id = ?", (memory_id,)
            )
            row = await cursor.fetchone()
            if not row:
                continue

            embedding = json.loads(row[0])

            # Find candidates
            if lsh_index:
                candidates = lsh_index.query_candidates(embedding, max_candidates=100)
            else:
                candidates = set(memory_ids)

            # Find similar memories
            duplicates = []
            for candidate_id in candidates:
                if candidate_id == memory_id or candidate_id in processed:
                    continue

                # Get candidate embedding
                cursor = await self.db.execute(
                    "SELECT vec_to_json(embedding) FROM embeddings WHERE memory_id = ?",
                    (candidate_id,),
                )
                row = await cursor.fetchone()
                if not row:
                    continue

                candidate_embedding = json.loads(row[0])

                # Compute cosine similarity
                try:
                    import numpy as np

                    emb1 = np.array(embedding)
                    emb2 = np.array(candidate_embedding)
                    similarity = float(
                        np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                    )
                except ImportError:
                    # Fallback without numpy
                    dot_product = sum(a * b for a, b in zip(embedding, candidate_embedding, strict=False))
                    norm1 = sum(a * a for a in embedding) ** 0.5
                    norm2 = sum(b * b for b in candidate_embedding) ** 0.5
                    similarity = dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0

                if similarity >= similarity_threshold:
                    duplicates.append(candidate_id)
                    processed.add(candidate_id)

            if duplicates:
                avg_similarity = similarity_threshold  # Simplified
                duplicate_groups.append(
                    {
                        "primary_id": memory_id,
                        "duplicate_ids": duplicates,
                        "avg_similarity": avg_similarity,
                    }
                )
                processed.add(memory_id)

        return duplicate_groups

    async def get_all_embeddings(
        self,
        namespace: str | None = None,
        limit: int | None = None,
    ) -> list[tuple[str, list[float]]]:
        """Get all embeddings for LSH index building.

        Args:
            namespace: Target namespace filter
            limit: Maximum number of embeddings to retrieve

        Returns:
            List of (memory_id, embedding) tuples
        """
        if namespace:
            query = """
                SELECT m.id, vec_to_json(e.embedding)
                FROM memories m
                JOIN embeddings e ON e.memory_id = m.id
                WHERE m.namespace = ?
                ORDER BY m.created_at DESC
            """
            params: tuple[Any, ...] = (namespace,)
        else:
            query = """
                SELECT m.id, vec_to_json(e.embedding)
                FROM memories m
                JOIN embeddings e ON e.memory_id = m.id
                ORDER BY m.created_at DESC
            """
            params = ()

        if limit:
            query += " LIMIT ?"
            params = params + (limit,)

        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()

        results = []
        for row in rows:
            memory_id = row[0]
            embedding = json.loads(row[1])
            results.append((memory_id, embedding))

        return results
