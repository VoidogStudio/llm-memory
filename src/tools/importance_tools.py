"""Importance scoring MCP tools."""

from typing import Any

from src.services.importance_service import ImportanceService
from src.tools import create_error_response


async def memory_get_score(
    service: ImportanceService,
    id: str,
) -> dict[str, Any]:
    """Get importance score for a memory.

    Args:
        service: Importance service instance
        id: Memory ID

    Returns:
        Score info with access statistics
    """
    try:
        result = await service.get_score(memory_id=id)
        return result
    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="NotFoundError",
            details={"memory_id": id},
        )
    except Exception as e:
        return create_error_response(
            message=f"Failed to get importance score: {str(e)}",
            error_type="ImportanceError",
        )


async def memory_set_score(
    service: ImportanceService,
    id: str,
    score: float,
    reason: str | None = None,
) -> dict[str, Any]:
    """Manually set importance score for a memory.

    Args:
        service: Importance service instance
        id: Memory ID
        score: New score (0.0-1.0)
        reason: Optional reason for manual override (for audit trail)

    Returns:
        Previous and new score info
    """
    try:
        result = await service.set_score(memory_id=id, score=score, reason=reason)
        return result
    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
            details={"memory_id": id, "score": score},
        )
    except Exception as e:
        return create_error_response(
            message=f"Failed to set importance score: {str(e)}",
            error_type="ImportanceError",
        )
