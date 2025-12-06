"""Agent and messaging models."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Message type classification."""

    DIRECT = "direct"
    BROADCAST = "broadcast"
    CONTEXT = "context"


class MessageStatus(str, Enum):
    """Message status."""

    PENDING = "pending"
    READ = "read"
    ARCHIVED = "archived"


class AccessLevel(str, Enum):
    """Access level for shared contexts."""

    PUBLIC = "public"
    RESTRICTED = "restricted"


class Agent(BaseModel):
    """Agent model."""

    id: str
    name: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Message(BaseModel):
    """Inter-agent message model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    receiver_id: str | None = None  # None = broadcast
    content: str
    message_type: MessageType = MessageType.DIRECT
    status: MessageStatus = MessageStatus.PENDING
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    read_at: datetime | None = None


class SharedContext(BaseModel):
    """Shared context model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key: str
    value: Any
    owner_agent_id: str
    access_level: AccessLevel = AccessLevel.PUBLIC
    allowed_agents: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
