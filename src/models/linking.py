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


class MemoryLink(BaseModel):
    """Memory link model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    link_type: LinkType = LinkType.RELATED
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LinkCreate(BaseModel):
    """Link creation request."""

    source_id: str
    target_id: str
    link_type: LinkType = LinkType.RELATED
    bidirectional: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
