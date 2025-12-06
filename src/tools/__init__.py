"""MCP tool definitions."""

from datetime import datetime, timezone
from typing import Any

__all__ = ["create_error_response"]


def create_error_response(
    message: str,
    error_type: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create standardized error response for MCP tools.

    Args:
        message: User-friendly error message
        error_type: Error type name (e.g., ValidationError, NotFoundError)
        details: Optional additional details

    Returns:
        Structured error response dictionary
    """
    response = {
        "error": True,
        "message": message,
        "error_type": error_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if details:
        response["details"] = details
    return response
