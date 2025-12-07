"""Tests for acquisition models."""

import uuid
from datetime import datetime, timezone

import pytest

from src.models.acquisition import (
    DetectedConfig,
    LearningCategory,
    ProjectType,
    ScanResult,
    ScanStatistics,
    SourceType,
    StalenessAction,
    SyncSourceType,
    SyncStatistics,
)


class TestAcquisitionEnums:
    """Test acquisition enum types."""

    def test_source_type_values(self):
        """Test SourceType enum values."""
        assert SourceType.PROJECT_SCAN == "project_scan"
        assert SourceType.KNOWLEDGE_SYNC == "knowledge_sync"
        assert SourceType.SESSION_LEARNING == "session_learning"
        assert SourceType.MANUAL == "manual"

    def test_sync_source_type_values(self):
        """Test SyncSourceType enum values."""
        assert SyncSourceType.LOCAL_FILE == "local_file"
        assert SyncSourceType.LOCAL_DIRECTORY == "local_directory"
        assert SyncSourceType.URL == "url"
        assert SyncSourceType.GITHUB_REPO == "github_repo"

    def test_learning_category_values(self):
        """Test LearningCategory enum values."""
        assert LearningCategory.ERROR_RESOLUTION == "error_resolution"
        assert LearningCategory.DESIGN_DECISION == "design_decision"
        assert LearningCategory.BEST_PRACTICE == "best_practice"
        assert LearningCategory.USER_PREFERENCE == "user_preference"

    def test_project_type_values(self):
        """Test ProjectType enum values."""
        assert ProjectType.PYTHON == "python"
        assert ProjectType.NODEJS == "nodejs"
        assert ProjectType.RUST == "rust"
        assert ProjectType.GO == "go"
        assert ProjectType.JAVA == "java"
        assert ProjectType.UNKNOWN == "unknown"

    def test_staleness_action_values(self):
        """Test StalenessAction enum values."""
        assert StalenessAction.REFRESH == "refresh"
        assert StalenessAction.ARCHIVE == "archive"
        assert StalenessAction.DELETE == "delete"


class TestScanStatistics:
    """Test ScanStatistics model."""

    def test_default_initialization(self):
        """Test default initialization of ScanStatistics."""
        stats = ScanStatistics()

        assert stats.files_scanned == 0
        assert stats.memories_created == 0
        assert stats.memories_updated == 0
        assert stats.errors == 0
        assert stats.skipped_files == 0

    def test_custom_initialization(self):
        """Test custom initialization of ScanStatistics."""
        stats = ScanStatistics(
            files_scanned=100,
            memories_created=80,
            memories_updated=20,
            errors=5,
            skipped_files=15,
        )

        assert stats.files_scanned == 100
        assert stats.memories_created == 80
        assert stats.memories_updated == 20
        assert stats.errors == 5
        assert stats.skipped_files == 15


class TestDetectedConfig:
    """Test DetectedConfig model."""

    def test_default_initialization(self):
        """Test default initialization of DetectedConfig."""
        config = DetectedConfig()

        assert config.package_manager is None
        assert config.test_framework is None
        assert config.linter is None
        assert config.formatter is None
        assert config.language_version is None

    def test_python_project_config(self):
        """Test Python project configuration."""
        config = DetectedConfig(
            package_manager="pip",
            test_framework="pytest",
            linter="ruff",
            formatter="black",
            language_version="3.11",
        )

        assert config.package_manager == "pip"
        assert config.test_framework == "pytest"
        assert config.linter == "ruff"
        assert config.formatter == "black"
        assert config.language_version == "3.11"


class TestScanResult:
    """Test ScanResult model."""

    def test_scan_result_creation(self):
        """Test ScanResult creation with all fields."""
        stats = ScanStatistics(
            files_scanned=50, memories_created=40, memories_updated=10
        )
        config = DetectedConfig(
            package_manager="pip", test_framework="pytest", linter="ruff"
        )

        result = ScanResult(
            project_name="test-project",
            namespace="test-namespace",
            statistics=stats,
            project_type=ProjectType.PYTHON,
            detected_config=config,
        )

        assert result.project_name == "test-project"
        assert result.namespace == "test-namespace"
        assert result.statistics.files_scanned == 50
        assert result.project_type == ProjectType.PYTHON
        assert result.detected_config.linter == "ruff"
        assert isinstance(result.scan_id, str)
        assert isinstance(result.scanned_at, datetime)

    def test_scan_id_is_unique(self):
        """Test that each ScanResult gets a unique scan_id."""
        result1 = ScanResult(
            project_name="test",
            namespace="ns",
            statistics=ScanStatistics(),
            project_type=ProjectType.PYTHON,
            detected_config=DetectedConfig(),
        )
        result2 = ScanResult(
            project_name="test",
            namespace="ns",
            statistics=ScanStatistics(),
            project_type=ProjectType.PYTHON,
            detected_config=DetectedConfig(),
        )

        assert result1.scan_id != result2.scan_id
        # Verify it's a valid UUID
        uuid.UUID(result1.scan_id)
        uuid.UUID(result2.scan_id)

    def test_scan_result_with_errors(self):
        """Test ScanResult with error information."""
        errors = [
            {"file": "test.py", "error": "FileNotFoundError"},
            {"file": "main.py", "error": "PermissionError"},
        ]

        result = ScanResult(
            project_name="test",
            namespace="ns",
            statistics=ScanStatistics(errors=2),
            project_type=ProjectType.PYTHON,
            detected_config=DetectedConfig(),
            errors=errors,
        )

        assert len(result.errors) == 2
        assert result.statistics.errors == 2
        assert result.errors[0]["file"] == "test.py"

    def test_scan_result_with_categories(self):
        """Test ScanResult with category statistics."""
        result = ScanResult(
            project_name="test",
            namespace="ns",
            statistics=ScanStatistics(),
            project_type=ProjectType.PYTHON,
            detected_config=DetectedConfig(),
            categories={"source_code": 30, "documentation": 15, "config": 5},
        )

        assert result.categories["source_code"] == 30
        assert result.categories["documentation"] == 15
        assert result.categories["config"] == 5


class TestSyncStatistics:
    """Test SyncStatistics model."""

    def test_default_initialization(self):
        """Test default initialization of SyncStatistics."""
        stats = SyncStatistics()

        assert stats.files_processed == 0
        assert stats.chunks_created == 0
        assert stats.chunks_updated == 0
        assert stats.chunks_deleted == 0
        assert stats.unchanged == 0

    def test_sync_statistics_with_values(self):
        """Test SyncStatistics with custom values."""
        stats = SyncStatistics(
            files_processed=20,
            chunks_created=100,
            chunks_updated=30,
            chunks_deleted=5,
            unchanged=10,
        )

        assert stats.files_processed == 20
        assert stats.chunks_created == 100
        assert stats.chunks_updated == 30
        assert stats.chunks_deleted == 5
        assert stats.unchanged == 10
