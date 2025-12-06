"""Memory decay MCP tools."""

from typing import Any

from src.services.decay_service import DecayService
from src.tools import create_error_response


async def memory_decay_configure(
    service: DecayService,
    enabled: bool | None = None,
    threshold: float | None = None,
    grace_period_days: int | None = None,
    auto_run_interval_hours: int | None = None,
    max_delete_per_run: int | None = None,
) -> dict[str, Any]:
    """Configure memory decay settings.

    Args:
        service: Decay service instance
        enabled: Enable/disable decay
        threshold: Importance score threshold (0.0-1.0)
        grace_period_days: Days before deletion eligible (min: 1)
        auto_run_interval_hours: Auto-run interval (reserved for future)
        max_delete_per_run: Maximum deletions per run (1-10000)

    Returns:
        Updated configuration
    """
    try:
        config = await service.configure(
            enabled=enabled,
            threshold=threshold,
            grace_period_days=grace_period_days,
            auto_run_interval_hours=auto_run_interval_hours,
            max_delete_per_run=max_delete_per_run,
        )

        return {
            "enabled": config.enabled,
            "threshold": config.threshold,
            "grace_period_days": config.grace_period_days,
            "auto_run_interval_hours": config.auto_run_interval_hours,
            "max_delete_per_run": config.max_delete_per_run,
            "last_run_at": config.last_run_at.isoformat() if config.last_run_at else None,
            "updated_at": config.updated_at.isoformat(),
        }
    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )


async def memory_decay_run(
    service: DecayService,
    threshold: float | None = None,
    grace_period_days: int | None = None,
    dry_run: bool = False,
    max_delete: int | None = None,
) -> dict[str, Any]:
    """Run memory decay to delete low-importance memories.

    Args:
        service: Decay service instance
        threshold: Override importance threshold
        grace_period_days: Override grace period
        dry_run: If True, only preview without deleting
        max_delete: Override maximum deletions

    Returns:
        Deletion results with affected IDs
    """
    result = await service.run(
        threshold=threshold,
        grace_period_days=grace_period_days,
        dry_run=dry_run,
        max_delete=max_delete,
    )

    return {
        "deleted_count": result.deleted_count,
        "deleted_ids": result.deleted_ids,
        "threshold": result.threshold,
        "grace_period_days": result.grace_period_days,
        "dry_run": result.dry_run,
    }


async def memory_decay_status(
    service: DecayService,
) -> dict[str, Any]:
    """Get current decay status and statistics.

    Args:
        service: Decay service instance

    Returns:
        Configuration and statistics
    """
    return await service.status()
