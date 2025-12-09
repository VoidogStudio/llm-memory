"""Memory dependency tracking MCP tools."""

from typing import Any

from src.exceptions import NotFoundError, ValidationError
from src.services.dependency_service import DependencyService
from src.tools import create_error_response


async def memory_dependency_analyze(
    service: DependencyService,
    memory_id: str,
    cascade_type: str = "update",
    max_depth: int = 5,
) -> dict[str, Any]:
    """Analyze dependency impact for a memory.

    Args:
        service: Dependency service instance
        memory_id: Source memory ID
        cascade_type: Type of cascade to analyze ("update" | "delete")
        max_depth: Maximum traversal depth (1-10, default 5)

    Returns:
        Dependency analysis result
    """
    try:
        analysis = await service.analyze_impact(memory_id, cascade_type, max_depth)

        return {
            "source_memory_id": analysis.source_memory_id,
            "total_affected": analysis.total_affected,
            "max_depth_reached": analysis.max_depth_reached,
            "has_cycles": analysis.has_cycles,
            "cycle_paths": analysis.cycle_paths if analysis.has_cycles else None,
            "affected_memories": [
                {
                    "memory_id": a.memory_id,
                    "depth": a.depth,
                    "link_type": a.link_type.value,
                    "cascade_type": a.cascade_type,
                    "strength": a.strength,
                }
                for a in analysis.affected_memories
            ],
        }
    except NotFoundError as e:
        return create_error_response(
            message=str(e),
            error_type="NotFoundError",
        )
    except ValidationError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )


async def memory_dependency_propagate(
    service: DependencyService,
    memory_id: str,
    notification_type: str = "update",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Propagate change notifications to dependent memories.

    Args:
        service: Dependency service instance
        memory_id: Source memory ID
        notification_type: Type of notification ("update" | "delete" | "stale")
        metadata: Additional context about the change

    Returns:
        Propagation result
    """
    try:
        result = await service.propagate_update(
            memory_id, notification_type, metadata
        )

        return {
            "source_memory_id": memory_id,
            "notification_type": notification_type,
            "affected_count": result["affected_count"],
            "notifications_created": result["notifications_created"],
        }
    except NotFoundError as e:
        return create_error_response(
            message=str(e),
            error_type="NotFoundError",
        )
    except ValidationError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )
