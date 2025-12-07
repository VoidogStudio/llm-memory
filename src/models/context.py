"""Context building models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass
class ContextMemory:
    """Memory item in context result."""

    id: str
    content: str
    original_tokens: int
    tokens: int
    summarized: bool
    similarity: float
    importance_score: float
    source: Literal["direct", "related"]
    depth: int
    link_type: str | None = None


@dataclass
class ContextResult:
    """Result of context building."""

    memories: list[ContextMemory]
    total_tokens: int
    token_budget: int
    memories_count: int
    summarized_count: int
    related_count: int
    cache_hit: bool = False


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    query_hash: str
    query_embedding: list[float]
    result: Any
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    hit_count: int = 0
    last_accessed: datetime | None = None


@dataclass
class CacheStats:
    """Cache statistics."""

    total_entries: int
    hit_count: int
    miss_count: int
    hit_rate: float
    memory_usage_bytes: int
    oldest_entry: datetime | None
    newest_entry: datetime | None


@dataclass
class GraphNode:
    """Node in graph traversal."""

    memory_id: str
    depth: int
    link_type: str | None
    path: list[str] = field(default_factory=list)
