"""Memory service for business logic."""

from datetime import datetime, timedelta, timezone

from llm_memory.db.repositories.memory_repository import MemoryRepository
from llm_memory.models.memory import (
    ContentType,
    Memory,
    MemoryTier,
    SearchResult,
)
from llm_memory.services.embedding_service import EmbeddingService


class MemoryService:
    """Service for memory operations."""

    def __init__(
        self, repository: MemoryRepository, embedding_service: EmbeddingService
    ) -> None:
        """Initialize memory service.

        Args:
            repository: Memory repository
            embedding_service: Embedding service
        """
        self.repository = repository
        self.embedding_service = embedding_service

    async def store(
        self,
        content: str,
        content_type: ContentType = ContentType.TEXT,
        memory_tier: MemoryTier = MemoryTier.LONG_TERM,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        agent_id: str | None = None,
        ttl_seconds: int | None = None,
    ) -> Memory:
        """Store a new memory entry.

        Args:
            content: Memory content
            content_type: Content type
            memory_tier: Memory tier
            tags: Tags for categorization
            metadata: Additional metadata
            agent_id: Agent ID
            ttl_seconds: Time-to-live in seconds

        Returns:
            Created memory object
        """
        # Create memory object
        now = datetime.now(timezone.utc)
        expires_at = None

        if ttl_seconds:
            expires_at = now + timedelta(seconds=ttl_seconds)

        memory = Memory(
            content=content,
            content_type=content_type,
            memory_tier=memory_tier,
            tags=tags or [],
            metadata=metadata or {},
            agent_id=agent_id,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
        )

        # Generate embedding
        embedding = await self.embedding_service.generate(content)

        # Store in repository
        return await self.repository.create(memory, embedding)

    async def search(
        self,
        query: str,
        top_k: int = 10,
        memory_tier: MemoryTier | None = None,
        tags: list[str] | None = None,
        content_type: str | None = None,
        min_similarity: float = 0.0,
    ) -> list[SearchResult]:
        """Search memories using semantic similarity.

        Args:
            query: Search query
            top_k: Number of results
            memory_tier: Filter by tier
            tags: Filter by tags
            content_type: Filter by content type
            min_similarity: Minimum similarity threshold

        Returns:
            List of search results
        """
        # Generate query embedding
        embedding = await self.embedding_service.generate(query)

        # Perform vector search
        results = await self.repository.vector_search(
            embedding=embedding,
            top_k=top_k,
            memory_tier=memory_tier,
            tags=tags,
            content_type=content_type,
        )

        # Filter by minimum similarity
        if min_similarity > 0.0:
            results = [r for r in results if r.similarity >= min_similarity]

        return results

    async def get(self, memory_id: str) -> Memory | None:
        """Get memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Memory object or None if not found
        """
        return await self.repository.find_by_id(memory_id)

    async def update(
        self,
        memory_id: str,
        content: str | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        memory_tier: MemoryTier | None = None,
    ) -> Memory | None:
        """Update memory entry.

        Args:
            memory_id: Memory ID
            content: New content
            tags: New tags
            metadata: New metadata
            memory_tier: New tier

        Returns:
            Updated memory or None if not found
        """
        updates = {}

        if content is not None:
            updates["content"] = content

        if tags is not None:
            updates["tags"] = tags

        if metadata is not None:
            updates["metadata"] = metadata

        if memory_tier is not None:
            updates["memory_tier"] = memory_tier

        # Update memory first
        memory = await self.repository.update(memory_id, updates)

        # If content changed, regenerate and update embedding
        if content is not None and memory is not None:
            new_embedding = await self.embedding_service.generate(content)
            # Update embedding in repository
            await self.repository.update_embedding(memory_id, new_embedding)

        return memory

    async def delete(
        self,
        memory_id: str | None = None,
        ids: list[str] | None = None,
        memory_tier: MemoryTier | None = None,
        older_than: datetime | None = None,
    ) -> list[str]:
        """Delete memories.

        Args:
            memory_id: Single memory ID
            ids: List of memory IDs
            memory_tier: Delete by tier
            older_than: Delete older than datetime

        Returns:
            List of deleted IDs
        """
        if memory_id:
            deleted = await self.repository.delete(memory_id)
            return [memory_id] if deleted else []

        if ids or memory_tier or older_than:
            return await self.repository.delete_many(
                ids=ids, memory_tier=memory_tier, older_than=older_than
            )

        return []

    async def list_memories(
        self,
        memory_tier: MemoryTier | None = None,
        tags: list[str] | None = None,
        content_type: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Memory], int]:
        """List memories with filters.

        Args:
            memory_tier: Filter by tier
            tags: Filter by tags
            content_type: Filter by content type
            created_after: Created after datetime
            created_before: Created before datetime
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (memories list, total count)
        """
        return await self.repository.find_by_filters(
            memory_tier=memory_tier,
            tags=tags,
            content_type=content_type,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            offset=offset,
        )

    async def cleanup_expired(self) -> int:
        """Clean up expired memories.

        Returns:
            Number of deleted memories
        """
        return await self.repository.cleanup_expired()
