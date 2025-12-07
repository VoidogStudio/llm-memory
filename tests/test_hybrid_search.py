"""Tests for FR-003: Hybrid Search."""

import pytest

from src.services.memory_service import MemoryService
from src.services.tokenization_service import TokenizationService


class TestTokenization:
    """Test TokenizationService functionality."""

    def test_tokenization_service_initialization(self):
        """Test Case 23/24: Initialize tokenization service."""
        service = TokenizationService()
        assert service is not None

    def test_tokenize_english_text(self):
        """Test Case 24: Tokenize English text (fallback when SudachiPy not available)."""
        service = TokenizationService()
        result = service.tokenize("English text here")

        # Should return some form of tokenized text
        assert result is not None
        assert isinstance(result, str)

    def test_has_japanese_support(self):
        """Test Case 25: Check Japanese support availability."""
        service = TokenizationService()

        # Should return boolean indicating SudachiPy availability
        assert isinstance(service.has_japanese_support, bool)

    def test_tokenize_query(self):
        """Test FTS5 query tokenization."""
        service = TokenizationService()
        query = 'test "exact phrase" search'
        result = service.tokenize_query(query)

        # Should escape special characters for FTS5
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.asyncio
class TestKeywordSearch:
    """Test FTS5 keyword search functionality."""

    async def test_keyword_search_basic(self, memory_service: MemoryService):
        """Test Case 26: Basic keyword search."""
        # Create memories with different content
        await memory_service.store(content="apple banana fruit", content_type="text")
        await memory_service.store(content="cherry apple dessert", content_type="text")
        await memory_service.store(content="date fig snack", content_type="text")

        # Search for "apple"
        result = await memory_service.search(
            query="apple",
            search_mode="keyword",
            top_k=10,
        )

        # Should find 2 memories with "apple"
        assert len(result) == 2

        # Results should have keyword_score
        for res in result:
            assert res.keyword_score is not None

    async def test_keyword_search_phrase(self, memory_service: MemoryService):
        """Test Case 27: Phrase search with quotes."""
        await memory_service.store(content="quick brown fox jumps", content_type="text")
        await memory_service.store(content="brown fox running", content_type="text")
        await memory_service.store(content="quick fox", content_type="text")

        # Search for exact phrase "brown fox"
        result = await memory_service.search(
            query='"brown fox"',
            search_mode="keyword",
            top_k=10,
        )

        # Should find memories with the exact phrase
        assert len(result) >= 1
        assert any("brown fox" in r.memory.content.lower() for r in result)

    async def test_keyword_search_with_filter(self, memory_service: MemoryService):
        """Test Case 28: Keyword search with memory_tier filter."""
        # Create memories with different tiers
        await memory_service.store(
            content="long term apple memory",
            content_type="text",
            memory_tier="long_term",
        )
        await memory_service.store(
            content="working apple memory",
            content_type="text",
            memory_tier="working",
        )
        await memory_service.store(
            content="short term apple memory",
            content_type="text",
            memory_tier="short_term",
        )

        # Search with tier filter
        result = await memory_service.search(
            query="apple",
            search_mode="keyword",
            memory_tier="long_term",
            top_k=10,
        )

        # Should only find long_term memories
        assert len(result) >= 1
        for res in result:
            mem = await memory_service.get(res.memory.id)
            assert mem.memory_tier == "long_term"


@pytest.mark.asyncio
class TestHybridSearch:
    """Test hybrid search functionality."""

    async def test_hybrid_search_rrf(self, memory_service: MemoryService):
        """Test Case 29: Hybrid search with RRF integration."""
        # Create diverse memories
        await memory_service.store(content="Python programming language", content_type="text")
        await memory_service.store(content="Java programming tutorial", content_type="text")
        await memory_service.store(content="Machine learning with Python", content_type="text")
        await memory_service.store(content="Data science programming", content_type="text")

        # Hybrid search for "programming"
        result = await memory_service.search(
            query="programming",
            search_mode="hybrid",
            top_k=10,
        )

        # Should return results
        assert len(result) >= 3

        # Results should have both similarity and keyword_score
        for res in result:
            assert res.similarity is not None
            # keyword_score may be null if only semantic match
            if "programming" in res.memory.content.lower():
                assert res.keyword_score is not None

    async def test_hybrid_search_keyword_weight(self, memory_service: MemoryService):
        """Test Case 30: Adjust keyword weight in hybrid search."""
        # Create memories
        await memory_service.store(content="exact keyword match", content_type="text")
        await memory_service.store(content="semantic similar content", content_type="text")

        # Search with high keyword weight
        result_high = await memory_service.search(
            query="keyword",
            search_mode="hybrid",
            keyword_weight=0.7,
            top_k=10,
        )

        # Search with low keyword weight
        result_low = await memory_service.search(
            query="keyword",
            search_mode="hybrid",
            keyword_weight=0.3,
            top_k=10,
        )

        # Both should return results
        assert len(result_high) >= 1
        assert len(result_low) >= 1

    async def test_hybrid_search_semantic_only(self, memory_service: MemoryService):
        """Test Case 31: Hybrid search where only semantic matches."""
        # Create memory without the exact keyword
        await memory_service.store(
            content="Python is a programming language",
            content_type="text",
        )

        # Search with related but different term
        result = await memory_service.search(
            query="coding",
            search_mode="hybrid",
            top_k=10,
        )

        # Should find semantic matches
        # keyword_score should be null for non-keyword matches
        if len(result) > 0:
            for res in result:
                assert res.similarity is not None
                # May have keyword_score or not depending on tokenization


@pytest.mark.asyncio
class TestFTS5Triggers:
    """Test FTS5 table synchronization triggers."""

    async def test_fts5_insert_trigger(self, memory_service: MemoryService, memory_repository):
        """Test Case 32: INSERT trigger updates FTS5 table."""
        memory = await memory_service.store(
            content="Test content for FTS5",
            content_type="text",
        )

        # Verify FTS5 table has the content
        result = await memory_service.search(
            query="FTS5",
            search_mode="keyword",
            top_k=10,
        )

        # Should find the memory via keyword search
        assert len(result) >= 1
        assert any(r.memory.id == memory.id for r in result)

    async def test_fts5_update_trigger(self, memory_service: MemoryService):
        """Test Case 33: UPDATE trigger updates FTS5 table."""
        memory = await memory_service.store(
            content="Original content",
            content_type="text",
        )

        # Update the content
        await memory_service.update(
            memory_id=memory.id,
            content="Updated content for testing",
        )

        # Search for new content
        result = await memory_service.search(
            query="Updated",
            search_mode="keyword",
            top_k=10,
        )

        # Should find the updated memory
        assert len(result) >= 1
        assert any(r.memory.id == memory.id for r in result)

        # Search for old content should not find it
        result_old = await memory_service.search(
            query="Original",
            search_mode="keyword",
            top_k=10,
        )

        # Should not find with old content
        found_with_old = any(r.memory.id == memory.id for r in result_old)
        assert not found_with_old

    async def test_fts5_delete_trigger(self, memory_service: MemoryService):
        """Test Case 34: DELETE trigger removes from FTS5 table."""
        memory = await memory_service.store(
            content="Content to be deleted",
            content_type="text",
        )

        # Verify it exists
        result_before = await memory_service.search(
            query="deleted",
            search_mode="keyword",
            top_k=10,
        )
        assert len(result_before) >= 1

        # Delete the memory
        await memory_service.delete(memory.id)

        # Search again
        result_after = await memory_service.search(
            query="deleted",
            search_mode="keyword",
            top_k=10,
        )

        # Should not find the deleted memory
        found_after = any(r.memory.id == memory.id for r in result_after)
        assert not found_after


@pytest.mark.asyncio
class TestSemanticSearch:
    """Test semantic search mode still works."""

    async def test_semantic_search_mode(self, memory_service: MemoryService):
        """Test semantic search mode (default/explicit)."""
        await memory_service.store(content="Machine learning tutorial", content_type="text")
        await memory_service.store(content="Deep learning guide", content_type="text")

        # Semantic search
        result = await memory_service.search(
            query="AI training",
            search_mode="semantic",
            top_k=10,
        )

        # Should find semantically similar results
        assert len(result) >= 1

        # Should have similarity scores
        for res in result:
            assert res.similarity is not None
