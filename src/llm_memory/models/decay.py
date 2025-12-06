"""Memory decay models."""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class DecayConfig(BaseModel):
    """Decay configuration model."""

    enabled: bool = False
    threshold: float = Field(default=0.1, ge=0.0, le=1.0)
    grace_period_days: int = Field(default=7, ge=1)
    auto_run_interval_hours: int = Field(default=24, ge=1)
    max_delete_per_run: int = Field(default=100, ge=1, le=10000)
    last_run_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DecayLog(BaseModel):
    """Decay execution log model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_count: int
    deleted_ids: list[str]
    threshold: float
    dry_run: bool


class DecayRunResult(BaseModel):
    """Result of decay run operation."""

    deleted_count: int
    deleted_ids: list[str]
    threshold: float
    grace_period_days: int
    dry_run: bool
    next_candidates_count: int | None = None
    failed_count: int = 0
    failed_ids: list[str] = Field(default_factory=list)
    errors: list[dict] | None = None
