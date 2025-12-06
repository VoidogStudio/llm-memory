"""Tests for Smart Chunking feature (FR-003)."""

import json

import pytest

from llm_memory.db.repositories.knowledge_repository import KnowledgeRepository
from llm_memory.services.embedding_service import EmbeddingService
from llm_memory.services.knowledge_service import KnowledgeService


@pytest.fixture
def sample_markdown() -> str:
    """Sample Markdown for testing."""
    return """# Introduction

This is the introduction section with some content.

## Background

Background information about the topic.

### Details

More detailed information about the background.

## Conclusion

Summary and conclusion of the document."""


@pytest.fixture
def large_markdown() -> str:
    """Large Markdown section that exceeds chunk size."""
    return """# Large Section

This is a very long section that will exceed the chunk size limit. """ + ("x" * 1000)


# SC-001: Sentence 戦略の基本動作
@pytest.mark.asyncio
async def test_sentence_chunking_strategy(
    knowledge_service: KnowledgeService,
) -> None:
    """Test SC-001: Sentence chunking strategy basic operation."""
    # Given: Text with multiple sentences
    content = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."

    # When: Import with sentence strategy
    doc, chunks_created = await knowledge_service.import_document(
        title="Test Document",
        content=content,
        chunking_strategy="sentence",
        chunk_size=30,  # Force multiple chunks
    )

    # Then: Content should be split at sentence boundaries
    assert chunks_created > 1
    assert doc.id is not None
    assert doc.title == "Test Document"

    # Verify chunks are sentence-based
    # Query chunks directly from database
    cursor = await knowledge_service.repository.db.execute(
        "SELECT content FROM knowledge_chunks WHERE document_id = ? ORDER BY chunk_index",
        (doc.id,)
    )
    rows = await cursor.fetchall()
    for row in rows:
        # Each chunk should not exceed chunk_size much (allows for sentence completion)
        assert len(row["content"]) <= 100  # Reasonable bound


# SC-002: Paragraph 戦略の基本動作
@pytest.mark.asyncio
async def test_paragraph_chunking_strategy(
    knowledge_service: KnowledgeService,
) -> None:
    """Test SC-002: Paragraph chunking strategy basic operation."""
    # Given: Text with multiple paragraphs
    content = """First paragraph with some content.

Second paragraph with more content.

Third paragraph with additional content."""

    # When: Import with paragraph strategy
    doc, chunks_created = await knowledge_service.import_document(
        title="Test Document",
        content=content,
        chunking_strategy="paragraph",
        chunk_size=500,
    )

    # Then: Content should be split by paragraph boundaries
    assert chunks_created == 3
    assert doc.title == "Test Document"

    # Verify chunks
    cursor = await knowledge_service.repository.db.execute(
        "SELECT COUNT(*) as count FROM knowledge_chunks WHERE document_id = ?",
        (doc.id,)
    )
    row = await cursor.fetchone()
    assert row["count"] == 3


# SC-003: Semantic 戦略の基本動作
@pytest.mark.asyncio
async def test_semantic_chunking_strategy(
    knowledge_service: KnowledgeService,
    sample_markdown: str,
) -> None:
    """Test SC-003: Semantic chunking strategy with Markdown."""
    # When: Import Markdown with semantic strategy
    doc, chunks_created = await knowledge_service.import_document(
        title="Test Markdown",
        content=sample_markdown,
        chunking_strategy="semantic",
    )

    # Then: Content should be split by sections
    assert chunks_created >= 3  # Introduction, Background, Details, Conclusion
    assert doc.title == "Test Markdown"

    # Verify section paths are set
    cursor = await knowledge_service.repository.db.execute(
        "SELECT section_path FROM knowledge_chunks WHERE document_id = ?",
        (doc.id,)
    )
    rows = await cursor.fetchall()
    section_paths = [json.loads(row["section_path"]) for row in rows]

    # Check for expected section paths (paths are hierarchical)
    assert ["Introduction"] in section_paths
    # Background can appear as nested path
    has_background = any("Background" in path for path in section_paths)
    assert has_background, f"Expected 'Background' in section_paths, got {section_paths}"
    # Conclusion can also be nested under Introduction
    has_conclusion = any("Conclusion" in path for path in section_paths)
    assert has_conclusion, f"Expected 'Conclusion' in section_paths, got {section_paths}"


# SC-004: has_previous/has_next の設定
@pytest.mark.asyncio
async def test_has_previous_has_next_flags(
    knowledge_service: KnowledgeService,
) -> None:
    """Test SC-004: has_previous and has_next flags are set correctly."""
    # Given: Content that will be split into multiple chunks
    content = "First sentence. " * 20 + "Second sentence. " * 20 + "Third sentence. " * 20

    # When: Import with sentence strategy
    doc, chunks_created = await knowledge_service.import_document(
        title="Test Document",
        content=content,
        chunking_strategy="sentence",
        chunk_size=100,
    )

    # Then: Chunks should have correct flags
    assert chunks_created > 1

    cursor = await knowledge_service.repository.db.execute(
        "SELECT has_previous, has_next FROM knowledge_chunks WHERE document_id = ? ORDER BY chunk_index",
        (doc.id,)
    )
    rows = await cursor.fetchall()
    assert len(rows) > 1

    # First chunk: has_previous=False, has_next=True
    assert rows[0]["has_previous"] == 0  # False
    assert rows[0]["has_next"] == 1  # True

    # Middle chunks: has_previous=True, has_next=True
    if len(rows) > 2:
        for i in range(1, len(rows) - 1):
            assert rows[i]["has_previous"] == 1  # True
            assert rows[i]["has_next"] == 1  # True

    # Last chunk: has_previous=True, has_next=False
    assert rows[-1]["has_previous"] == 1  # True
    assert rows[-1]["has_next"] == 0  # False


# SC-005: 非Markdownでのフォールバック
@pytest.mark.asyncio
async def test_semantic_fallback_on_plain_text(
    knowledge_service: KnowledgeService,
) -> None:
    """Test SC-005: Semantic strategy falls back to paragraph on plain text."""
    # Given: Plain text without Markdown headings
    content = """This is plain text without any Markdown headings.

It has paragraphs but no sections.

This should fallback to paragraph strategy."""

    # When: Import with semantic strategy
    doc, chunks_created = await knowledge_service.import_document(
        title="Plain Text",
        content=content,
        chunking_strategy="semantic",
        chunk_size=500,
    )

    # Then: Should fallback to paragraph strategy
    assert chunks_created >= 1

    cursor = await knowledge_service.repository.db.execute(
        "SELECT section_path FROM knowledge_chunks WHERE document_id = ?",
        (doc.id,)
    )
    rows = await cursor.fetchall()
    # All chunks should have empty section_path (no Markdown sections)
    for row in rows:
        section_path = json.loads(row["section_path"])
        assert section_path == []


# SC-006: 大きなセクションのフォールバック
@pytest.mark.asyncio
async def test_semantic_fallback_on_large_section(
    knowledge_service: KnowledgeService,
    large_markdown: str,
) -> None:
    """Test SC-006: Large sections are split using paragraph fallback."""
    # When: Import large Markdown section
    doc, chunks_created = await knowledge_service.import_document(
        title="Large Section",
        content=large_markdown,
        chunking_strategy="semantic",
        chunk_size=200,  # Small chunk size to force splitting
    )

    # Then: Section should be split into multiple chunks
    assert chunks_created > 1

    cursor = await knowledge_service.repository.db.execute(
        "SELECT section_path FROM knowledge_chunks WHERE document_id = ?",
        (doc.id,)
    )
    rows = await cursor.fetchall()
    # All chunks should have same section_path
    section_paths = [json.loads(row["section_path"]) for row in rows]
    # All should belong to "Large Section"
    for path in section_paths:
        assert "Large Section" in path if path else True


# SC-007: 不正な chunking_strategy の拒否
@pytest.mark.asyncio
async def test_invalid_chunking_strategy_rejected(
    knowledge_service: KnowledgeService,
) -> None:
    """Test SC-007: Invalid chunking strategy is rejected."""
    # When/Then: Invalid strategy should raise ValueError
    with pytest.raises(ValueError, match="chunking_strategy must be one of"):
        await knowledge_service.import_document(
            title="Test",
            content="Some content",
            chunking_strategy="invalid",
        )


# SC-008: 空のコンテンツ
@pytest.mark.asyncio
async def test_empty_content_handling(
    knowledge_repository: KnowledgeRepository,
    embedding_service: EmbeddingService,
) -> None:
    """Test SC-008: Empty content handling."""
    # Given: Knowledge service
    service = KnowledgeService(
        repository=knowledge_repository, embedding_service=embedding_service
    )

    # When: Import with empty content
    # Note: The service will create chunks, but empty content should result in 0 chunks
    content = ""

    # Test that split methods return empty list for empty content
    result = service.split_by_sentence(content)
    assert result == []

    result = service.split_by_paragraph(content)
    assert result == []

    result = service.split_by_semantic(content)
    assert result == []
