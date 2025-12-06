"""Validation utilities for input sanitization and security.

This module provides reusable validators for common input types
to ensure consistency and security across the codebase.
"""

import uuid
from typing import TYPE_CHECKING

from llm_memory.models.memory import MemoryTier

if TYPE_CHECKING:
    from llm_memory.config.settings import Settings


class ValidationError(ValueError):
    """Raised when input validation fails."""


def validate_uuid(id_str: str, field_name: str = "id") -> str:
    """Validate and return a UUID string.

    Args:
        id_str: The string to validate as UUID
        field_name: Name of the field for error messages

    Returns:
        The validated UUID string

    Raises:
        ValidationError: If the string is not a valid UUID
    """
    if not id_str or not isinstance(id_str, str):
        raise ValidationError(f"{field_name} must be a non-empty string")

    try:
        uuid.UUID(id_str)
        return id_str
    except ValueError as e:
        raise ValidationError(f"Invalid UUID format for {field_name}: {id_str}") from e


def validate_content(
    content: str,
    settings: "Settings | None" = None,
    max_length: int | None = None,
) -> str:
    """Validate content is non-empty and within size limits.

    Args:
        content: The content string to validate
        settings: Optional settings object for max length
        max_length: Optional explicit max length (overrides settings)

    Returns:
        The validated content string (stripped)

    Raises:
        ValidationError: If content is empty or exceeds max length
    """
    if not content or not isinstance(content, str):
        raise ValidationError("Content must be a non-empty string")

    content = content.strip()
    if not content:
        raise ValidationError("Content cannot be empty or whitespace only")

    # Determine max length
    limit = max_length
    if limit is None and settings is not None:
        limit = settings.max_content_length

    if limit is not None and len(content) > limit:
        raise ValidationError(
            f"Content exceeds maximum length of {limit:,} characters "
            f"(got {len(content):,})"
        )

    return content


def validate_memory_tier(tier: str) -> MemoryTier:
    """Validate and convert a string to MemoryTier enum.

    Args:
        tier: The tier string to validate

    Returns:
        The corresponding MemoryTier enum value

    Raises:
        ValidationError: If the tier is not valid
    """
    try:
        return MemoryTier(tier)
    except ValueError as e:
        valid_tiers = [t.value for t in MemoryTier]
        raise ValidationError(
            f"Invalid memory_tier: '{tier}'. "
            f"Valid tiers are: {', '.join(valid_tiers)}"
        ) from e


def validate_tags(tags: list[str] | None) -> list[str]:
    """Validate and normalize a list of tags.

    Args:
        tags: Optional list of tag strings

    Returns:
        Normalized list of tags (stripped, non-empty, unique)

    Raises:
        ValidationError: If tags contain invalid values
    """
    if tags is None:
        return []

    if not isinstance(tags, list):
        raise ValidationError("Tags must be a list of strings")

    normalized: list[str] = []
    for tag in tags:
        if not isinstance(tag, str):
            raise ValidationError(f"Tag must be a string, got {type(tag).__name__}")
        tag = tag.strip()
        if tag and tag not in normalized:
            normalized.append(tag)

    return normalized


def validate_positive_int(
    value: int,
    field_name: str,
    min_value: int = 1,
    max_value: int | None = None,
) -> int:
    """Validate a positive integer within bounds.

    Args:
        value: The integer value to validate
        field_name: Name of the field for error messages
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive), None for no limit

    Returns:
        The validated integer

    Raises:
        ValidationError: If value is out of bounds
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer")

    if value < min_value:
        raise ValidationError(f"{field_name} must be at least {min_value}")

    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} must be at most {max_value}")

    return value


def validate_batch_ids(ids: list[str], field_name: str = "ids") -> list[str]:
    """Validate a list of IDs for batch operations.

    Args:
        ids: List of ID strings to validate
        field_name: Name of the field for error messages

    Returns:
        List of validated UUID strings

    Raises:
        ValidationError: If any ID is invalid or list is empty
    """
    if not ids or not isinstance(ids, list):
        raise ValidationError(f"{field_name} must be a non-empty list")

    return [validate_uuid(id_str, f"{field_name}[{i}]") for i, id_str in enumerate(ids)]
