"""Agent service for business logic."""

from datetime import datetime, timezone
from typing import Any

from llm_memory.db.repositories.agent_repository import AgentRepository
from llm_memory.models.agent import (
    AccessLevel,
    Agent,
    Message,
    MessageStatus,
    MessageType,
    SharedContext,
)


class AgentService:
    """Service for agent operations."""

    def __init__(self, repository: AgentRepository) -> None:
        """Initialize agent service.

        Args:
            repository: Agent repository
        """
        self.repository = repository

    async def register(
        self, agent_id: str, name: str, description: str | None = None
    ) -> Agent:
        """Register a new agent or get existing.

        Args:
            agent_id: Agent ID
            name: Agent name
            description: Agent description

        Returns:
            Agent object
        """
        # Check if agent exists
        existing = await self.repository.find_by_id(agent_id)
        if existing:
            return existing

        # Create new agent
        now = datetime.now(timezone.utc)
        agent = Agent(
            id=agent_id,
            name=name,
            description=description,
            created_at=now,
            last_active_at=now,
        )

        return await self.repository.create(agent)

    async def send_message(
        self,
        sender_id: str,
        content: str,
        receiver_id: str | None = None,
        message_type: MessageType = MessageType.DIRECT,
        metadata: dict | None = None,
    ) -> Message:
        """Send a message to another agent or broadcast.

        Args:
            sender_id: Sender agent ID
            content: Message content
            receiver_id: Receiver agent ID (None for broadcast)
            message_type: Message type
            metadata: Additional metadata

        Returns:
            Created message
        """
        # Ensure sender exists (auto-register)
        await self.register(sender_id, sender_id)

        # Create message
        message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )

        # Store message
        created = await self.repository.create_message(message)

        # Update sender's last active
        await self.repository.update_last_active(sender_id)

        return created

    async def receive_messages(
        self,
        agent_id: str,
        status: MessageStatus | None = MessageStatus.PENDING,
        mark_as_read: bool = True,
        limit: int = 50,
    ) -> list[Message]:
        """Receive messages for an agent.

        Args:
            agent_id: Agent ID
            status: Filter by status (None for all messages)
            mark_as_read: Mark messages as read
            limit: Maximum messages

        Returns:
            List of messages
        """
        # Ensure agent exists
        await self.register(agent_id, agent_id)

        # Get messages
        messages = await self.repository.find_messages(agent_id, status, limit)

        # Mark as read if requested
        if mark_as_read and messages:
            message_ids = [msg.id for msg in messages if msg.status == MessageStatus.PENDING]
            if message_ids:
                await self.repository.mark_messages_as_read(message_ids)

        # Update agent's last active
        await self.repository.update_last_active(agent_id)

        return messages

    async def share_context(
        self,
        key: str,
        value: Any,
        agent_id: str,
        access_level: AccessLevel = AccessLevel.PUBLIC,
        allowed_agents: list[str] | None = None,
    ) -> SharedContext:
        """Share a context value.

        Args:
            key: Context key
            value: Context value
            agent_id: Owner agent ID
            access_level: Access level
            allowed_agents: Allowed agent IDs for restricted access

        Returns:
            Created or updated context
        """
        # Ensure agent exists
        await self.register(agent_id, agent_id)

        # Create context
        context = SharedContext(
            key=key,
            value=value,
            owner_agent_id=agent_id,
            access_level=access_level,
            allowed_agents=allowed_agents or [],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        return await self.repository.upsert_context(context)

    async def read_context(self, key: str, agent_id: str) -> SharedContext | None:
        """Read a shared context value.

        Args:
            key: Context key
            agent_id: Reading agent ID

        Returns:
            Context or None if not found or access denied
        """
        # Get context
        context = await self.repository.find_context(key)

        if not context:
            return None

        # Check access
        if context.access_level == AccessLevel.RESTRICTED:
            if agent_id not in context.allowed_agents and agent_id != context.owner_agent_id:
                return None

        return context
