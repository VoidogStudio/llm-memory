"""Memory versioning MCP tools."""

from typing import Any

from src.exceptions import NotFoundError, ValidationError
from src.services.versioning_service import VersioningService
from src.tools import create_error_response


async def memory_version_history(
    service: VersioningService,
    memory_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Get version history for a memory.

    Args:
        service: Versioning service instance
        memory_id: Memory ID
        limit: Maximum versions to return (1-50, default 10)

    Returns:
        Version history information
    """
    try:
        history = await service.get_history(memory_id, limit)

        return {
            "memory_id": history.memory_id,
            "current_version": history.current_version,
            "total_versions": history.total_versions,
            "versions": [
                {
                    "version": v.version,
                    "content_preview": v.content[:200] + ("..." if len(v.content) > 200 else ""),
                    "created_at": v.created_at.isoformat(),
                    "change_reason": v.change_reason,
                }
                for v in history.versions
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


async def memory_version_get(
    service: VersioningService,
    memory_id: str,
    version: int,
) -> dict[str, Any]:
    """Get a specific version of a memory.

    Args:
        service: Versioning service instance
        memory_id: Memory ID
        version: Version number to retrieve

    Returns:
        Version information
    """
    try:
        version_obj = await service.get_version(memory_id, version)

        return {
            "memory_id": version_obj.memory_id,
            "version": version_obj.version,
            "content": version_obj.content,
            "content_type": version_obj.content_type,
            "tags": version_obj.tags,
            "metadata": version_obj.metadata,
            "created_at": version_obj.created_at.isoformat(),
            "change_reason": version_obj.change_reason,
        }
    except NotFoundError as e:
        return create_error_response(
            message=str(e),
            error_type="NotFoundError",
        )


async def memory_version_rollback(
    service: VersioningService,
    memory_id: str,
    target_version: int,
    reason: str | None = None,
) -> dict[str, Any]:
    """Rollback a memory to a specific version.

    Args:
        service: Versioning service instance
        memory_id: Memory ID
        target_version: Version number to rollback to
        reason: Optional reason for rollback

    Returns:
        Rollback result
    """
    try:
        # Get current version before rollback
        history = await service.get_history(memory_id, limit=1)
        previous_version = history.current_version

        # Perform rollback
        memory = await service.rollback(memory_id, target_version, reason)

        return {
            "id": memory.id,
            "previous_version": previous_version,
            "new_version": memory.version,
            "rolled_back_to": target_version,
            "content": memory.content,
            "reason": reason,
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


async def memory_version_diff(
    service: VersioningService,
    memory_id: str,
    old_version: int,
    new_version: int,
) -> dict[str, Any]:
    """Show differences between two versions.

    Args:
        service: Versioning service instance
        memory_id: Memory ID
        old_version: Older version number
        new_version: Newer version number

    Returns:
        Version diff information
    """
    try:
        diff = await service.diff_versions(memory_id, old_version, new_version)

        return {
            "memory_id": diff.memory_id,
            "old_version": diff.old_version,
            "new_version": diff.new_version,
            "content_changed": diff.content_changed,
            "content_diff": diff.content_diff,
            "tags_added": diff.tags_added,
            "tags_removed": diff.tags_removed,
            "metadata_changed": diff.metadata_changed,
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
