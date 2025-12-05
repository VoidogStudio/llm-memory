"""Batch operation MCP tools."""

from typing import Any

from llm_memory.services.memory_service import MemoryService
from llm_memory.tools import create_error_response


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
    """
    try:
        result = await service.batch_store(items=items, on_error=on_error)
        return result
    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
            details={"items_count": len(items)},
        )
    except Exception as e:
        return create_error_response(
            message=f"Batch store failed: {str(e)}",
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
    """
    try:
        result = await service.batch_update(updates=updates, on_error=on_error)
        return result
    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
            details={"updates_count": len(updates)},
        )
    except Exception as e:
        return create_error_response(
            message=f"Batch update failed: {str(e)}",
            error_type="BatchOperationError",
        )
