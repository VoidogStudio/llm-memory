"""Export/Import models."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ExportMetadata(BaseModel):
    """Export file metadata."""

    schema_version: int = 3
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    llm_memory_version: str = "1.2.0"
    counts: dict[str, int] = Field(default_factory=dict)


class ExportResult(BaseModel):
    """Result of export operation."""

    exported_at: datetime
    schema_version: int
    counts: dict[str, int]
    file_path: str
    file_size_bytes: int


class ImportResult(BaseModel):
    """Result of import operation."""

    imported_at: datetime
    schema_version: int
    mode: str
    counts: dict[str, int]
    skipped_count: int = 0
    error_count: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
