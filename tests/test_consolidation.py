"""Tests for FR-001: Memory Consolidation."""

import pytest

from llm_memory.exceptions import NotFoundError
from llm_memory.services.consolidation_service import ConsolidationService
from llm_memory.services.memory_service import MemoryService


@pytest.mark.asyncio
class TestMemoryConsolidate:
    """Test memory_consolidate functionality."""

    async def test_consolidate_basic(
        self, memory_service: MemoryService, memory_repository, embedding_service
    ):
        """Test Case 35: Basic memory consolidation."""
        # Create 3 memories
        mem1 = await memory_service.store(
            content="Python is a programming language.",
            content_type="text",
            tags=["python", "programming"],
        )
        mem2 = await memory_service.store(
            content="Python is used for web development.",
            content_type="text",
            tags=["python", "web"],
        )
        mem3 = await memory_service.store(
            content="Python has excellent data science libraries.",
            content_type="text",
            tags=["python", "data"],
        )

        # Consolidate
        consolidation_service = ConsolidationService(
            repository=memory_repository,
            embedding_service=embedding_service,
        )

        result = await consolidation_service.consolidate(
            memory_ids=[mem1.id, mem2.id, mem3.id]
        )

        assert result["consolidated_id"] is not None
        assert result["source_count"] == 3
        assert set(result["source_ids"]) == {mem1.id, mem2.id, mem3.id}

        # Verify consolidated memory exists
        consolidated = await memory_service.get(result["consolidated_id"])
        assert consolidated is not None
        assert "Python" in consolidated.content
        assert consolidated.consolidated_from is not None

    async def test_consolidate_merge_tags(
        self, memory_service: MemoryService, memory_repository, embedding_service
    ):
        """Test Case 36: Tag merging during consolidation."""
        mem1 = await memory_service.store(
            content="Memory A",
            content_type="text",
            tags=["a", "b"],
        )
        mem2 = await memory_service.store(
            content="Memory B",
            content_type="text",
            tags=["b", "c"],
        )

        consolidation_service = ConsolidationService(
            repository=memory_repository,
            embedding_service=embedding_service,
        )

        result = await consolidation_service.consolidate(
            memory_ids=[mem1.id, mem2.id],
            tags=None,  # Auto-merge
        )

        # Verify merged tags
        consolidated = await memory_service.get(result["consolidated_id"])
        assert set(consolidated.tags) == {"a", "b", "c"}

    async def test_consolidate_custom_tags(
        self, memory_service: MemoryService, memory_repository, embedding_service
    ):
        """Test Case 37: Custom tags for consolidation."""
        mem1 = await memory_service.store(content="Memory 1", content_type="text", tags=["old"])
        mem2 = await memory_service.store(content="Memory 2", content_type="text", tags=["old"])

        consolidation_service = ConsolidationService(
            repository=memory_repository,
            embedding_service=embedding_service,
        )

        result = await consolidation_service.consolidate(
            memory_ids=[mem1.id, mem2.id],
            tags=["custom", "new"],
        )

        # Verify custom tags
        consolidated = await memory_service.get(result["consolidated_id"])
        assert set(consolidated.tags) == {"custom", "new"}
        assert "old" not in consolidated.tags

    async def test_consolidate_delete_originals(
        self, memory_service: MemoryService, memory_repository, embedding_service
    ):
        """Test Case 38: Delete original memories after consolidation."""
        mem1 = await memory_service.store(content="Memory 1", content_type="text")
        mem2 = await memory_service.store(content="Memory 2", content_type="text")
        mem3 = await memory_service.store(content="Memory 3", content_type="text")

        consolidation_service = ConsolidationService(
            repository=memory_repository,
            embedding_service=embedding_service,
        )

        result = await consolidation_service.consolidate(
            memory_ids=[mem1.id, mem2.id, mem3.id],
            preserve_originals=False,
        )

        # Verify originals are deleted (get() returns None for deleted memories)
        deleted_mem1 = await memory_service.get(mem1.id)
        assert deleted_mem1 is None

        deleted_mem2 = await memory_service.get(mem2.id)
        assert deleted_mem2 is None

        deleted_mem3 = await memory_service.get(mem3.id)
        assert deleted_mem3 is None

        # Consolidated memory should exist
        consolidated = await memory_service.get(result["consolidated_id"])
        assert consolidated is not None

    async def test_consolidate_short_content(
        self, memory_service: MemoryService, memory_repository, embedding_service
    ):
        """Test Case 39: Short content doesn't require summarization."""
        mem1 = await memory_service.store(content="Short text A", content_type="text")
        mem2 = await memory_service.store(content="Short text B", content_type="text")

        consolidation_service = ConsolidationService(
            repository=memory_repository,
            embedding_service=embedding_service,
        )

        result = await consolidation_service.consolidate(
            memory_ids=[mem1.id, mem2.id],
            summary_strategy="auto",
        )

        # Should concatenate without summarization
        consolidated = await memory_service.get(result["consolidated_id"])
        assert "Short text A" in consolidated.content or "Short text B" in consolidated.content

    async def test_consolidate_long_content(
        self, memory_service: MemoryService, memory_repository, embedding_service
    ):
        """Test Case 40: Long content triggers summarization."""
        # Create long content (> 5000 chars)
        long_text = " ".join([f"Sentence {i}." for i in range(1000)])

        mem1 = await memory_service.store(content=long_text, content_type="text")
        mem2 = await memory_service.store(content=long_text, content_type="text")

        consolidation_service = ConsolidationService(
            repository=memory_repository,
            embedding_service=embedding_service,
        )

        result = await consolidation_service.consolidate(
            memory_ids=[mem1.id, mem2.id],
            summary_strategy="auto",
        )

        # Should summarize
        consolidated = await memory_service.get(result["consolidated_id"])
        # Summary should be shorter than combined original
        assert len(consolidated.content) < len(long_text) * 2


@pytest.mark.asyncio
class TestConsolidationValidation:
    """Test consolidation validation rules."""

    async def test_consolidate_single_memory(
        self, memory_service: MemoryService, memory_repository, embedding_service
    ):
        """Test Case 41: Reject consolidation with only 1 memory."""
        mem1 = await memory_service.store(content="Single memory", content_type="text")

        consolidation_service = ConsolidationService(
            repository=memory_repository,
            embedding_service=embedding_service,
        )

        with pytest.raises(ValueError) as exc_info:
            await consolidation_service.consolidate(memory_ids=[mem1.id])

        assert "minimum" in str(exc_info.value).lower() or "at least 2" in str(
            exc_info.value
        ).lower()

    async def test_consolidate_exceeds_maximum(
        self, memory_service: MemoryService, memory_repository, embedding_service
    ):
        """Test Case 42: Reject consolidation exceeding 50 memories."""
        # Create 51 memories
        memory_ids = []
        for i in range(51):
            mem = await memory_service.store(content=f"Memory {i}", content_type="text")
            memory_ids.append(mem.id)

        consolidation_service = ConsolidationService(
            repository=memory_repository,
            embedding_service=embedding_service,
        )

        with pytest.raises(ValueError) as exc_info:
            await consolidation_service.consolidate(memory_ids=memory_ids)

        assert "maximum" in str(exc_info.value).lower() or "50" in str(exc_info.value)

    async def test_consolidate_nonexistent_id(
        self, memory_service: MemoryService, memory_repository, embedding_service
    ):
        """Test Case 43: Handle nonexistent memory IDs."""
        mem1 = await memory_service.store(content="Memory 1", content_type="text")

        consolidation_service = ConsolidationService(
            repository=memory_repository,
            embedding_service=embedding_service,
        )

        with pytest.raises(NotFoundError):
            await consolidation_service.consolidate(
                memory_ids=[mem1.id, "nonexistent-id-12345"]
            )

    async def test_consolidate_abstractive_not_implemented(
        self, memory_service: MemoryService, memory_repository, embedding_service
    ):
        """Test Case 44: Abstractive strategy not yet implemented."""
        mem1 = await memory_service.store(content="Memory 1", content_type="text")
        mem2 = await memory_service.store(content="Memory 2", content_type="text")

        consolidation_service = ConsolidationService(
            repository=memory_repository,
            embedding_service=embedding_service,
        )

        with pytest.raises(NotImplementedError):
            await consolidation_service.consolidate(
                memory_ids=[mem1.id, mem2.id],
                summary_strategy="abstractive",
            )


@pytest.mark.asyncio
class TestExtractiveSummarization:
    """Test extractive summarization algorithm."""

    async def test_extractive_summary_sentence_selection(self):
        """Test Case 45: Sentence selection in extractive summary."""
        from llm_memory.utils.summarization import extractive_summary

        # Create text with repeated important words
        text = """
        Python is a programming language. Python is widely used.
        The weather is nice today. Python has many libraries.
        Random sentence here. Python is popular for data science.
        Another random sentence. Python is easy to learn.
        Some other content here. Python programming is fun.
        """

        summary = extractive_summary(text, max_length=200)

        # Summary should contain sentences with "Python"
        assert "Python" in summary
        # Summary should be shorter than original
        assert len(summary) < len(text)

    async def test_extractive_summary_order_preserved(self):
        """Test Case 45: Original sentence order is preserved."""
        from llm_memory.utils.summarization import extractive_summary

        text = """First sentence. Second sentence is important and contains key terms.
        Third sentence here. Fourth sentence also has important key terms."""

        summary = extractive_summary(text, max_length=500)

        # If both important sentences are selected, they should maintain order
        if "Second" in summary and "Fourth" in summary:
            assert summary.index("Second") < summary.index("Fourth")

    async def test_sentence_scoring(self):
        """Test Case 46: Sentence scoring based on word frequency."""
        from llm_memory.utils.summarization import calculate_word_frequency, score_sentence

        text = "python programming language python code python developer"
        word_freq = calculate_word_frequency(text)

        # "python" should have high frequency
        assert word_freq.get("python", 0) > word_freq.get("language", 0)

        # Sentence with more frequent words should score higher
        sentence1 = "python python python"
        sentence2 = "language code developer"

        score1 = score_sentence(sentence1, word_freq)
        score2 = score_sentence(sentence2, word_freq)

        assert score1 > score2
