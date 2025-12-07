"""Auto Knowledge Acquisition MCP tools."""

from typing import Any

from src.services.knowledge_sync_service import KnowledgeSyncService
from src.services.project_scan_service import ProjectScanService
from src.services.session_learning_service import SessionLearningService
from src.services.staleness_service import StalenessService
from src.tools import create_error_response


async def project_scan(
    service: ProjectScanService,
    project_path: str,
    namespace: str | None = None,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    max_file_size_kb: int = 100,
    force_rescan: bool = False,
) -> dict[str, Any]:
    """Scan a project directory and extract knowledge.

    Scans source files, configuration, and documentation from a project
    directory and stores them as structured knowledge in the memory system.

    Args:
        service: Project scan service instance
        project_path: Path to project directory to scan
        namespace: Target namespace (default: project name)
        include_patterns: Additional file patterns to include (gitignore format)
        exclude_patterns: Additional file patterns to exclude (gitignore format)
        max_file_size_kb: Maximum file size to process in KB
        force_rescan: Force rescan even if already scanned

    Returns:
        Scan result with statistics and detected configuration
    """
    # Validate project_path
    if not project_path or not project_path.strip():
        return create_error_response(
            message="project_path cannot be empty",
            error_type="ValidationError",
        )

    # Validate max_file_size_kb
    if max_file_size_kb < 1 or max_file_size_kb > 10000:
        return create_error_response(
            message="max_file_size_kb must be between 1 and 10000",
            error_type="ValidationError",
        )

    try:
        result = await service.scan(
            project_path=project_path,
            namespace=namespace,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_file_size_kb=max_file_size_kb,
            force_rescan=force_rescan,
        )

        return result.model_dump()

    except FileNotFoundError as e:
        return create_error_response(
            message=f"Project path not found: {str(e)}",
            error_type="FileNotFoundError",
        )
    except ValueError as e:
        return create_error_response(
            message=f"Invalid project path: {str(e)}",
            error_type="ValidationError",
        )
    except Exception as e:
        return create_error_response(
            message=f"Error scanning project: {str(e)}",
            error_type="ScanError",
        )


async def knowledge_sync(
    service: KnowledgeSyncService,
    source_type: str,
    source_path: str,
    namespace: str | None = None,
    category: str = "external_docs",
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    update_mode: str = "smart",
) -> dict[str, Any]:
    """Sync knowledge from external documentation sources.

    Imports and maintains external documentation (local files, directories,
    URLs, or GitHub repos) in the knowledge base with change detection.

    Args:
        service: Knowledge sync service instance
        source_type: Source type (local_file/local_directory/url/github_repo)
        source_path: Path or URL to the source
        namespace: Target namespace
        category: Document category for organization
        include_patterns: File patterns to include (for directories)
        exclude_patterns: File patterns to exclude (for directories)
        chunk_size: Characters per chunk for processing
        chunk_overlap: Overlap between chunks
        update_mode: Update mode (smart=only changed, full=all)

    Returns:
        Sync result with statistics and processed documents
    """
    # Validate source_type
    valid_types = ["local_file", "local_directory", "url", "github_repo"]
    if source_type not in valid_types:
        return create_error_response(
            message=f"Invalid source_type: {source_type}. Must be one of: {', '.join(valid_types)}",
            error_type="ValidationError",
        )

    # Validate source_path
    if not source_path or not source_path.strip():
        return create_error_response(
            message="source_path cannot be empty",
            error_type="ValidationError",
        )

    # Validate chunk_size
    if chunk_size < 50 or chunk_size > 5000:
        return create_error_response(
            message="chunk_size must be between 50 and 5000",
            error_type="ValidationError",
        )

    # Validate chunk_overlap
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        return create_error_response(
            message="chunk_overlap must be >= 0 and < chunk_size",
            error_type="ValidationError",
        )

    # Validate update_mode
    if update_mode not in ["smart", "full"]:
        return create_error_response(
            message="update_mode must be 'smart' or 'full'",
            error_type="ValidationError",
        )

    try:
        result = await service.sync(
            source_type=source_type,
            source_path=source_path,
            namespace=namespace,
            category=category,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            update_mode=update_mode,
        )

        return result.model_dump()

    except FileNotFoundError as e:
        return create_error_response(
            message=f"Source not found: {str(e)}",
            error_type="FileNotFoundError",
        )
    except NotImplementedError as e:
        return create_error_response(
            message=f"Feature not yet implemented: {str(e)}",
            error_type="NotImplementedError",
        )
    except Exception as e:
        return create_error_response(
            message=f"Error syncing knowledge: {str(e)}",
            error_type="SyncError",
        )


async def session_learn(
    service: SessionLearningService,
    content: str,
    category: str,
    context: str | None = None,
    confidence: float = 0.8,
    namespace: str | None = None,
    related_files: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Record learning from the current session.

    Captures important insights, patterns, or decisions from the current
    session with automatic deduplication against similar learnings.

    Args:
        service: Session learning service instance
        content: Learning content to record
        category: Learning category (error_resolution/design_decision/best_practice/user_preference)
        context: Additional context about the learning
        confidence: Confidence score (0.0-1.0)
        namespace: Target namespace
        related_files: List of related file paths
        tags: Additional tags for categorization

    Returns:
        Learning result with similar learnings and action taken
    """
    # Validate content
    if not content or not content.strip():
        return create_error_response(
            message="content cannot be empty",
            error_type="ValidationError",
        )

    # Validate category
    valid_categories = ["error_resolution", "design_decision", "best_practice", "user_preference"]
    if category not in valid_categories:
        return create_error_response(
            message=f"Invalid category: {category}. Must be one of: {', '.join(valid_categories)}",
            error_type="ValidationError",
        )

    # Validate confidence
    if confidence < 0.0 or confidence > 1.0:
        return create_error_response(
            message="confidence must be between 0.0 and 1.0",
            error_type="ValidationError",
        )

    try:
        result = await service.learn(
            content=content,
            category=category,
            context=context,
            confidence=confidence,
            namespace=namespace,
            related_files=related_files,
            tags=tags,
        )

        return result.model_dump()

    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )
    except Exception as e:
        return create_error_response(
            message=f"Error recording learning: {str(e)}",
            error_type="LearningError",
        )


async def knowledge_check_staleness(
    service: StalenessService,
    namespace: str | None = None,
    stale_days: int = 30,
    check_source_changes: bool = True,
    categories: list[str] | None = None,
    include_auto_scan: bool = True,
    include_sync: bool = True,
    include_learning: bool = True,
    limit: int = 100,
) -> dict[str, Any]:
    """Check for stale or outdated knowledge.

    Identifies knowledge that may be outdated based on source file changes
    and access patterns. Provides recommendations for refresh actions.

    Args:
        service: Staleness service instance
        namespace: Target namespace (None for all)
        stale_days: Days threshold for staleness detection
        check_source_changes: Whether to check if source files changed
        categories: Specific categories to check (None for all)
        include_auto_scan: Include project scan results
        include_sync: Include synced knowledge
        include_learning: Include session learnings
        limit: Maximum number of results to return

    Returns:
        Staleness result with statistics, stale items, and recommendations
    """
    # Validate stale_days
    if stale_days < 1:
        return create_error_response(
            message="stale_days must be >= 1",
            error_type="ValidationError",
        )

    # Validate limit
    if limit < 1 or limit > 1000:
        return create_error_response(
            message="limit must be between 1 and 1000",
            error_type="ValidationError",
        )

    try:
        result = await service.check(
            namespace=namespace,
            stale_days=stale_days,
            check_source_changes=check_source_changes,
            categories=categories,
            include_auto_scan=include_auto_scan,
            include_sync=include_sync,
            include_learning=include_learning,
            limit=limit,
        )

        return result.model_dump()

    except Exception as e:
        return create_error_response(
            message=f"Error checking staleness: {str(e)}",
            error_type="StalenessCheckError",
        )


async def knowledge_refresh_stale(
    service: StalenessService,
    memory_ids: list[str] | None = None,
    namespace: str | None = None,
    action: str = "refresh",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Refresh or clean up stale knowledge.

    Takes action on stale knowledge items: refresh from source, archive
    (lower importance), or delete. Supports dry-run mode for preview.

    Args:
        service: Staleness service instance
        memory_ids: Specific memory IDs to refresh (None for all stale)
        namespace: Target namespace
        action: Action to take (refresh/archive/delete)
        dry_run: Preview mode - show what would happen without changes

    Returns:
        Refresh result with affected items and action taken
    """
    # Validate action
    valid_actions = ["refresh", "archive", "delete"]
    if action not in valid_actions:
        return create_error_response(
            message=f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}",
            error_type="ValidationError",
        )

    try:
        result = await service.refresh(
            memory_ids=memory_ids,
            namespace=namespace,
            action=action,
            dry_run=dry_run,
        )

        return result.model_dump()

    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )
    except Exception as e:
        return create_error_response(
            message=f"Error refreshing knowledge: {str(e)}",
            error_type="RefreshError",
        )
