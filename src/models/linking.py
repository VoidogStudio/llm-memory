"""Memory linking models."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LinkType(str, Enum):
    """Link type classification."""

    RELATED = "related"
    PARENT = "parent"
    CHILD = "child"
    SIMILAR = "similar"
    REFERENCE = "reference"
    DEPENDS_ON = "depends_on"  # v1.7.0
    DERIVED_FROM = "derived_from"  # v1.7.0


class MemoryLink(BaseModel):
    """Memory link model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    link_type: LinkType = LinkType.RELATED
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # v1.7.0 Dependency Tracking
    cascade_on_update: bool = False
    cascade_on_delete: bool = False
    strength: float = Field(default=1.0, ge=0.0, le=1.0)


class LinkCreate(BaseModel):
    """Link creation request."""

    source_id: str
    target_id: str
    link_type: LinkType = LinkType.RELATED
    bidirectional: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
