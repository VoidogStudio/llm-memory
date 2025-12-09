"""Memory versioning models."""

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class MemoryVersion(BaseModel):
    """Memory version snapshot."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_id: str
    version: int
    content: str
    content_type: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    change_reason: str | None = None


class VersionDiff(BaseModel):
    """Difference between two versions."""

    memory_id: str
    old_version: int
    new_version: int
    content_changed: bool
    content_diff: str | None = None  # unified diff format
    tags_added: list[str] = Field(default_factory=list)
    tags_removed: list[str] = Field(default_factory=list)
    metadata_changed: dict[str, Any] = Field(default_factory=dict)


class VersionHistory(BaseModel):
    """Version history for a memory."""

    memory_id: str
    current_version: int
    total_versions: int
    versions: list[MemoryVersion] = Field(default_factory=list)
