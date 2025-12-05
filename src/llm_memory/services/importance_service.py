"""Importance scoring service."""

import math
from datetime import datetime, timedelta, timezone

from llm_memory.db.repositories.memory_repository import MemoryRepository


class ImportanceService:
    """Service for managing memory importance scores."""

    # Score calculation parameters
    RECENCY_WEIGHT: float = 0.6
    FREQUENCY_WEIGHT: float = 0.4
    DECAY_RATE: float = 30.0  # days
    MAX_ACCESSES: int = 100

    def __init__(self, repository: MemoryRepository) -> None:
        """Initialize importance service.

        Args:
            repository: Memory repository instance
        """
        self.repository = repository

    def calculate_score(
        self,
        access_count: int,
        last_accessed_at: datetime | None,
        created_at: datetime,
    ) -> float:
        """Calculate importance score based on access patterns.

        Args:
            access_count: Number of times memory was accessed
            last_accessed_at: Last access timestamp
            created_at: Memory creation timestamp

        Returns:
            Importance score between 0.0 and 1.0
        """
        now = datetime.now(timezone.utc)

        # Recency score (exponential decay)
        if last_accessed_at:
            days_since_access = (now - last_accessed_at).total_seconds() / 86400
        else:
            days_since_access = (now - created_at).total_seconds() / 86400

        recency_score = math.exp(-days_since_access / self.DECAY_RATE)

        # Frequency score (normalized)
        frequency_score = min(access_count / self.MAX_ACCESSES, 1.0)

        # Combined score
        importance = (
            self.RECENCY_WEIGHT * recency_score + self.FREQUENCY_WEIGHT * frequency_score
        )

        return round(importance, 4)

    async def calculate_and_update_score(self, memory_id: str) -> float:
        """Calculate and update importance score for a memory.

        Args:
            memory_id: Memory ID

        Returns:
            New importance score
        """
        now = datetime.now(timezone.utc)

        # Get current stats
        stats = await self.repository.get_access_stats(memory_id)

        # Calculate new score
        new_score = self.calculate_score(
            access_count=stats["access_count"],
            last_accessed_at=stats["last_accessed_at"],
            created_at=stats["created_at"],
        )

        # Update importance fields
        await self.repository.update_importance(
            memory_id=memory_id,
            score=new_score,
            access_count=stats["access_count"],
            last_accessed_at=stats["last_accessed_at"] or now,
        )

        return new_score

    async def log_access(
        self,
        memory_id: str,
        access_type: str,  # 'get' | 'search'
    ) -> None:
        """Log memory access and update score.

        Args:
            memory_id: Accessed memory ID
            access_type: Type of access
        """
        now = datetime.now(timezone.utc)

        # Log access
        await self.repository.log_access(memory_id, access_type)

        # Get current stats
        stats = await self.repository.get_access_stats(memory_id)

        # Calculate new score
        new_score = self.calculate_score(
            access_count=stats["access_count"] + 1,
            last_accessed_at=now,
            created_at=stats["created_at"],
        )

        # Update importance fields
        await self.repository.update_importance(
            memory_id=memory_id,
            score=new_score,
            access_count=stats["access_count"] + 1,
            last_accessed_at=now,
        )

    async def get_score(self, memory_id: str) -> dict:
        """Get importance score for a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Score info with access statistics

        Raises:
            NotFoundError: If memory doesn't exist
        """
        stats = await self.repository.get_access_stats(memory_id)

        return {
            "memory_id": memory_id,
            "importance_score": stats["importance_score"],
            "access_count": stats["access_count"],
            "last_accessed_at": (
                stats["last_accessed_at"].isoformat() if stats["last_accessed_at"] else None
            ),
            "score_updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def set_score(
        self,
        memory_id: str,
        score: float,
        reason: str | None = None,
    ) -> dict:
        """Manually set importance score.

        Args:
            memory_id: Memory ID
            score: New score (0.0-1.0)
            reason: Optional reason for manual override (for audit trail)

        Returns:
            Previous and new score info

        Raises:
            ValueError: If score out of range
            NotFoundError: If memory doesn't exist
        """
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {score}")

        if reason is None:
            reason = "Manual override"

        # Get previous score
        stats = await self.repository.get_access_stats(memory_id)
        previous_score = stats["importance_score"]

        # Update score
        await self.repository.update_importance(
            memory_id=memory_id,
            score=score,
        )

        # Log the manual override to access log for audit trail
        import uuid

        log_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await self.repository.db.execute(
            """
            INSERT INTO memory_access_log (id, memory_id, accessed_at, access_type)
            VALUES (?, ?, ?, ?)
            """,
            (
                log_id,
                memory_id,
                now,
                f"score_override: {previous_score:.3f} -> {score:.3f} ({reason})",
            ),
        )
        await self.repository.db.commit()

        return {
            "memory_id": memory_id,
            "previous_score": previous_score,
            "new_score": score,
            "reason": reason,
            "updated_at": now,
        }

    async def cleanup_access_logs(self, retention_days: int = 30) -> int:
        """Clean up old access logs.

        Args:
            retention_days: Days to retain logs

        Returns:
            Number of deleted log entries
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
        return await self.repository.cleanup_access_logs(cutoff_time)
