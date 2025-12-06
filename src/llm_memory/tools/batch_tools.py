"""Batch operation MCP tools."""

import logging
from typing import Any

from llm_memory.exceptions import NotFoundError
from llm_memory.services.memory_service import MemoryService
from llm_memory.tools import create_error_response

logger = logging.getLogger(__name__)


async def memory_batch_store(
    service: MemoryService,
    items: list[dict[str, Any]],
    on_error: str = "rollback",
) -> dict[str, Any]:
    """Store multiple memories in a single batch operation.

    Args:
        service: Memory service instance
        items: List of memory items (each has memory_store params)
        on_error: Error handling strategy (rollback/continue/stop)

    Returns:
        Batch operation result with success/error counts

    Error types:
        - ValidationError: Invalid input parameters
        - BatchOperationError: Unexpected error during batch processing
    """
    try:
        result = await service.batch_store(items=items, on_error=on_error)
        return result
    except ValueError as e:
        logger.warning("Batch store validation failed: %s", e)
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
            details={"items_count": len(items) if items else 0},
        )
    except (OSError, RuntimeError) as e:
        # Database or system errors
        logger.error("Batch store system error: %s", e, exc_info=True)
        return create_error_response(
            message=f"Batch store failed due to system error: {e}",
            error_type="BatchOperationError",
            details={"items_count": len(items) if items else 0},
        )
    except Exception as e:
        # Log unexpected errors for debugging
        logger.exception("Unexpected error in batch_store: %s", e)
        return create_error_response(
            message=f"Batch store failed: {e}",
            error_type="BatchOperationError",
        )


async def memory_batch_update(
    service: MemoryService,
    updates: list[dict[str, Any]],
    on_error: str = "rollback",
) -> dict[str, Any]:
    """Update multiple memories in a single batch operation.

    Args:
        service: Memory service instance
        updates: List of updates (each has {id: str, ...fields})
        on_error: Error handling strategy (rollback/continue/stop)

    Returns:
        Batch operation result with success/error counts

    Error types:
        - ValidationError: Invalid input parameters
        - NotFoundError: One or more memories not found
        - BatchOperationError: Unexpected error during batch processing
    """
    try:
        result = await service.batch_update(updates=updates, on_error=on_error)
        return result
    except ValueError as e:
        logger.warning("Batch update validation failed: %s", e)
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
            details={"updates_count": len(updates) if updates else 0},
        )
    except NotFoundError as e:
        logger.warning("Batch update not found: %s", e)
        return create_error_response(
            message=str(e),
            error_type="NotFoundError",
            details={"updates_count": len(updates) if updates else 0},
        )
    except (OSError, RuntimeError) as e:
        # Database or system errors
        logger.error("Batch update system error: %s", e, exc_info=True)
        return create_error_response(
            message=f"Batch update failed due to system error: {e}",
            error_type="BatchOperationError",
            details={"updates_count": len(updates) if updates else 0},
        )
    except Exception as e:
        # Log unexpected errors for debugging
        logger.exception("Unexpected error in batch_update: %s", e)
        return create_error_response(
            message=f"Batch update failed: {e}",
            error_type="BatchOperationError",
        )
