"""Custom exceptions for llm-memory."""


class NotFoundError(Exception):
    """Raised when a requested resource is not found."""

    pass


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


class ConflictError(Exception):
    """Raised when a resource conflict occurs."""

    pass
