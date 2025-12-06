"""Database export/import MCP tools."""

from datetime import datetime
from typing import Any

from src.services.export_import_service import ExportImportService
from src.tools import create_error_response


async def database_export(
    service: ExportImportService,
    output_path: str | None = None,
    include_embeddings: bool = True,
    memory_tier: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    format: str = "jsonl",
) -> dict[str, Any]:
    """Export database to file.

    Args:
        service: Export/Import service instance
        output_path: Output file path (required)
        include_embeddings: Include embedding vectors
        memory_tier: Filter by memory tier
        created_after: Filter by creation date (ISO format)
        created_before: Filter by creation date (ISO format)
        format: Output format (jsonl)

    Returns:
        Export results and statistics
    """
    # Validate output_path
    if not output_path:
        return create_error_response(
            message="output_path is required",
            error_type="ValidationError",
        )

    # Validate format
    if format != "jsonl":
        return create_error_response(
            message="format must be 'jsonl'",
            error_type="ValidationError",
        )

    # Parse datetime filters if provided
    created_after_dt = None
    created_before_dt = None

    try:
        if created_after:
            created_after_dt = datetime.fromisoformat(created_after)
        if created_before:
            created_before_dt = datetime.fromisoformat(created_before)
    except ValueError as e:
        return create_error_response(
            message=f"Invalid date format: {e}",
            error_type="ValidationError",
        )

    try:
        result = await service.export_database(
            output_path=output_path,
            include_embeddings=include_embeddings,
            memory_tier=memory_tier,
            created_after=created_after_dt,
            created_before=created_before_dt,
            format=format,
        )

        return {
            "exported_at": result.exported_at.isoformat(),
            "schema_version": result.schema_version,
            "counts": result.counts,
            "file_path": result.file_path,
            "file_size_bytes": result.file_size_bytes,
        }
    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )
    except OSError as e:
        return create_error_response(
            message=str(e),
            error_type="IOError",
        )


async def database_import(
    service: ExportImportService,
    input_path: str,
    mode: str = "merge",
    on_conflict: str = "skip",
    regenerate_embeddings: bool = False,
) -> dict[str, Any]:
    """Import database from file.

    Args:
        service: Export/Import service instance
        input_path: Input file path
        mode: Import mode (replace/merge)
        on_conflict: Conflict handling (skip/update/error)
        regenerate_embeddings: Regenerate embeddings from content

    Returns:
        Import results and statistics
    """
    # Validate input_path
    if not input_path:
        return create_error_response(
            message="input_path is required",
            error_type="ValidationError",
        )

    # Validate mode
    if mode not in ["replace", "merge"]:
        return create_error_response(
            message="mode must be 'replace' or 'merge'",
            error_type="ValidationError",
        )

    # Validate on_conflict
    if on_conflict not in ["skip", "update", "error"]:
        return create_error_response(
            message="on_conflict must be 'skip', 'update', or 'error'",
            error_type="ValidationError",
        )

    try:
        result = await service.import_database(
            input_path=input_path,
            mode=mode,
            on_conflict=on_conflict,
            regenerate_embeddings=regenerate_embeddings,
            use_transaction=False,
        )

        return {
            "imported_at": result.imported_at.isoformat(),
            "schema_version": result.schema_version,
            "mode": result.mode,
            "counts": result.counts,
            "skipped_count": result.skipped_count,
            "error_count": result.error_count,
            "errors": result.errors if result.errors else [],
        }
    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )
    except OSError as e:
        return create_error_response(
            message=str(e),
            error_type="IOError",
        )
