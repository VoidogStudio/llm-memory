"""Tests for Memory Versioning (FR-001)."""

import pytest
from src.exceptions import NotFoundError, ValidationError
from src.models.versioning import VersionHistory, MemoryVersion, VersionDiff
from src.services.versioning_service import VersioningService


class TestVersionHistory:
    """Test version history retrieval."""

    async def test_basic_version_history(
        self, memory_service, memory_repository, versioning_service
    ):
        """VER-001: Test basic version history retrieval."""
        # Given: Memory updated 3 times
        memory = await memory_service.store(content="Version 1")
        await memory_service.update(memory.id, content="Version 2")
        await memory_service.update(memory.id, content="Version 3")

        # When: Get version history
        history = await versioning_service.get_history(memory.id, limit=10)

        # Then: Verify history
        assert history.current_version == 3
        assert history.total_versions == 3
        assert len(history.versions) == 2  # Excludes current version
        assert history.versions[0].version == 2  # Descending order
        assert history.versions[1].version == 1

    async def test_new_memory_no_history(self, memory_service, versioning_service):
        """VER-002: Test history of newly created memory."""
        # Given: New memory (version=1)
        memory = await memory_service.store(content="New content")

        # When: Get version history
        history = await versioning_service.get_history(memory.id)

        # Then: No previous versions
        assert history.current_version == 1
        assert history.total_versions == 1
        assert len(history.versions) == 0

    async def test_nonexistent_memory_history(self, versioning_service):
        """VER-003: Test history of non-existent memory."""
        # Given: Non-existent memory_id
        # When/Then: Raises NotFoundError
        with pytest.raises(NotFoundError):
            await versioning_service.get_history("non-existent-id")

    async def test_limit_parameter(self, memory_service, versioning_service):
        """VER-004: Test limit parameter validation."""
        # Given: Memory with 10 versions
        memory = await memory_service.store(content="V1")
        for i in range(2, 11):
            await memory_service.update(memory.id, content=f"V{i}")

        # When: Get with limit=3
        history = await versioning_service.get_history(memory.id, limit=3)

        # Then: Only 3 most recent versions
        assert len(history.versions) == 3
        assert history.versions[0].version == 9
        assert history.versions[2].version == 7

    async def test_limit_out_of_range(self, memory_service, versioning_service):
        """VER-005: Test limit parameter range validation."""
        # Given: Any memory
        memory = await memory_service.store(content="Test")

        # When/Then: limit > 50 raises ValidationError
        with pytest.raises(ValidationError):
            await versioning_service.get_history(memory.id, limit=100)


class TestVersionGet:
    """Test specific version retrieval."""

    async def test_get_specific_version(self, memory_service, versioning_service):
        """VER-006: Test retrieving specific version."""
        # Given: Memory with version 2
        memory = await memory_service.store(content="V1", tags=["tag1"])
        await memory_service.update(memory.id, content="V2", tags=["tag2"])

        # When: Get version 1
        version = await versioning_service.get_version(memory.id, version=1)

        # Then: Verify version 1 content
        assert version.version == 1
        assert version.content == "V1"
        assert version.tags == ["tag1"]

    async def test_get_nonexistent_version(self, memory_service, versioning_service):
        """VER-007: Test retrieving non-existent version."""
        # Given: Memory with versions 1-3
        memory = await memory_service.store(content="V1")
        await memory_service.update(memory.id, content="V2")
        await memory_service.update(memory.id, content="V3")

        # When/Then: version=5 raises NotFoundError
        with pytest.raises(NotFoundError):
            await versioning_service.get_version(memory.id, version=5)


class TestVersionRollback:
    """Test version rollback functionality."""

    async def test_normal_rollback(
        self, memory_service, memory_repository, versioning_service
    ):
        """VER-008: Test normal rollback operation."""
        # Given: Memory at version 3, version 1 had "old"
        memory = await memory_service.store(content="old")
        await memory_service.update(memory.id, content="middle")
        await memory_service.update(memory.id, content="new")

        # When: Rollback to version 1
        rolled_back = await versioning_service.rollback(memory.id, target_version=1)

        # Then: Verify rollback
        assert rolled_back.content == "old"
        assert rolled_back.version == 4  # Rollback creates new version

        # Verify version 3 is saved in history
        history = await versioning_service.get_history(memory.id)
        assert history.current_version == 4
        assert any(v.version == 3 for v in history.versions)

    async def test_rollback_to_current_version(self, memory_service, versioning_service):
        """VER-009: Test rollback to current version."""
        # Given: Memory at version 3
        memory = await memory_service.store(content="V1")
        await memory_service.update(memory.id, content="V2")
        await memory_service.update(memory.id, content="V3")

        # When/Then: Rollback to current version raises ValidationError
        with pytest.raises(ValidationError):
            await versioning_service.rollback(memory.id, target_version=3)

    async def test_rollback_reason_recorded(
        self, memory_service, versioning_service
    ):
        """VER-010: Test rollback reason is recorded."""
        # Given: Memory at version 2
        memory = await memory_service.store(content="V1")
        await memory_service.update(memory.id, content="V2")

        # When: Rollback with reason
        await versioning_service.rollback(
            memory.id, target_version=1, reason="Bug fix"
        )

        # Then: Reason is recorded
        history = await versioning_service.get_history(memory.id)
        version_2 = next(v for v in history.versions if v.version == 2)
        assert "Bug fix" in version_2.change_reason


class TestVersionDiff:
    """Test version diff functionality."""

    async def test_content_diff(self, memory_service, versioning_service):
        """VER-011: Test content change diff."""
        # Given: Version 1 and 2 with different content
        memory = await memory_service.store(content="Hello")
        await memory_service.update(memory.id, content="Hello World")

        # When: Get diff
        diff = await versioning_service.diff_versions(
            memory.id, old_version=1, new_version=2
        )

        # Then: Content changed
        assert diff.content_changed is True
        assert diff.content_diff is not None
        assert "Hello" in diff.content_diff
        assert "World" in diff.content_diff

    async def test_tags_diff(self, memory_service, versioning_service):
        """VER-012: Test tags change diff."""
        # Given: Version 1 and 2 with different tags
        memory = await memory_service.store(content="Test", tags=["a", "b"])
        await memory_service.update(memory.id, tags=["b", "c"])

        # When: Get diff
        diff = await versioning_service.diff_versions(
            memory.id, old_version=1, new_version=2
        )

        # Then: Tags changed
        assert "c" in diff.tags_added
        assert "a" in diff.tags_removed

    async def test_no_content_change_diff(self, memory_service, versioning_service):
        """VER-013: Test diff when content unchanged."""
        # Given: Two versions with same content
        memory = await memory_service.store(content="Same", tags=["v1"])
        await memory_service.update(memory.id, tags=["v2"])  # Only tags changed

        # When: Get diff
        diff = await versioning_service.diff_versions(
            memory.id, old_version=1, new_version=2
        )

        # Then: No content change
        assert diff.content_changed is False
        assert diff.content_diff is None

    async def test_reverse_version_order(self, memory_service, versioning_service):
        """VER-014: Test reverse version order raises error."""
        # Given: Memory with versions 1 and 2
        memory = await memory_service.store(content="V1")
        await memory_service.update(memory.id, content="V2")

        # When/Then: old_version > new_version raises ValidationError
        with pytest.raises(ValidationError):
            await versioning_service.diff_versions(
                memory.id, old_version=2, new_version=1
            )


# Fixtures

@pytest.fixture
async def versioning_service(memory_db, memory_repository):
    """VersioningService instance for testing."""
    return VersioningService(repository=memory_repository)
