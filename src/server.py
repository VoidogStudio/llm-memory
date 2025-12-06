"""MCP server implementation for LLM Memory."""

import asyncio
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.config.settings import Settings
from src.db.database import Database
from src.db.repositories.agent_repository import AgentRepository
from src.db.repositories.knowledge_repository import KnowledgeRepository
from src.db.repositories.memory_repository import MemoryRepository
from src.embeddings.local import LocalEmbeddingProvider
from src.embeddings.openai import OpenAIEmbeddingProvider
from src.services.agent_service import AgentService
from src.services.consolidation_service import ConsolidationService
from src.services.decay_service import DecayService
from src.services.embedding_service import EmbeddingService
from src.services.export_import_service import ExportImportService
from src.services.importance_service import ImportanceService
from src.services.knowledge_service import KnowledgeService
from src.services.linking_service import LinkingService
from src.services.memory_service import MemoryService
from src.services.namespace_service import NamespaceService
from src.tools import (
    agent_tools,
    batch_tools,
    consolidation_tools,
    decay_tools,
    export_import_tools,
    importance_tools,
    knowledge_tools,
    linking_tools,
    memory_tools,
    similarity_tools,
)

# Initialize FastMCP server
mcp = FastMCP("llm-memory")

# Global service instances (initialized in main)
memory_service: MemoryService | None = None
agent_service: AgentService | None = None
knowledge_service: KnowledgeService | None = None
importance_service: ImportanceService | None = None
consolidation_service: ConsolidationService | None = None
decay_service: DecayService | None = None
linking_service: LinkingService | None = None
export_import_service: ExportImportService | None = None
namespace_service: NamespaceService | None = None
db: Database | None = None

# Background tasks
_background_tasks: set[asyncio.Task[None]] = set()


async def initialize_services(settings: Settings) -> None:
    """Initialize all services and database.

    Args:
        settings: Application settings
    """
    global memory_service, agent_service, knowledge_service, importance_service, consolidation_service, decay_service, linking_service, export_import_service, namespace_service, db

    # Initialize database
    db = Database(settings.database_path, settings.embedding_dimensions)
    await db.connect()
    await db.migrate()

    # Initialize embedding provider
    if settings.embedding_provider == "local":
        embedding_provider = LocalEmbeddingProvider(settings.embedding_model)
    else:
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key required for openai provider")
        embedding_provider = OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    # Initialize services
    embedding_service = EmbeddingService(embedding_provider)
    namespace_service = NamespaceService(settings)

    memory_repo = MemoryRepository(db)
    memory_service = MemoryService(memory_repo, embedding_service, namespace_service)

    agent_repo = AgentRepository(db)
    agent_service = AgentService(agent_repo)

    knowledge_repo = KnowledgeRepository(db)
    knowledge_service = KnowledgeService(knowledge_repo, embedding_service)

    importance_service = ImportanceService(memory_repo)
    consolidation_service = ConsolidationService(memory_repo, embedding_service)
    decay_service = DecayService(memory_repo, db)
    linking_service = LinkingService(memory_repo, db)
    export_import_service = ExportImportService(memory_repo, knowledge_repo, agent_repo, db, embedding_service)

    # Start background tasks
    await start_background_tasks()


async def start_background_tasks() -> None:
    """Start background tasks for TTL cleanup."""
    global _background_tasks

    if not memory_service:
        logging.warning("Services not initialized, skipping background tasks")
        return

    # Create TTL cleanup task with safe callback
    task = asyncio.create_task(_ttl_cleanup_task())
    _background_tasks.add(task)

    # Safe callback to handle race condition
    def remove_task(t: asyncio.Task[None]) -> None:
        try:
            _background_tasks.discard(t)
        except Exception as e:
            # Log errors during cleanup for debugging, but don't raise
            logging.debug("Error during background task cleanup: %s", e)

    task.add_done_callback(remove_task)


async def stop_background_tasks() -> None:
    """Stop all background tasks gracefully."""
    global _background_tasks

    if not _background_tasks:
        return

    # Cancel all tasks
    for task in _background_tasks:
        task.cancel()

    # Wait for cancellation with timeout
    try:
        await asyncio.wait_for(
            asyncio.gather(*_background_tasks, return_exceptions=True),
            timeout=5.0,
        )
    except asyncio.TimeoutError:
        logging.warning("Background tasks did not stop within timeout")


async def _ttl_cleanup_task() -> None:
    """Background task for TTL cleanup."""
    settings = Settings()
    interval = settings.cleanup_interval_seconds

    while True:
        try:
            await asyncio.sleep(interval)

            if memory_service:
                count = await memory_service.cleanup_expired()
                if count > 0:
                    logging.info(f"Cleaned up {count} expired memories")
        except asyncio.CancelledError:
            logging.info("TTL cleanup task cancelled")
            raise
        except Exception as e:
            logging.error(f"Error in TTL cleanup: {e}")


async def shutdown_services() -> None:
    """Shutdown all services and close database."""
    global db

    # Stop background tasks first
    await stop_background_tasks()

    # Close database
    if db:
        await db.close()


# Memory Tools
@mcp.tool()
async def memory_store(
    content: str,
    content_type: str = "text",
    memory_tier: str = "long_term",
    tags: list[str] | None = None,
    metadata: dict | None = None,
    agent_id: str | None = None,
    ttl_seconds: int | None = None,
    namespace: str | None = None,
) -> dict[str, Any]:
    """Store a new memory entry with automatic embedding generation.

    Args:
        content: The content to store (text, code, JSON, etc.)
        content_type: Type of content (text/image/code/json/yaml)
        memory_tier: Memory tier (short_term/long_term/working)
        tags: List of tags for categorization
        metadata: Additional metadata as key-value pairs
        ttl_seconds: Time-to-live in seconds (for short_term memories)
        agent_id: Agent ID
        namespace: Target namespace (default: auto-detect from project)

    Returns:
        The created memory entry with id and timestamps
    """
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await memory_tools.memory_store(
        memory_service, content, content_type, memory_tier, tags, metadata, agent_id, ttl_seconds, namespace
    )


@mcp.tool()
async def memory_search(
    query: str,
    top_k: int = 10,
    memory_tier: str | None = None,
    tags: list[str] | None = None,
    content_type: str | None = None,
    min_similarity: float = 0.0,
    namespace: str | None = None,
    search_scope: str = "current",
) -> dict[str, Any]:
    """Search memories using semantic similarity.

    Args:
        query: Search query text
        top_k: Maximum number of results to return
        memory_tier: Filter by memory tier
        tags: Filter by tags (AND condition)
        content_type: Filter by content type
        min_similarity: Minimum similarity threshold (0.0-1.0)
        namespace: Target namespace (default: auto-detect)
        search_scope: Search scope - current (this namespace only), shared (current + shared), all (all namespaces)

    Returns:
        List of matching memories with similarity scores
    """
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await memory_tools.memory_search(
        memory_service, query, top_k, memory_tier, tags, content_type, min_similarity, namespace=namespace, search_scope=search_scope
    )


@mcp.tool()
async def memory_get(id: str) -> dict[str, Any]:
    """Get a specific memory by ID.

    Args:
        id: The memory ID (UUID)

    Returns:
        The complete memory entry or error if not found
    """
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await memory_tools.memory_get(memory_service, id)


@mcp.tool()
async def memory_update(
    id: str,
    content: str | None = None,
    tags: list[str] | None = None,
    metadata: dict | None = None,
    memory_tier: str | None = None,
) -> dict[str, Any]:
    """Update an existing memory entry.

    Args:
        id: The memory ID to update
        content: New content (will regenerate embedding)
        tags: New tags list (replaces existing)
        metadata: Additional metadata (merged with existing)
        memory_tier: New tier (for promotion/demotion)

    Returns:
        Update confirmation with timestamp
    """
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await memory_tools.memory_update(memory_service, id, content, tags, metadata, memory_tier)


@mcp.tool()
async def memory_delete(
    id: str | None = None,
    ids: list[str] | None = None,
    memory_tier: str | None = None,
    older_than: str | None = None,
) -> dict[str, Any]:
    """Delete memories by ID or criteria.

    Args:
        id: Single memory ID to delete
        ids: List of memory IDs to delete
        memory_tier: Delete all memories in this tier
        older_than: Delete memories older than this datetime (ISO format)

    Returns:
        Deletion count and list of deleted IDs
    """
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await memory_tools.memory_delete(memory_service, id, ids, memory_tier, older_than)


@mcp.tool()
async def memory_list(
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
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await memory_tools.memory_list(
        memory_service, memory_tier, tags, content_type, created_after, created_before, limit, offset
    )


# Agent Tools
@mcp.tool()
async def agent_register(
    agent_id: str,
    name: str,
    description: str | None = None,
) -> dict[str, Any]:
    """Register a new agent or get existing.

    Args:
        agent_id: Unique agent identifier
        name: Agent display name
        description: Optional agent description

    Returns:
        Registered agent info
    """
    if not agent_service:
        raise RuntimeError("Services not initialized")
    return await agent_tools.agent_register(agent_service, agent_id, name, description)


@mcp.tool()
async def agent_get(agent_id: str) -> dict[str, Any]:
    """Get an agent by ID.

    Args:
        agent_id: Agent ID to look up

    Returns:
        Agent info or error if not found
    """
    if not agent_service:
        raise RuntimeError("Services not initialized")
    return await agent_tools.agent_get(agent_service, agent_id)


@mcp.tool()
async def agent_send_message(
    sender_id: str,
    content: str,
    receiver_id: str | None = None,
    message_type: str = "direct",
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Send a message to another agent or broadcast.

    Args:
        sender_id: The sending agent's ID
        content: Message content
        receiver_id: Target agent ID (None for broadcast)
        message_type: Type (direct/broadcast/context)
        metadata: Additional metadata

    Returns:
        Sent message ID and timestamp
    """
    if not agent_service:
        raise RuntimeError("Services not initialized")
    return await agent_tools.agent_send_message(
        agent_service, sender_id, content, receiver_id, message_type, metadata
    )


@mcp.tool()
async def agent_receive_messages(
    agent_id: str, status: str = "pending", mark_as_read: bool = True, limit: int = 50
) -> dict[str, Any]:
    """Receive messages for an agent.

    Args:
        agent_id: The receiving agent's ID
        status: Filter by status (pending/read/all)
        mark_as_read: Automatically mark as read
        limit: Maximum messages to return

    Returns:
        List of messages
    """
    if not agent_service:
        raise RuntimeError("Services not initialized")
    return await agent_tools.agent_receive_messages(agent_service, agent_id, status, mark_as_read, limit)


@mcp.tool()
async def context_share(
    key: str,
    value: Any,
    agent_id: str,
    access_level: str = "public",
    allowed_agents: list[str] | None = None,
) -> dict[str, Any]:
    """Share a context value with other agents.

    Args:
        key: Context key (unique identifier)
        value: Value to store (will be JSON serialized)
        agent_id: Owner agent ID
        access_level: Access level (public/restricted)
        allowed_agents: List of agent IDs with access (for restricted)

    Returns:
        Confirmation with timestamp
    """
    if not agent_service:
        raise RuntimeError("Services not initialized")
    return await agent_tools.context_share(agent_service, key, value, agent_id, access_level, allowed_agents)


@mcp.tool()
async def context_read(key: str, agent_id: str) -> dict[str, Any]:
    """Read a shared context value.

    Args:
        key: Context key to read
        agent_id: Reading agent ID (for access check)

    Returns:
        Context value and metadata
    """
    if not agent_service:
        raise RuntimeError("Services not initialized")
    return await agent_tools.context_read(agent_service, key, agent_id)


# Knowledge Tools
@mcp.tool()
async def knowledge_import(
    title: str,
    content: str,
    source: str | None = None,
    category: str | None = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Import a document into the knowledge base.

    Args:
        title: Document title
        content: Full document content
        source: Source URL or file path
        category: Category for organization
        chunk_size: Characters per chunk
        chunk_overlap: Overlap between chunks
        metadata: Additional metadata

    Returns:
        Document ID and chunk count
    """
    if not knowledge_service:
        raise RuntimeError("Services not initialized")
    return await knowledge_tools.knowledge_import(
        knowledge_service, title, content, source, category, chunk_size, chunk_overlap, metadata
    )


@mcp.tool()
async def knowledge_query(
    query: str,
    top_k: int = 5,
    category: str | None = None,
    document_id: str | None = None,
    include_document_info: bool = True,
) -> dict[str, Any]:
    """Query the knowledge base.

    Args:
        query: Search query
        top_k: Number of chunks to return
        category: Filter by category
        document_id: Filter by document
        include_document_info: Include document metadata

    Returns:
        Matching chunks with similarity scores
    """
    if not knowledge_service:
        raise RuntimeError("Services not initialized")
    return await knowledge_tools.knowledge_query(
        knowledge_service, query, top_k, category, document_id, include_document_info
    )


# Similarity Tools
@mcp.tool()
async def memory_similar(
    id: str,
    top_k: int = 10,
    min_similarity: float = 0.7,
    namespace: str | None = None,
    search_scope: str = "current",
    exclude_linked: bool = True,
) -> dict[str, Any]:
    """Find memories similar to a specified memory.

    Args:
        id: Base memory ID to find similar memories for
        top_k: Maximum number of results to return (1-1000)
        min_similarity: Minimum similarity threshold (0.0-1.0)
        namespace: Target namespace (default: auto-detect)
        search_scope: Search scope (current/shared/all)
        exclude_linked: Exclude already linked memories

    Returns:
        Similar memories with similarity scores
    """
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await similarity_tools.memory_similar(
        memory_service, id, top_k, min_similarity, namespace, search_scope, exclude_linked
    )


@mcp.tool()
async def memory_deduplicate(
    namespace: str | None = None,
    similarity_threshold: float = 0.95,
    dry_run: bool = True,
    merge_strategy: str = "keep_newest",
    merge_metadata: bool = True,
    limit: int = 1000,
    use_lsh: bool = True,
) -> dict[str, Any]:
    """Detect and optionally merge duplicate memories.

    Args:
        namespace: Target namespace (default: auto-detect)
        similarity_threshold: Similarity threshold for duplicates (0.0-1.0)
        dry_run: Preview mode without actual deletion (default: True)
        merge_strategy: Strategy for choosing primary (keep_newest/keep_oldest/highest_importance)
        merge_metadata: Merge metadata from duplicates into primary
        limit: Maximum memories to process (1-10000)
        use_lsh: Use LSH optimization for faster duplicate detection

    Returns:
        Duplicate groups and merge results
    """
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await similarity_tools.memory_deduplicate(
        memory_service, namespace, similarity_threshold, dry_run, merge_strategy, merge_metadata, limit, use_lsh
    )


# Batch Tools
@mcp.tool()
async def memory_batch_store(
    items: list[dict[str, Any]],
    on_error: str = "rollback",
) -> dict[str, Any]:
    """Store multiple memories in a single batch operation.

    Args:
        items: List of memory items (each has memory_store params)
        on_error: Error handling strategy (rollback/continue/stop)

    Returns:
        Batch operation result with success/error counts
    """
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await batch_tools.memory_batch_store(memory_service, items, on_error)


@mcp.tool()
async def memory_batch_update(
    updates: list[dict[str, Any]],
    on_error: str = "rollback",
) -> dict[str, Any]:
    """Update multiple memories in a single batch operation.

    Args:
        updates: List of updates (each has {id: str, ...fields})
        on_error: Error handling strategy (rollback/continue/stop)

    Returns:
        Batch operation result with success/error counts
    """
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await batch_tools.memory_batch_update(memory_service, updates, on_error)


# Importance Tools
@mcp.tool()
async def memory_get_score(id: str) -> dict[str, Any]:
    """Get importance score for a memory.

    Args:
        id: Memory ID

    Returns:
        Score info with access statistics
    """
    if not importance_service:
        raise RuntimeError("Services not initialized")
    return await importance_tools.memory_get_score(importance_service, id)


@mcp.tool()
async def memory_set_score(
    id: str,
    score: float,
    reason: str | None = None,
) -> dict[str, Any]:
    """Manually set importance score for a memory.

    Args:
        id: Memory ID
        score: New score (0.0-1.0)
        reason: Optional reason for manual override (for audit trail)

    Returns:
        Previous and new score info
    """
    if not importance_service:
        raise RuntimeError("Services not initialized")
    return await importance_tools.memory_set_score(importance_service, id, score, reason)


# Consolidation Tools
@mcp.tool()
async def memory_consolidate(
    memory_ids: list[str],
    summary_strategy: str = "auto",
    preserve_originals: bool = True,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Consolidate multiple memories into a single summarized memory.

    Args:
        memory_ids: List of memory IDs to consolidate (2-50)
        summary_strategy: Summarization strategy (auto/extractive)
        preserve_originals: Keep original memories (default True)
        tags: Tags for consolidated memory
        metadata: Additional metadata

    Returns:
        Consolidation result
    """
    if not consolidation_service:
        raise RuntimeError("Services not initialized")
    return await consolidation_tools.memory_consolidate(
        consolidation_service, memory_ids, summary_strategy, preserve_originals, tags, metadata
    )


# Decay Tools
@mcp.tool()
async def memory_decay_configure(
    enabled: bool | None = None,
    threshold: float | None = None,
    grace_period_days: int | None = None,
    auto_run_interval_hours: int | None = None,
    max_delete_per_run: int | None = None,
) -> dict[str, Any]:
    """Configure memory decay settings.

    Args:
        enabled: Enable/disable decay
        threshold: Importance score threshold (0.0-1.0)
        grace_period_days: Days before deletion eligible (min: 1)
        auto_run_interval_hours: Auto-run interval (reserved for future)
        max_delete_per_run: Maximum deletions per run (1-10000)

    Returns:
        Updated configuration
    """
    if not decay_service:
        raise RuntimeError("Services not initialized")
    return await decay_tools.memory_decay_configure(
        decay_service, enabled, threshold, grace_period_days, auto_run_interval_hours, max_delete_per_run
    )


@mcp.tool()
async def memory_decay_run(
    threshold: float | None = None,
    grace_period_days: int | None = None,
    dry_run: bool = False,
    max_delete: int | None = None,
) -> dict[str, Any]:
    """Run memory decay to delete low-importance memories.

    Args:
        threshold: Override importance threshold
        grace_period_days: Override grace period
        dry_run: If True, only preview without deleting
        max_delete: Override maximum deletions

    Returns:
        Deletion results with affected IDs
    """
    if not decay_service:
        raise RuntimeError("Services not initialized")
    return await decay_tools.memory_decay_run(decay_service, threshold, grace_period_days, dry_run, max_delete)


@mcp.tool()
async def memory_decay_status() -> dict[str, Any]:
    """Get current decay status and statistics.

    Returns:
        Configuration and statistics
    """
    if not decay_service:
        raise RuntimeError("Services not initialized")
    return await decay_tools.memory_decay_status(decay_service)


# Linking Tools
@mcp.tool()
async def memory_link(
    source_id: str,
    target_id: str,
    link_type: str = "related",
    bidirectional: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a link between two memories.

    Args:
        source_id: Source memory ID
        target_id: Target memory ID
        link_type: Link type (related/parent/child/similar/reference)
        bidirectional: Create reverse link automatically
        metadata: Optional link metadata

    Returns:
        Created link information
    """
    if not linking_service:
        raise RuntimeError("Services not initialized")
    return await linking_tools.memory_link(linking_service, source_id, target_id, link_type, bidirectional, metadata)


@mcp.tool()
async def memory_unlink(
    source_id: str,
    target_id: str,
    link_type: str | None = None,
) -> dict[str, Any]:
    """Remove link(s) between two memories.

    Args:
        source_id: Source memory ID
        target_id: Target memory ID
        link_type: Specific type to remove (None = all)

    Returns:
        Deletion count
    """
    if not linking_service:
        raise RuntimeError("Services not initialized")
    return await linking_tools.memory_unlink(linking_service, source_id, target_id, link_type)


@mcp.tool()
async def memory_get_links(
    memory_id: str,
    link_type: str | None = None,
    direction: str = "both",
) -> dict[str, Any]:
    """Get links for a memory.

    Args:
        memory_id: Memory ID
        link_type: Filter by link type
        direction: Direction filter (outgoing/incoming/both)

    Returns:
        List of links
    """
    if not linking_service:
        raise RuntimeError("Services not initialized")
    return await linking_tools.memory_get_links(linking_service, memory_id, link_type, direction)


# Export/Import Tools
@mcp.tool()
async def database_export(
    output_path: str | None = None,
    include_embeddings: bool = True,
    memory_tier: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    format: str = "jsonl",
) -> dict[str, Any]:
    """Export database to file.

    Args:
        output_path: Output file path (required)
        include_embeddings: Include embedding vectors
        memory_tier: Filter by memory tier
        created_after: Filter by creation date (ISO format)
        created_before: Filter by creation date (ISO format)
        format: Output format (jsonl)

    Returns:
        Export results and statistics
    """
    if not export_import_service:
        raise RuntimeError("Services not initialized")
    return await export_import_tools.database_export(
        export_import_service, output_path, include_embeddings, memory_tier, created_after, created_before, format
    )


@mcp.tool()
async def database_import(
    input_path: str,
    mode: str = "merge",
    on_conflict: str = "skip",
    regenerate_embeddings: bool = False,
) -> dict[str, Any]:
    """Import database from file.

    Args:
        input_path: Input file path
        mode: Import mode (replace/merge)
        on_conflict: Conflict handling (skip/update/error)
        regenerate_embeddings: Regenerate embeddings from content

    Returns:
        Import results and statistics
    """
    if not export_import_service:
        raise RuntimeError("Services not initialized")
    return await export_import_tools.database_import(export_import_service, input_path, mode, on_conflict, regenerate_embeddings)


def create_server() -> FastMCP:
    """Create and return MCP server instance.

    Returns:
        FastMCP server instance
    """
    return mcp
