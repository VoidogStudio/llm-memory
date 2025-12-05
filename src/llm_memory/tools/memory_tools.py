"""Memory-related MCP tools."""

from datetime import datetime
from typing import Any

from llm_memory.models.memory import ContentType, MemoryTier
from llm_memory.services.memory_service import MemoryService
from llm_memory.tools import create_error_response


async def memory_store(
    service: MemoryService,
    content: str,
    content_type: str = "text",
    memory_tier: str = "long_term",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    agent_id: str | None = None,
    ttl_seconds: int | None = None,
) -> dict[str, Any]:
    """Store a new memory entry with automatic embedding generation.

    Args:
        service: Memory service instance
        content: The content to store
        content_type: Type of content (text/image/code/json/yaml)
        memory_tier: Memory tier (short_term/long_term/working)
        tags: List of tags for categorization
        metadata: Additional metadata
        agent_id: Agent ID
        ttl_seconds: Time-to-live in seconds (for short_term memories)

    Returns:
        Created memory entry with id and timestamps
    """
    # Content validation
    if not content or not content.strip():
        return create_error_response(
            message="Content cannot be empty",
            error_type="ValidationError",
        )

    # memory_tier validation
    try:
        tier = MemoryTier(memory_tier)
    except ValueError:
        return create_error_response(
            message=f"Invalid memory_tier: {memory_tier}. Must be one of: short_term, long_term, working",
            error_type="ValidationError",
        )

    # content_type validation
    try:
        ctype = ContentType(content_type)
    except ValueError:
        return create_error_response(
            message=f"Invalid content_type: {content_type}. Must be one of: text, image, code, json, yaml",
            error_type="ValidationError",
        )

    # ttl_seconds validation
    if ttl_seconds is not None and ttl_seconds < 0:
        return create_error_response(
            message="ttl_seconds must be >= 0",
            error_type="ValidationError",
        )

    memory = await service.store(
        content=content,
        content_type=ctype,
        memory_tier=tier,
        tags=tags,
        metadata=metadata,
        agent_id=agent_id,
        ttl_seconds=ttl_seconds,
    )

    return {
        "id": memory.id,
        "content": memory.content,
        "memory_tier": memory.memory_tier.value,
        "created_at": memory.created_at.isoformat(),
    }


async def memory_search(
    service: MemoryService,
    query: str,
    top_k: int = 10,
    memory_tier: str | None = None,
    tags: list[str] | None = None,
    content_type: str | None = None,
    min_similarity: float = 0.0,
) -> dict[str, Any]:
    """Search memories using semantic similarity.

    Args:
        service: Memory service instance
        query: Search query text
        top_k: Maximum number of results to return
        memory_tier: Filter by memory tier
        tags: Filter by tags (AND condition)
        content_type: Filter by content type
        min_similarity: Minimum similarity threshold (0.0-1.0)

    Returns:
        List of matching memories with similarity scores
    """
    # top_k validation
    if top_k < 1 or top_k > 1000:
        return create_error_response(
            message="top_k must be between 1 and 1000",
            error_type="ValidationError",
        )

    # min_similarity validation
    if min_similarity < 0.0 or min_similarity > 1.0:
        return create_error_response(
            message="min_similarity must be between 0.0 and 1.0",
            error_type="ValidationError",
        )

    tier = MemoryTier(memory_tier) if memory_tier else None

    results = await service.search(
        query=query,
        top_k=top_k,
        memory_tier=tier,
        tags=tags,
        content_type=content_type,
        min_similarity=min_similarity,
    )

    return {
        "results": [
            {
                "id": r.memory.id,
                "content": r.memory.content,
                "similarity": r.similarity,
                "memory_tier": r.memory.memory_tier.value,
                "tags": r.memory.tags,
                "created_at": r.memory.created_at.isoformat(),
            }
            for r in results
        ],
        "total": len(results),
    }


async def memory_get(service: MemoryService, id: str) -> dict[str, Any]:
    """Get a specific memory by ID.

    Args:
        service: Memory service instance
        id: The memory ID (UUID)

    Returns:
        The complete memory entry or error if not found
    """
    memory = await service.get(id)

    if not memory:
        return create_error_response(
            message=f"Memory not found: {id}",
            error_type="NotFoundError",
        )

    return {
        "id": memory.id,
        "content": memory.content,
        "content_type": memory.content_type.value,
        "memory_tier": memory.memory_tier.value,
        "tags": memory.tags,
        "metadata": memory.metadata,
        "created_at": memory.created_at.isoformat(),
        "updated_at": memory.updated_at.isoformat(),
        "expires_at": memory.expires_at.isoformat() if memory.expires_at else None,
    }


async def memory_update(
    service: MemoryService,
    id: str,
    content: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    memory_tier: str | None = None,
) -> dict[str, Any]:
    """Update an existing memory entry.

    Args:
        service: Memory service instance
        id: The memory ID to update
        content: New content (will regenerate embedding)
        tags: New tags list (replaces existing)
        metadata: Additional metadata (merged with existing)
        memory_tier: New tier (for promotion/demotion)

    Returns:
        Update confirmation with timestamp
    """
    tier = MemoryTier(memory_tier) if memory_tier else None

    memory = await service.update(
        memory_id=id, content=content, tags=tags, metadata=metadata, memory_tier=tier
    )

    if not memory:
        return create_error_response(
            message=f"Memory not found: {id}",
            error_type="NotFoundError",
        )

    return {"id": memory.id, "updated": True, "updated_at": memory.updated_at.isoformat()}


async def memory_delete(
    service: MemoryService,
    id: str | None = None,
    ids: list[str] | None = None,
    memory_tier: str | None = None,
    older_than: str | None = None,
) -> dict[str, Any]:
    """Delete memories by ID or criteria.

    Args:
        service: Memory service instance
        id: Single memory ID to delete
        ids: List of memory IDs to delete
        memory_tier: Delete all memories in this tier
        older_than: Delete memories older than this datetime (ISO format)

    Returns:
        Deletion count and list of deleted IDs
    """
    tier = MemoryTier(memory_tier) if memory_tier else None
    older_dt = datetime.fromisoformat(older_than) if older_than else None

    deleted_ids = await service.delete(
        memory_id=id, ids=ids, memory_tier=tier, older_than=older_dt
    )

    return {"deleted_count": len(deleted_ids), "deleted_ids": deleted_ids}


async def memory_list(
    service: MemoryService,
    memory_tier: str | None = None,
    tags: list[str] | None = None,
    content_type: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List memories with filtering and pagination.

    Args:
        service: Memory service instance
        memory_tier: Filter by tier
        tags: Filter by tags (AND condition)
        content_type: Filter by content type
        created_after: Filter by creation date (ISO format)
        created_before: Filter by creation date (ISO format)
        limit: Maximum results (default 50, max 1000)
        offset: Pagination offset

    Returns:
        List of memories with pagination info
    """
    tier = MemoryTier(memory_tier) if memory_tier else None
    after_dt = datetime.fromisoformat(created_after) if created_after else None
    before_dt = datetime.fromisoformat(created_before) if created_before else None

    memories, total = await service.list_memories(
        memory_tier=tier,
        tags=tags,
        content_type=content_type,
        created_after=after_dt,
        created_before=before_dt,
        limit=limit,
        offset=offset,
    )

    return {
        "memories": [
            {
                "id": m.id,
                "content": m.content,
                "content_type": m.content_type.value,
                "memory_tier": m.memory_tier.value,
                "tags": m.tags,
                "created_at": m.created_at.isoformat(),
            }
            for m in memories
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
