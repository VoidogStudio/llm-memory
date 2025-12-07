"""Staleness detection service for Auto Knowledge Acquisition."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from src.db.repositories.memory_repository import MemoryRepository
from src.models.acquisition import (
    RefreshResult,
    SourceType,
    StaleMemoryInfo,
    StalenessAction,
    StalenessRecommendation,
    StalenessResult,
    StalenessStatistics,
)
from src.models.memory import Memory
from src.services.file_hash_service import FileHashService

logger = logging.getLogger(__name__)


class StalenessService:
    """Service for staleness detection and refresh."""

    def __init__(
        self,
        memory_repository: MemoryRepository,
        file_hash_service: FileHashService,
    ) -> None:
        """Initialize staleness service.

        Args:
            memory_repository: Memory repository
            file_hash_service: File hash service
        """
        self.memory_repository = memory_repository
        self.file_hash_service = file_hash_service

    async def check(
        self,
        namespace: str | None = None,
        stale_days: int = 30,
        check_source_changes: bool = True,
        categories: list[str] | None = None,
        include_auto_scan: bool = True,
        include_sync: bool = True,
        include_learning: bool = True,
        limit: int = 100,
    ) -> StalenessResult:
        """Check for stale knowledge.

        Args:
            namespace: Target namespace (None for all)
            stale_days: Days threshold for staleness
            check_source_changes: Whether to check source file changes
            categories: Categories to check (None for all)
            include_auto_scan: Include project scan results
            include_sync: Include sync results
            include_learning: Include session learning
            limit: Maximum number of results

        Returns:
            Staleness result
        """
        target_namespace = namespace or "default"

        # Get memories to check
        memories = await self.memory_repository.list_all(
            namespace=target_namespace,
            limit=limit * 2,  # Get more to filter
        )

        # Filter by source type
        filtered_memories = []
        for memory in memories:
            source_type = memory.metadata.get("source_type")

            if source_type == SourceType.PROJECT_SCAN.value and include_auto_scan:
                filtered_memories.append(memory)
            elif source_type == SourceType.KNOWLEDGE_SYNC.value and include_sync:
                filtered_memories.append(memory)
            elif source_type == SourceType.SESSION_LEARNING.value and include_learning:
                filtered_memories.append(memory)

            # Also include if no source_type (legacy memories)
            if not source_type and include_auto_scan:
                filtered_memories.append(memory)

        # Filter by category if specified
        if categories:
            category_filtered = []
            for memory in filtered_memories:
                memory_category = memory.metadata.get("category")
                if memory_category in categories:
                    category_filtered.append(memory)
            filtered_memories = category_filtered

        # Initialize statistics
        statistics = StalenessStatistics(total_checked=len(filtered_memories))
        stale_memories: list[StaleMemoryInfo] = []

        # Check each memory for staleness
        for memory in filtered_memories[:limit]:
            staleness_reasons = []

            # Check source changes
            source_changed = False
            current_hash = None
            stored_hash = None

            if check_source_changes:
                is_changed, curr_hash, stor_hash = await self._check_source_changed(memory)
                source_changed = is_changed
                current_hash = curr_hash
                stored_hash = stor_hash

                if source_changed:
                    staleness_reasons.append("source_file_changed")
                    statistics.source_changed += 1

            # Check last access
            not_accessed, days_since = self._check_not_accessed(memory, stale_days)

            if not_accessed:
                staleness_reasons.append(f"not_accessed_{days_since}_days")
                statistics.not_accessed += 1

            # Apply AND condition (both must be true)
            is_stale = source_changed and not_accessed

            if is_stale:
                staleness_reasons.append("both_conditions_met")
                statistics.both_conditions += 1
                statistics.stale_count += 1

                # Create stale memory info
                content_preview = memory.content[:200]
                if len(memory.content) > 200:
                    content_preview += "..."

                stale_info = StaleMemoryInfo(
                    memory_id=memory.id,
                    content_preview=content_preview,
                    source_type=SourceType(
                        memory.metadata.get("source_type", SourceType.MANUAL.value)
                    ),
                    source_file=memory.metadata.get("source_file"),
                    staleness_reason=staleness_reasons,
                    last_accessed_at=memory.last_accessed_at,
                    days_since_access=days_since,
                    source_hash_current=current_hash,
                    source_hash_stored=stored_hash,
                )

                stale_memories.append(stale_info)

        # Generate recommendations
        recommendations = self._generate_recommendations(stale_memories, statistics)

        logger.info(
            f"Staleness check completed: {statistics.total_checked} checked, "
            f"{statistics.stale_count} stale"
        )

        return StalenessResult(
            namespace=target_namespace,
            statistics=statistics,
            stale_memories=stale_memories,
            recommendations=recommendations,
        )

    async def _check_source_changed(
        self,
        memory: Memory,
    ) -> tuple[bool, str | None, str | None]:
        """Check if source file has changed.

        Args:
            memory: Memory to check

        Returns:
            Tuple of (is_changed, current_hash, stored_hash)
        """
        source_file = memory.metadata.get("source_file")
        stored_hash = memory.metadata.get("file_hash")

        if not source_file or not stored_hash:
            return (False, None, None)

        # Try to find the file
        try:
            # Attempt to resolve path
            file_path = Path(source_file)

            # If not absolute, we can't check
            if not file_path.is_absolute():
                # Try to construct from project metadata
                project_name = memory.metadata.get("project_name")
                if project_name:
                    # This is a heuristic - in production, you'd need a registry
                    logger.debug(f"Cannot resolve relative path: {source_file}")
                return (False, None, stored_hash)

            if not file_path.exists():
                logger.debug(f"Source file not found: {source_file}")
                return (True, None, stored_hash)  # File deleted = changed

            # Calculate current hash
            current_hash = await self.file_hash_service.calculate_file_hash(file_path)

            # Compare
            is_changed = self.file_hash_service.is_changed(current_hash, stored_hash)

            return (is_changed, current_hash, stored_hash)

        except Exception as e:
            logger.warning(f"Error checking source file {source_file}: {e}")
            return (False, None, stored_hash)

    def _check_not_accessed(
        self,
        memory: Memory,
        stale_days: int,
    ) -> tuple[bool, int | None]:
        """Check if memory has not been accessed.

        Args:
            memory: Memory to check
            stale_days: Days threshold

        Returns:
            Tuple of (is_stale, days_since_access)
        """
        if not memory.last_accessed_at:
            # Never accessed, use created_at
            reference_time = memory.created_at
        else:
            reference_time = memory.last_accessed_at

        now = datetime.now(timezone.utc)
        delta = now - reference_time
        days_since = delta.days

        is_stale = days_since >= stale_days

        return (is_stale, days_since)

    def _generate_recommendations(
        self,
        stale_memories: list[StaleMemoryInfo],
        statistics: StalenessStatistics,
    ) -> list[StalenessRecommendation]:
        """Generate recommendations based on staleness results.

        Args:
            stale_memories: List of stale memories
            statistics: Staleness statistics

        Returns:
            List of recommendations
        """
        recommendations = []

        # Count by source type
        project_scan_count = sum(
            1 for m in stale_memories if m.source_type == SourceType.PROJECT_SCAN
        )
        sync_count = sum(
            1 for m in stale_memories if m.source_type == SourceType.KNOWLEDGE_SYNC
        )
        learning_count = sum(
            1 for m in stale_memories if m.source_type == SourceType.SESSION_LEARNING
        )

        # Recommend project rescan
        if project_scan_count > 5:
            recommendations.append(
                StalenessRecommendation(
                    action="rescan",
                    target="project",
                    reason=f"Found {project_scan_count} stale project files. "
                    "Consider rescanning the project.",
                )
            )

        # Recommend sync refresh
        if sync_count > 3:
            recommendations.append(
                StalenessRecommendation(
                    action="rescan",
                    target="sync",
                    reason=f"Found {sync_count} stale synced documents. "
                    "Consider re-syncing external sources.",
                )
            )

        # Recommend learning review
        if learning_count > 10:
            recommendations.append(
                StalenessRecommendation(
                    action="review",
                    target="learning",
                    reason=f"Found {learning_count} stale learnings. "
                    "Consider reviewing or archiving old learnings.",
                )
            )

        # General recommendation if many stale items
        if statistics.stale_count > 20:
            recommendations.append(
                StalenessRecommendation(
                    action="review",
                    target="project",
                    reason=f"Found {statistics.stale_count} total stale items. "
                    "Consider a comprehensive refresh.",
                )
            )

        return recommendations

    async def refresh(
        self,
        memory_ids: list[str] | None = None,
        namespace: str | None = None,
        action: str = "refresh",
        dry_run: bool = True,
    ) -> RefreshResult:
        """Refresh stale knowledge.

        Args:
            memory_ids: Specific memory IDs to refresh (None for all stale)
            namespace: Target namespace
            action: Action to take (refresh/archive/delete)
            dry_run: Preview mode (don't make changes)

        Returns:
            Refresh result
        """
        try:
            staleness_action = StalenessAction(action)
        except ValueError as e:
            raise ValueError(
                f"Invalid action: {action}. "
                f"Must be one of: {', '.join([a.value for a in StalenessAction])}"
            ) from e

        affected_memories: list[dict] = []
        affected_count = 0

        if memory_ids:
            # Refresh specific memories
            for memory_id in memory_ids:
                try:
                    memory = await self.memory_repository.find_by_id(memory_id)
                    if not memory:
                        logger.warning(f"Memory not found: {memory_id}")
                        continue

                    if not dry_run:
                        await self._apply_action(memory, staleness_action)

                    affected_memories.append({
                        "memory_id": memory_id,
                        "source_file": memory.metadata.get("source_file"),
                        "action": action,
                    })
                    affected_count += 1

                except Exception as e:
                    logger.error(f"Error refreshing memory {memory_id}: {e}")
                    affected_memories.append({
                        "memory_id": memory_id,
                        "error": str(e),
                    })

        else:
            # Find and refresh all stale memories
            staleness_result = await self.check(namespace=namespace)

            for stale_info in staleness_result.stale_memories:
                try:
                    memory = await self.memory_repository.find_by_id(stale_info.memory_id)
                    if not memory:
                        continue

                    if not dry_run:
                        await self._apply_action(memory, staleness_action)

                    affected_memories.append({
                        "memory_id": stale_info.memory_id,
                        "source_file": stale_info.source_file,
                        "action": action,
                    })
                    affected_count += 1

                except Exception as e:
                    logger.error(f"Error refreshing memory {stale_info.memory_id}: {e}")

        return RefreshResult(
            action=staleness_action,
            dry_run=dry_run,
            affected_count=affected_count,
            affected_memories=affected_memories,
        )

    async def _apply_action(self, memory: Memory, action: StalenessAction) -> None:
        """Apply staleness action to memory.

        Args:
            memory: Memory to update
            action: Action to apply
        """
        if action == StalenessAction.REFRESH:
            # For refresh, we would ideally re-scan the source
            # For now, just update last_accessed_at using update_importance
            await self.memory_repository.update_importance(
                memory_id=memory.id,
                score=memory.importance_score,
                last_accessed_at=datetime.now(timezone.utc),
            )

        elif action == StalenessAction.ARCHIVE:
            # Lower importance score
            new_score = max(0.0, memory.importance_score - 0.3)
            await self.memory_repository.update_importance(
                memory_id=memory.id,
                score=new_score,
            )

        elif action == StalenessAction.DELETE:
            # Delete memory
            await self.memory_repository.delete(memory.id)
