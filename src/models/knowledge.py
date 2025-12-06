"""Knowledge base models."""

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Document(BaseModel):
    """Knowledge document model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    source: str | None = None
    category: str | None = None
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Chunk(BaseModel):
    """Document chunk model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    content: str
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    section_path: list[str] = Field(default_factory=list)
    has_previous: bool = False
    has_next: bool = False


class ChunkResult(BaseModel):
    """Chunk search result with document info."""

    chunk: Chunk
    document: Document
    similarity: float


class DocumentImport(BaseModel):
    """Document import request."""

    title: str
    content: str
    source: str | None = None
    category: str | None = None
    chunk_size: int = 500
    chunk_overlap: int = 50
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentImportResult(BaseModel):
    """Result of document import operation."""

    document_id: str
    chunks_created: int
