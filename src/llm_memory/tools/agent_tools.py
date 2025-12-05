"""Agent-related MCP tools."""

from typing import Any

from llm_memory.models.agent import AccessLevel, MessageStatus, MessageType
from llm_memory.services.agent_service import AgentService


async def agent_register(
    service: AgentService,
    agent_id: str,
    name: str,
    description: str | None = None,
) -> dict[str, Any]:
    """Register a new agent or get existing.

    Args:
        service: Agent service instance
        agent_id: Unique agent identifier
        name: Agent display name
        description: Optional agent description

    Returns:
        Registered agent info
    """
    agent = await service.register(agent_id=agent_id, name=name, description=description)

    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "created_at": agent.created_at.isoformat(),
        "registered": True,
    }


async def agent_get(
    service: AgentService,
    agent_id: str,
) -> dict[str, Any]:
    """Get an agent by ID.

    Args:
        service: Agent service instance
        agent_id: Agent ID to look up

    Returns:
        Agent info or error if not found
    """
    agent = await service.repository.find_by_id(agent_id)

    if not agent:
        raise ValueError(f"Agent not found: {agent_id}")

    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "created_at": agent.created_at.isoformat(),
        "last_active_at": agent.last_active_at.isoformat() if agent.last_active_at else None,
    }


async def agent_send_message(
    service: AgentService,
    sender_id: str,
    content: str,
    receiver_id: str | None = None,
    message_type: str = "direct",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a message to another agent or broadcast.

    Args:
        service: Agent service instance
        sender_id: The sending agent's ID
        content: Message content
        receiver_id: Target agent ID (None for broadcast)
        message_type: Type (direct/broadcast/context)
        metadata: Additional metadata

    Returns:
        Sent message ID and timestamp
    """
    message = await service.send_message(
        sender_id=sender_id,
        content=content,
        receiver_id=receiver_id,
        message_type=MessageType(message_type),
        metadata=metadata,
    )

    return {"id": message.id, "sent": True, "created_at": message.created_at.isoformat()}


async def agent_receive_messages(
    service: AgentService,
    agent_id: str,
    status: str = "pending",
    mark_as_read: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    """Receive messages for an agent.

    Args:
        service: Agent service instance
        agent_id: The receiving agent's ID
        status: Filter by status (pending/read/all)
        mark_as_read: Automatically mark as read
        limit: Maximum messages to return

    Returns:
        List of messages
    """
    msg_status = MessageStatus(status) if status != "all" else MessageStatus.PENDING

    messages = await service.receive_messages(
        agent_id=agent_id, status=msg_status, mark_as_read=mark_as_read, limit=limit
    )

    return {
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "content": m.content,
                "message_type": m.message_type.value,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "total": len(messages),
    }


async def context_share(
    service: AgentService,
    key: str,
    value: Any,
    agent_id: str,
    access_level: str = "public",
    allowed_agents: list[str] | None = None,
) -> dict[str, Any]:
    """Share a context value with other agents.

    Args:
        service: Agent service instance
        key: Context key (unique identifier)
        value: Value to store (will be JSON serialized)
        agent_id: Owner agent ID
        access_level: Access level (public/restricted)
        allowed_agents: List of agent IDs with access (for restricted)

    Returns:
        Confirmation with timestamp
    """
    context = await service.share_context(
        key=key,
        value=value,
        agent_id=agent_id,
        access_level=AccessLevel(access_level),
        allowed_agents=allowed_agents,
    )

    return {"key": context.key, "stored": True, "updated_at": context.updated_at.isoformat()}


async def context_read(service: AgentService, key: str, agent_id: str) -> dict[str, Any]:
    """Read a shared context value.

    Args:
        service: Agent service instance
        key: Context key to read
        agent_id: Reading agent ID (for access check)

    Returns:
        Context value and metadata
    """
    context = await service.read_context(key=key, agent_id=agent_id)

    if not context:
        raise ValueError(f"Context not found or access denied: {key}")

    return {
        "key": context.key,
        "value": context.value,
        "owner_agent_id": context.owner_agent_id,
        "updated_at": context.updated_at.isoformat(),
    }
