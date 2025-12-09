"""Memory schema models."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Schema field types."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    ARRAY = "array"
    OBJECT = "object"


class SchemaField(BaseModel):
    """Schema field definition."""

    name: str
    type: FieldType
    required: bool = False
    indexed: bool = False
    description: str | None = None
    default: Any | None = None
    validation: dict[str, Any] | None = None  # min, max, pattern, enum


class MemorySchema(BaseModel):
    """Memory schema definition."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    namespace: str
    version: int = 1
    fields: list[SchemaField]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TypedMemoryCreate(BaseModel):
    """Typed memory creation request."""

    schema_name: str
    namespace: str | None = None
    structured_content: dict[str, Any]
    content: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
