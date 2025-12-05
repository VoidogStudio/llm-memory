"""Memory models."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryTier(str, Enum):
    """Memory tier classification."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working"


class ContentType(str, Enum):
    """Content type classification."""

    TEXT = "text"
    IMAGE = "image"
    CODE = "code"
    JSON = "json"
    YAML = "yaml"


class Memory(BaseModel):
    """Memory entry model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    content_type: ContentType = ContentType.TEXT
    memory_tier: MemoryTier = MemoryTier.LONG_TERM
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    agent_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    # Importance scoring fields (FR-002)
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    access_count: int = Field(default=0, ge=0)
    last_accessed_at: datetime | None = None
    # Memory consolidation field (FR-001)
    consolidated_from: list[str] | None = None


class MemoryCreate(BaseModel):
    """Memory creation request."""

    content: str
    content_type: ContentType = ContentType.TEXT
    memory_tier: MemoryTier = MemoryTier.LONG_TERM
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    agent_id: str | None = None
    ttl_seconds: int | None = None


class MemoryUpdate(BaseModel):
    """Memory update request."""

    content: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    memory_tier: MemoryTier | None = None


class SearchResult(BaseModel):
    """Search result with similarity score."""

    memory: Memory
    similarity: float
    # Hybrid search fields (FR-003)
    keyword_score: float | None = None
    combined_score: float | None = None
