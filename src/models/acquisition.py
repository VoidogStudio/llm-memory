"""Acquisition models for Auto Knowledge Acquisition feature."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Source type classification."""

    PROJECT_SCAN = "project_scan"
    KNOWLEDGE_SYNC = "knowledge_sync"
    SESSION_LEARNING = "session_learning"
    MANUAL = "manual"


class SyncSourceType(str, Enum):
    """Sync source type."""

    LOCAL_FILE = "local_file"
    LOCAL_DIRECTORY = "local_directory"
    URL = "url"
    GITHUB_REPO = "github_repo"


class LearningCategory(str, Enum):
    """Learning category."""

    ERROR_RESOLUTION = "error_resolution"
    DESIGN_DECISION = "design_decision"
    BEST_PRACTICE = "best_practice"
    USER_PREFERENCE = "user_preference"


class ProjectType(str, Enum):
    """Project type classification."""

    PYTHON = "python"
    NODEJS = "nodejs"
    RUST = "rust"
    GO = "go"
    JAVA = "java"
    UNKNOWN = "unknown"


class StalenessAction(str, Enum):
    """Staleness action."""

    REFRESH = "refresh"
    ARCHIVE = "archive"
    DELETE = "delete"


class ScanStatistics(BaseModel):
    """Scan statistics."""

    files_scanned: int = 0
    memories_created: int = 0
    memories_updated: int = 0
    errors: int = 0
    skipped_files: int = 0


class DetectedConfig(BaseModel):
    """Detected project configuration."""

    package_manager: str | None = None
    test_framework: str | None = None
    linter: str | None = None
    formatter: str | None = None
    language_version: str | None = None


class ScanResult(BaseModel):
    """Project scan result."""

    scan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_name: str
    namespace: str
    scanned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    statistics: ScanStatistics
    project_type: ProjectType
    detected_config: DetectedConfig
    categories: dict[str, int] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class SyncStatistics(BaseModel):
    """Sync statistics."""

    files_processed: int = 0
    chunks_created: int = 0
    chunks_updated: int = 0
    chunks_deleted: int = 0
    unchanged: int = 0


class SyncDocumentInfo(BaseModel):
    """Sync document information."""

    document_id: str
    title: str
    source_file: str
    chunks_count: int
    status: str  # "created" | "updated" | "unchanged"


class SyncResult(BaseModel):
    """Knowledge sync result."""

    sync_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: SyncSourceType
    source_path: str
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    statistics: SyncStatistics
    documents: list[SyncDocumentInfo] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class SimilarLearning(BaseModel):
    """Similar learning information."""

    memory_id: str
    content: str
    similarity: float
    category: LearningCategory


class LearningResult(BaseModel):
    """Session learning result."""

    learning_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_id: str
    category: LearningCategory
    content: str
    confidence: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    similar_learnings: list[SimilarLearning] = Field(default_factory=list)
    action_taken: str = "created"  # "created" | "updated" | "skipped"


class StalenessStatistics(BaseModel):
    """Staleness check statistics."""

    total_checked: int = 0
    stale_count: int = 0
    source_changed: int = 0
    not_accessed: int = 0
    both_conditions: int = 0


class StaleMemoryInfo(BaseModel):
    """Stale memory information."""

    memory_id: str
    content_preview: str
    source_type: SourceType
    source_file: str | None
    staleness_reason: list[str]
    last_accessed_at: datetime | None
    days_since_access: int | None
    source_hash_current: str | None
    source_hash_stored: str | None


class StalenessRecommendation(BaseModel):
    """Staleness recommendation."""

    action: str  # "rescan" | "review" | "delete"
    target: str  # "project" | "sync" | "learning"
    reason: str


class StalenessResult(BaseModel):
    """Staleness check result."""

    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    namespace: str
    statistics: StalenessStatistics
    stale_memories: list[StaleMemoryInfo] = Field(default_factory=list)
    recommendations: list[StalenessRecommendation] = Field(default_factory=list)


class RefreshResult(BaseModel):
    """Refresh result."""

    action: StalenessAction
    dry_run: bool
    affected_count: int
    affected_memories: list[dict[str, Any]] = Field(default_factory=list)
