"""Agent repository for database operations."""

import json
from datetime import datetime, timezone
from typing import Any

from llm_memory.db.database import Database
from llm_memory.models.agent import (
    AccessLevel,
    Agent,
    Message,
    MessageStatus,
    MessageType,
    SharedContext,
)


class AgentRepository:
    """Repository for agent operations."""

    def __init__(self, db: Database) -> None:
        """Initialize repository.

        Args:
            db: Database instance
        """
        self.db = db

    async def create(self, agent: Agent) -> Agent:
        """Create a new agent.

        Args:
            agent: Agent object to create

        Returns:
            Created agent object
        """
        await self.db.execute(
            """
            INSERT INTO agents (id, name, description, metadata, created_at, last_active_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                agent.id,
                agent.name,
                agent.description,
                json.dumps(agent.metadata),
                agent.created_at.isoformat(),
                agent.last_active_at.isoformat(),
            ),
        )
        await self.db.commit()
        return agent

    async def find_by_id(self, agent_id: str) -> Agent | None:
        """Find agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent object or None if not found
        """
        cursor = await self.db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
        row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_agent(row)

    async def update_last_active(self, agent_id: str) -> None:
        """Update agent's last active timestamp.

        Args:
            agent_id: Agent ID
        """
        await self.db.execute(
            "UPDATE agents SET last_active_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), agent_id),
        )
        await self.db.commit()

    async def create_message(self, message: Message) -> Message:
        """Create a new message.

        Args:
            message: Message object to create

        Returns:
            Created message object
        """
        await self.db.execute(
            """
            INSERT INTO messages (
                id, sender_id, receiver_id, content, message_type,
                status, metadata, created_at, read_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.id,
                message.sender_id,
                message.receiver_id,
                message.content,
                message.message_type.value,
                message.status.value,
                json.dumps(message.metadata),
                message.created_at.isoformat(),
                message.read_at.isoformat() if message.read_at else None,
            ),
        )
        await self.db.commit()
        return message

    async def find_messages(
        self, agent_id: str, status: MessageStatus | None = None, limit: int = 50
    ) -> list[Message]:
        """Find messages for an agent.

        Args:
            agent_id: Agent ID
            status: Filter by message status
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        # Build query
        if status and status != MessageStatus.PENDING:
            if status == MessageStatus.READ:
                query = """
                    SELECT * FROM messages
                    WHERE (receiver_id = ? OR receiver_id IS NULL)
                    AND status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """
                params = (agent_id, status.value, limit)
            else:
                query = """
                    SELECT * FROM messages
                    WHERE (receiver_id = ? OR receiver_id IS NULL)
                    AND status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """
                params = (agent_id, status.value, limit)
        else:
            # Default to pending
            query = """
                SELECT * FROM messages
                WHERE (receiver_id = ? OR receiver_id IS NULL)
                AND status = 'pending'
                ORDER BY created_at DESC
                LIMIT ?
            """
            params = (agent_id, limit)

        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()

        return [self._row_to_message(row) for row in rows]

    async def mark_messages_as_read(self, message_ids: list[str]) -> None:
        """Mark messages as read.

        Args:
            message_ids: List of message IDs to mark as read
        """
        if not message_ids:
            return

        # Validate IDs to prevent injection
        if not all(isinstance(id, str) for id in message_ids):
            raise ValueError("All IDs must be strings")

        placeholders = ",".join("?" * len(message_ids))
        await self.db.execute(
            f"""
            UPDATE messages
            SET status = 'read', read_at = ?
            WHERE id IN ({placeholders})
            """,
            tuple([datetime.now(timezone.utc).isoformat()] + message_ids),
        )
        await self.db.commit()

    async def upsert_context(self, context: SharedContext) -> SharedContext:
        """Create or update a shared context.

        Args:
            context: SharedContext object

        Returns:
            Created or updated context
        """
        # Check if exists
        cursor = await self.db.execute(
            "SELECT id FROM shared_contexts WHERE key = ?", (context.key,)
        )
        existing = await cursor.fetchone()

        if existing:
            # Update existing
            await self.db.execute(
                """
                UPDATE shared_contexts
                SET value = ?, owner_agent_id = ?, access_level = ?,
                    allowed_agents = ?, updated_at = ?
                WHERE key = ?
                """,
                (
                    json.dumps(context.value),
                    context.owner_agent_id,
                    context.access_level.value,
                    json.dumps(context.allowed_agents),
                    datetime.now(timezone.utc).isoformat(),
                    context.key,
                ),
            )
        else:
            # Insert new
            await self.db.execute(
                """
                INSERT INTO shared_contexts (
                    id, key, value, owner_agent_id, access_level,
                    allowed_agents, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context.id,
                    context.key,
                    json.dumps(context.value),
                    context.owner_agent_id,
                    context.access_level.value,
                    json.dumps(context.allowed_agents),
                    context.created_at.isoformat(),
                    context.updated_at.isoformat(),
                ),
            )

        await self.db.commit()
        return context

    async def find_context(self, key: str) -> SharedContext | None:
        """Find shared context by key.

        Args:
            key: Context key

        Returns:
            SharedContext object or None if not found
        """
        cursor = await self.db.execute(
            "SELECT * FROM shared_contexts WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_context(row)

    def _row_to_agent(self, row: Any) -> Agent:
        """Convert database row to Agent object.

        Args:
            row: Database row

        Returns:
            Agent object
        """
        return Agent(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
            last_active_at=datetime.fromisoformat(row["last_active_at"]),
        )

    def _row_to_message(self, row: Any) -> Message:
        """Convert database row to Message object.

        Args:
            row: Database row

        Returns:
            Message object
        """
        return Message(
            id=row["id"],
            sender_id=row["sender_id"],
            receiver_id=row["receiver_id"],
            content=row["content"],
            message_type=MessageType(row["message_type"]),
            status=MessageStatus(row["status"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
            read_at=datetime.fromisoformat(row["read_at"]) if row["read_at"] else None,
        )

    def _row_to_context(self, row: Any) -> SharedContext:
        """Convert database row to SharedContext object.

        Args:
            row: Database row

        Returns:
            SharedContext object
        """
        return SharedContext(
            id=row["id"],
            key=row["key"],
            value=json.loads(row["value"]),
            owner_agent_id=row["owner_agent_id"],
            access_level=AccessLevel(row["access_level"]),
            allowed_agents=json.loads(row["allowed_agents"]) if row["allowed_agents"] else [],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
