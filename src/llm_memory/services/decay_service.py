"""Service for managing memory decay."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from llm_memory.db.database import Database
from llm_memory.db.repositories.memory_repository import MemoryRepository
from llm_memory.models.decay import DecayConfig, DecayLog, DecayRunResult


class DecayService:
    """Service for managing memory decay."""

    def __init__(self, repository: MemoryRepository, db: Database) -> None:
        """Initialize decay service.

        Args:
            repository: Memory repository
            db: Database instance
        """
        self.repository = repository
        self.db = db

    async def configure(
        self,
        enabled: bool | None = None,
        threshold: float | None = None,
        grace_period_days: int | None = None,
        auto_run_interval_hours: int | None = None,
        max_delete_per_run: int | None = None,
    ) -> DecayConfig:
        """Configure decay settings.

        Args:
            enabled: Enable/disable decay
            threshold: Importance score threshold (0.0-1.0)
            grace_period_days: Days before deletion eligible
            auto_run_interval_hours: Auto-run interval (reserved)
            max_delete_per_run: Max deletions per run

        Returns:
            Updated DecayConfig

        Raises:
            ValueError: If parameters out of range
        """
        # Validate parameters
        if threshold is not None and (threshold < 0.0 or threshold > 1.0):
            raise ValueError("threshold must be between 0.0 and 1.0")
        if grace_period_days is not None and grace_period_days < 1:
            raise ValueError("grace_period_days must be >= 1")
        if auto_run_interval_hours is not None and auto_run_interval_hours < 1:
            raise ValueError("auto_run_interval_hours must be >= 1")
        if max_delete_per_run is not None and (max_delete_per_run < 1 or max_delete_per_run > 10000):
            raise ValueError("max_delete_per_run must be between 1 and 10000")

        # Get existing config or create default
        cursor = await self.db.execute("SELECT * FROM decay_config WHERE id = 1")
        row = await cursor.fetchone()

        if row:
            # Update existing config
            config = DecayConfig(
                enabled=row["enabled"] == 1,
                threshold=row["threshold"],
                grace_period_days=row["grace_period_days"],
                auto_run_interval_hours=row["auto_run_interval_hours"],
                max_delete_per_run=row["max_delete_per_run"],
                last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
        else:
            # Create default config
            config = DecayConfig()

        # Apply updates
        if enabled is not None:
            config.enabled = enabled
        if threshold is not None:
            config.threshold = threshold
        if grace_period_days is not None:
            config.grace_period_days = grace_period_days
        if auto_run_interval_hours is not None:
            config.auto_run_interval_hours = auto_run_interval_hours
        if max_delete_per_run is not None:
            config.max_delete_per_run = max_delete_per_run

        config.updated_at = datetime.now(timezone.utc)

        # UPSERT to database
        await self.db.execute(
            """
            INSERT INTO decay_config (
                id, enabled, threshold, grace_period_days,
                auto_run_interval_hours, max_delete_per_run,
                last_run_at, updated_at
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                enabled = excluded.enabled,
                threshold = excluded.threshold,
                grace_period_days = excluded.grace_period_days,
                auto_run_interval_hours = excluded.auto_run_interval_hours,
                max_delete_per_run = excluded.max_delete_per_run,
                updated_at = excluded.updated_at
            """,
            (
                1 if config.enabled else 0,
                config.threshold,
                config.grace_period_days,
                config.auto_run_interval_hours,
                config.max_delete_per_run,
                config.last_run_at.isoformat() if config.last_run_at else None,
                config.updated_at.isoformat(),
            ),
        )

        return config

    async def run(
        self,
        threshold: float | None = None,
        grace_period_days: int | None = None,
        dry_run: bool = False,
        max_delete: int | None = None,
        use_transaction: bool = True,
    ) -> DecayRunResult:
        """Run memory decay.

        Args:
            threshold: Override threshold (uses config if None)
            grace_period_days: Override grace period (uses config if None)
            dry_run: If True, only return candidates without deleting
            max_delete: Override max deletions (uses config if None)
            use_transaction: Whether to use transactions for deletions (default True)

        Returns:
            DecayRunResult with deletion details

        Raises:
            ValueError: If override parameters are out of range
        """
        # Validate override parameters
        if threshold is not None and (threshold < 0.0 or threshold > 1.0):
            raise ValueError("threshold must be between 0.0 and 1.0")
        if grace_period_days is not None and grace_period_days < 1:
            raise ValueError("grace_period_days must be >= 1")
        if max_delete is not None and (max_delete < 1 or max_delete > 10000):
            raise ValueError("max_delete must be between 1 and 10000")

        # Get config
        cursor = await self.db.execute("SELECT * FROM decay_config WHERE id = 1")
        row = await cursor.fetchone()

        if row:
            config = DecayConfig(
                enabled=row["enabled"] == 1,
                threshold=row["threshold"],
                grace_period_days=row["grace_period_days"],
                auto_run_interval_hours=row["auto_run_interval_hours"],
                max_delete_per_run=row["max_delete_per_run"],
                last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
        else:
            config = DecayConfig()

        # Apply overrides
        final_threshold = threshold if threshold is not None else config.threshold
        final_grace_period = grace_period_days if grace_period_days is not None else config.grace_period_days
        final_max_delete = max_delete if max_delete is not None else config.max_delete_per_run

        # Calculate grace period cutoff
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=final_grace_period)

        # Query candidate memories
        cursor = await self.db.execute(
            """
            SELECT id FROM memories
            WHERE importance_score <= ?
              AND created_at < ?
              AND expires_at IS NULL
            ORDER BY importance_score ASC
            LIMIT ?
            """,
            (final_threshold, cutoff_date.isoformat(), final_max_delete),
        )
        rows = await cursor.fetchall()
        candidate_ids = [row["id"] for row in rows]

        # If dry_run, return candidates without deleting
        if dry_run:
            result = DecayRunResult(
                deleted_count=len(candidate_ids),
                deleted_ids=candidate_ids,
                threshold=final_threshold,
                grace_period_days=final_grace_period,
                dry_run=True,
            )
            # Log dry run
            log = DecayLog(
                run_at=datetime.now(timezone.utc),
                deleted_count=len(candidate_ids),
                deleted_ids=candidate_ids,
                threshold=final_threshold,
                dry_run=True,
            )
            await self._save_log(log)
            return result

        # Delete memories with error handling
        # Note: repository.delete() handles its own transaction per deletion
        deleted_ids = []
        failed_ids = []
        errors = []

        for memory_id in candidate_ids:
            try:
                # Use repository delete which handles CASCADE (embeddings, FTS, access_log)
                # Each deletion is in its own transaction to prevent rollback of all deletions on single failure
                deleted = await self.repository.delete(memory_id, use_transaction=use_transaction)
                if deleted:
                    deleted_ids.append(memory_id)
                else:
                    failed_ids.append(memory_id)
            except Exception as e:
                failed_ids.append(memory_id)
                errors.append({"id": memory_id, "error": str(e)})
                # Continue with other deletions instead of rolling back all

        # Log execution
        log = DecayLog(
            run_at=datetime.now(timezone.utc),
            deleted_count=len(deleted_ids),
            deleted_ids=deleted_ids,
            threshold=final_threshold,
            dry_run=False,
        )
        await self._save_log(log)

        # Update last_run_at in config (create if not exists)
        await self.db.execute(
            """
            INSERT INTO decay_config (
                id, enabled, threshold, grace_period_days,
                auto_run_interval_hours, max_delete_per_run,
                last_run_at, updated_at
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                last_run_at = excluded.last_run_at
            """,
            (
                1 if config.enabled else 0,
                config.threshold,
                config.grace_period_days,
                config.auto_run_interval_hours,
                config.max_delete_per_run,
                log.run_at.isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        return DecayRunResult(
            deleted_count=len(deleted_ids),
            deleted_ids=deleted_ids,
            threshold=final_threshold,
            grace_period_days=final_grace_period,
            dry_run=False,
            failed_count=len(failed_ids),
            failed_ids=failed_ids,
            errors=errors if errors else None,
        )

    async def status(self) -> dict[str, Any]:
        """Get decay status and statistics.

        Returns:
            {
                "config": DecayConfig,
                "statistics": {
                    "total_memories": int,
                    "decay_candidates": int,
                    "last_run": DecayLog | None,
                    "total_deleted": int
                }
            }
        """
        # Get config
        cursor = await self.db.execute("SELECT * FROM decay_config WHERE id = 1")
        row = await cursor.fetchone()

        if row:
            config = DecayConfig(
                enabled=row["enabled"] == 1,
                threshold=row["threshold"],
                grace_period_days=row["grace_period_days"],
                auto_run_interval_hours=row["auto_run_interval_hours"],
                max_delete_per_run=row["max_delete_per_run"],
                last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
        else:
            config = DecayConfig()

        # Get total memories count
        cursor = await self.db.execute("SELECT COUNT(*) as count FROM memories")
        row = await cursor.fetchone()
        total_memories = row["count"] if row else 0

        # Get current decay candidates count
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=config.grace_period_days)
        cursor = await self.db.execute(
            """
            SELECT COUNT(*) as count FROM memories
            WHERE importance_score <= ?
              AND created_at < ?
              AND expires_at IS NULL
            """,
            (config.threshold, cutoff_date.isoformat()),
        )
        row = await cursor.fetchone()
        decay_candidates = row["count"] if row else 0

        # Get last run log
        cursor = await self.db.execute(
            "SELECT * FROM decay_log ORDER BY run_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        last_run = None
        if row:
            last_run = {
                "run_at": row["run_at"],
                "deleted_count": row["deleted_count"],
                "dry_run": row["dry_run"] == 1,
            }

        # Get total deleted count
        cursor = await self.db.execute(
            "SELECT SUM(deleted_count) as total FROM decay_log WHERE dry_run = 0"
        )
        row = await cursor.fetchone()
        total_deleted = row["total"] if row and row["total"] else 0

        return {
            "config": {
                "enabled": config.enabled,
                "threshold": config.threshold,
                "grace_period_days": config.grace_period_days,
                "auto_run_interval_hours": config.auto_run_interval_hours,
                "max_delete_per_run": config.max_delete_per_run,
                "last_run_at": config.last_run_at.isoformat() if config.last_run_at else None,
                "updated_at": config.updated_at.isoformat(),
            },
            "statistics": {
                "total_memories": total_memories,
                "decay_candidates": decay_candidates,
                "last_run": last_run,
                "total_deleted": total_deleted,
            },
        }

    async def _save_log(self, log: DecayLog) -> None:
        """Save decay log to database.

        Args:
            log: DecayLog to save
        """
        await self.db.execute(
            """
            INSERT INTO decay_log (
                id, run_at, deleted_count, deleted_ids, threshold, dry_run
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                log.id,
                log.run_at.isoformat(),
                log.deleted_count,
                json.dumps(log.deleted_ids),
                log.threshold,
                1 if log.dry_run else 0,
            ),
        )
