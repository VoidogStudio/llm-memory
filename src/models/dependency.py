"""Memory dependency models."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .linking import LinkType


class NotificationType(str, Enum):
    """Dependency notification types."""

    UPDATE = "update"
    DELETE = "delete"
    STALE = "stale"


class DependencyNotification(BaseModel):
    """Dependency change notification."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_memory_id: str
    target_memory_id: str
    notification_type: NotificationType
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: datetime | None = None


class AffectedMemory(BaseModel):
    """Memory affected by dependency cascade."""

    memory_id: str
    depth: int
    link_type: LinkType
    cascade_type: str  # 'update' | 'delete'
    strength: float


class DependencyAnalysis(BaseModel):
    """Result of dependency impact analysis."""

    source_memory_id: str
    affected_memories: list[AffectedMemory] = Field(default_factory=list)
    total_affected: int
    max_depth_reached: int
    has_cycles: bool
    cycle_paths: list[list[str]] = Field(default_factory=list)
