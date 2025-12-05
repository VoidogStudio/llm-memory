"""MCP server implementation for LLM Memory."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from llm_memory.config.settings import Settings
from llm_memory.db.database import Database
from llm_memory.db.repositories.agent_repository import AgentRepository
from llm_memory.db.repositories.knowledge_repository import KnowledgeRepository
from llm_memory.db.repositories.memory_repository import MemoryRepository
from llm_memory.embeddings.local import LocalEmbeddingProvider
from llm_memory.embeddings.openai import OpenAIEmbeddingProvider
from llm_memory.services.agent_service import AgentService
from llm_memory.services.embedding_service import EmbeddingService
from llm_memory.services.knowledge_service import KnowledgeService
from llm_memory.services.memory_service import MemoryService
from llm_memory.tools import agent_tools, knowledge_tools, memory_tools

# Initialize FastMCP server
mcp = FastMCP("llm-memory")

# Global service instances (initialized in main)
memory_service: MemoryService | None = None
agent_service: AgentService | None = None
knowledge_service: KnowledgeService | None = None
db: Database | None = None


async def initialize_services(settings: Settings) -> None:
    """Initialize all services and database.

    Args:
        settings: Application settings
    """
    global memory_service, agent_service, knowledge_service, db

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

    memory_repo = MemoryRepository(db)
    memory_service = MemoryService(memory_repo, embedding_service)

    agent_repo = AgentRepository(db)
    agent_service = AgentService(agent_repo)

    knowledge_repo = KnowledgeRepository(db)
    knowledge_service = KnowledgeService(knowledge_repo, embedding_service)


async def shutdown_services() -> None:
    """Shutdown all services and close database."""
    global db
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

    Returns:
        The created memory entry with id and timestamps
    """
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await memory_tools.memory_store(
        memory_service, content, content_type, memory_tier, tags, metadata, agent_id, ttl_seconds
    )


@mcp.tool()
async def memory_search(
    query: str,
    top_k: int = 10,
    memory_tier: str | None = None,
    tags: list[str] | None = None,
    content_type: str | None = None,
    min_similarity: float = 0.0,
) -> dict[str, Any]:
    """Search memories using semantic similarity.

    Args:
        query: Search query text
        top_k: Maximum number of results to return
        memory_tier: Filter by memory tier
        tags: Filter by tags (AND condition)
        content_type: Filter by content type
        min_similarity: Minimum similarity threshold (0.0-1.0)

    Returns:
        List of matching memories with similarity scores
    """
    if not memory_service:
        raise RuntimeError("Services not initialized")
    return await memory_tools.memory_search(
        memory_service, query, top_k, memory_tier, tags, content_type, min_similarity
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


def create_server() -> FastMCP:
    """Create and return MCP server instance.

    Returns:
        FastMCP server instance
    """
    return mcp
