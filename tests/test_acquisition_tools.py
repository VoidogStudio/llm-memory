"""Tests for acquisition tools."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.acquisition import (
    DetectedConfig,
    LearningCategory,
    LearningResult,
    ProjectType,
    ScanResult,
    ScanStatistics,
    StalenessResult,
    RefreshResult,
    SyncResult,
    SyncStatistics,
)
from src.tools.acquisition_tools import (
    knowledge_sync,
    project_scan,
    session_learn,
    knowledge_check_staleness,
    knowledge_refresh_stale,
)


class TestProjectScanTool:
    """Test project_scan tool."""

    @pytest.mark.asyncio
    async def test_project_scan_success(self):
        """Test successful project scan."""
        # Mock service
        mock_service = AsyncMock()
        mock_service.scan.return_value = ScanResult(
            project_name="test-project",
            namespace="project_test",
            statistics=ScanStatistics(
                files_scanned=10, memories_created=8, memories_updated=2
            ),
            project_type=ProjectType.PYTHON,
            detected_config=DetectedConfig(
                package_manager="pip", test_framework="pytest"
            ),
        )

        result = await project_scan(
            service=mock_service,
            project_path="/path/to/project",
        )

        assert "project_name" in result
        assert result["project_name"] == "test-project"
        assert result["statistics"]["files_scanned"] == 10
        mock_service.scan.assert_called_once()

    @pytest.mark.asyncio
    async def test_project_scan_empty_path(self):
        """Test project scan with empty path."""
        mock_service = AsyncMock()

        result = await project_scan(service=mock_service, project_path="")

        assert result["error"] is True
        assert "empty" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_project_scan_invalid_max_file_size(self):
        """Test project scan with invalid max_file_size_kb."""
        mock_service = AsyncMock()

        # Too small
        result = await project_scan(
            service=mock_service, project_path="/path", max_file_size_kb=0
        )
        assert result["error"] is True

        # Too large
        result = await project_scan(
            service=mock_service, project_path="/path", max_file_size_kb=10001
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_project_scan_file_not_found(self):
        """Test project scan with non-existent path."""
        mock_service = AsyncMock()
        mock_service.scan.side_effect = FileNotFoundError("Path not found")

        result = await project_scan(
            service=mock_service, project_path="/nonexistent"
        )

        assert result["error"] is True
        assert result["error_type"] == "FileNotFoundError"

    @pytest.mark.asyncio
    async def test_project_scan_with_patterns(self):
        """Test project scan with include/exclude patterns."""
        mock_service = AsyncMock()
        mock_service.scan.return_value = ScanResult(
            project_name="test",
            namespace="test",
            statistics=ScanStatistics(),
            project_type=ProjectType.PYTHON,
            detected_config=DetectedConfig(),
        )

        await project_scan(
            service=mock_service,
            project_path="/path",
            include_patterns=["*.py"],
            exclude_patterns=["test_*.py"],
        )

        call_args = mock_service.scan.call_args
        assert call_args.kwargs["include_patterns"] == ["*.py"]
        assert call_args.kwargs["exclude_patterns"] == ["test_*.py"]


class TestKnowledgeSyncTool:
    """Test knowledge_sync tool."""

    @pytest.mark.asyncio
    async def test_knowledge_sync_success(self):
        """Test successful knowledge sync."""
        mock_service = AsyncMock()
        mock_service.sync.return_value = SyncResult(
            sync_id="test-sync-id",
            namespace="docs",
            statistics=SyncStatistics(
                files_processed=5, chunks_created=50, chunks_updated=10
            ),
            source_type="local_file",
            source_path="/path/to/docs",
        )

        result = await knowledge_sync(
            service=mock_service,
            source_type="local_file",
            source_path="/path/to/doc.md",
        )

        assert result["source_type"] == "local_file"
        assert result["statistics"]["files_processed"] == 5
        mock_service.sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_knowledge_sync_invalid_source_type(self):
        """Test knowledge sync with invalid source type."""
        mock_service = AsyncMock()

        result = await knowledge_sync(
            service=mock_service,
            source_type="invalid_type",
            source_path="/path",
        )

        assert result["error"] is True
        assert "Invalid source_type" in result["message"]

    @pytest.mark.asyncio
    async def test_knowledge_sync_empty_path(self):
        """Test knowledge sync with empty source path."""
        mock_service = AsyncMock()

        result = await knowledge_sync(
            service=mock_service,
            source_type="local_file",
            source_path="",
        )

        assert result["error"] is True
        assert "empty" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_knowledge_sync_invalid_chunk_size(self):
        """Test knowledge sync with invalid chunk size."""
        mock_service = AsyncMock()

        # Too small
        result = await knowledge_sync(
            service=mock_service,
            source_type="local_file",
            source_path="/path",
            chunk_size=10,
        )
        assert result["error"] is True

        # Too large
        result = await knowledge_sync(
            service=mock_service,
            source_type="local_file",
            source_path="/path",
            chunk_size=10000,
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_knowledge_sync_invalid_chunk_overlap(self):
        """Test knowledge sync with invalid chunk overlap."""
        mock_service = AsyncMock()

        # Negative overlap
        result = await knowledge_sync(
            service=mock_service,
            source_type="local_file",
            source_path="/path",
            chunk_overlap=-1,
        )
        assert result["error"] is True

        # Overlap >= chunk_size
        result = await knowledge_sync(
            service=mock_service,
            source_type="local_file",
            source_path="/path",
            chunk_size=100,
            chunk_overlap=100,
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_knowledge_sync_invalid_update_mode(self):
        """Test knowledge sync with invalid update mode."""
        mock_service = AsyncMock()

        result = await knowledge_sync(
            service=mock_service,
            source_type="local_file",
            source_path="/path",
            update_mode="invalid",
        )

        assert result["error"] is True
        assert "update_mode" in result["message"]


class TestSessionLearnTool:
    """Test session_learn tool."""

    @pytest.mark.asyncio
    async def test_session_learn_success(self):
        """Test successful session learning."""
        mock_service = AsyncMock()
        mock_service.learn.return_value = LearningResult(
            learning_id="learn-123",
            memory_id="mem-123",
            content="Fix ImportError by adding to PYTHONPATH",
            action_taken="created",
            category=LearningCategory.ERROR_RESOLUTION,
            confidence=0.9,
            similar_learnings=[],
        )

        result = await session_learn(
            service=mock_service,
            content="Fix ImportError by adding to PYTHONPATH",
            category="error_resolution",
        )

        assert result["learning_id"] == "learn-123"
        assert result["action_taken"] == "created"
        mock_service.learn.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_learn_empty_content(self):
        """Test session learn with empty content."""
        mock_service = AsyncMock()

        result = await session_learn(
            service=mock_service, content="", category="error_resolution"
        )

        assert result["error"] is True
        assert "empty" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_session_learn_invalid_category(self):
        """Test session learn with invalid category."""
        mock_service = AsyncMock()
        mock_service.learn.side_effect = ValueError("Invalid category")

        result = await session_learn(
            service=mock_service, content="Test", category="invalid_category"
        )

        assert result["error"] is True
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_session_learn_invalid_confidence(self):
        """Test session learn with invalid confidence."""
        mock_service = AsyncMock()

        # Too low
        result = await session_learn(
            service=mock_service,
            content="Test",
            category="error_resolution",
            confidence=-0.1,
        )
        assert result["error"] is True

        # Too high
        result = await session_learn(
            service=mock_service,
            content="Test",
            category="error_resolution",
            confidence=1.5,
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_session_learn_with_optional_params(self):
        """Test session learn with optional parameters."""
        mock_service = AsyncMock()
        mock_service.learn.return_value = LearningResult(
            learning_id="learn-456",
            memory_id="mem-456",
            content="Always use async for I/O",
            action_taken="created",
            category=LearningCategory.BEST_PRACTICE,
            confidence=0.95,
            similar_learnings=[],
        )

        result = await session_learn(
            service=mock_service,
            content="Always use async for I/O",
            category="best_practice",
            context="Working on API",
            confidence=0.95,
            related_files=["api.py"],
            tags=["async", "performance"],
        )

        assert result["learning_id"] == "learn-456"
        call_args = mock_service.learn.call_args
        assert call_args.kwargs["context"] == "Working on API"
        assert call_args.kwargs["related_files"] == ["api.py"]


class TestKnowledgeCheckStalenessTool:
    """Test knowledge_check_staleness tool."""

    @pytest.mark.asyncio
    async def test_check_staleness_success(self):
        """Test successful staleness check."""
        from src.models.acquisition import StalenessStatistics
        mock_service = AsyncMock()
        mock_service.check.return_value = StalenessResult(
            namespace="default",
            statistics=StalenessStatistics(total_checked=100, stale_count=5),
            stale_memories=[],
            recommendations=[],
        )

        result = await knowledge_check_staleness(
            service=mock_service, stale_days=30
        )

        assert result["statistics"]["total_checked"] == 100
        assert result["statistics"]["stale_count"] == 5
        mock_service.check.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_staleness_invalid_days(self):
        """Test staleness check with invalid stale_days."""
        mock_service = AsyncMock()

        # Less than 1
        result = await knowledge_check_staleness(
            service=mock_service, stale_days=0
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_check_staleness_with_filters(self):
        """Test staleness check with category filters."""
        from src.models.acquisition import StalenessStatistics
        mock_service = AsyncMock()
        mock_service.check.return_value = StalenessResult(
            namespace="default",
            statistics=StalenessStatistics(total_checked=50, stale_count=2),
            stale_memories=[],
            recommendations=[],
        )

        await knowledge_check_staleness(
            service=mock_service,
            stale_days=30,
            include_auto_scan=True,
            include_sync=False,
        )

        call_args = mock_service.check.call_args
        assert call_args.kwargs["include_auto_scan"] is True
        assert call_args.kwargs["include_sync"] is False


class TestKnowledgeRefreshStaleTool:
    """Test knowledge_refresh_stale tool."""

    @pytest.mark.asyncio
    async def test_refresh_stale_success(self):
        """Test successful stale knowledge refresh."""
        from src.models.acquisition import StalenessAction
        mock_service = AsyncMock()
        mock_service.refresh.return_value = RefreshResult(
            action=StalenessAction.REFRESH,
            affected_count=3,
            affected_memories=[],
            dry_run=False,
        )

        result = await knowledge_refresh_stale(
            service=mock_service, action="refresh", dry_run=False
        )

        assert result["action"] == "refresh"
        assert result["affected_count"] == 3
        mock_service.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_stale_invalid_action(self):
        """Test refresh with invalid action."""
        mock_service = AsyncMock()

        result = await knowledge_refresh_stale(
            service=mock_service, action="invalid_action", dry_run=True
        )

        assert result["error"] is True
        assert "Invalid action" in result["message"]

    @pytest.mark.asyncio
    async def test_refresh_stale_dry_run(self):
        """Test refresh in dry-run mode."""
        from src.models.acquisition import StalenessAction
        mock_service = AsyncMock()
        mock_service.refresh.return_value = RefreshResult(
            action=StalenessAction.ARCHIVE,
            affected_count=5,
            affected_memories=[],
            dry_run=True,
        )

        result = await knowledge_refresh_stale(
            service=mock_service, action="archive", dry_run=True
        )

        assert result["dry_run"] is True
        assert result["affected_count"] == 5

    @pytest.mark.asyncio
    async def test_refresh_stale_with_memory_ids(self):
        """Test refresh with specific memory IDs."""
        from src.models.acquisition import StalenessAction
        mock_service = AsyncMock()
        mock_service.refresh.return_value = RefreshResult(
            action=StalenessAction.DELETE,
            affected_count=2,
            affected_memories=[],
            dry_run=False,
        )

        memory_ids = ["mem-1", "mem-2"]
        await knowledge_refresh_stale(
            service=mock_service,
            action="delete",
            memory_ids=memory_ids,
            dry_run=False,
        )

        call_args = mock_service.refresh.call_args
        assert call_args.kwargs["memory_ids"] == memory_ids

    @pytest.mark.asyncio
    async def test_refresh_stale_all_actions(self):
        """Test all valid refresh actions."""
        from src.models.acquisition import StalenessAction
        mock_service = AsyncMock()

        actions = ["refresh", "archive", "delete"]
        action_enums = [StalenessAction.REFRESH, StalenessAction.ARCHIVE, StalenessAction.DELETE]
        for action, action_enum in zip(actions, action_enums, strict=True):
            mock_service.refresh.return_value = RefreshResult(
                action=action_enum,
                affected_count=1,
                affected_memories=[],
                dry_run=True,
            )

            result = await knowledge_refresh_stale(
                service=mock_service, action=action, dry_run=True
            )

            assert result["action"] == action
