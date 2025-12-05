"""Memory consolidation service."""

import uuid
from datetime import datetime, timezone

from llm_memory.db.repositories.memory_repository import MemoryRepository
from llm_memory.models.memory import Memory, MemoryTier
from llm_memory.services.embedding_service import EmbeddingService
from llm_memory.utils.summarization import extractive_summary


class ConsolidationService:
    """Service for consolidating multiple memories."""

    MIN_MEMORIES: int = 2
    MAX_MEMORIES: int = 50
    MAX_SUMMARY_LENGTH: int = 4000

    def __init__(
        self,
        repository: MemoryRepository,
        embedding_service: EmbeddingService,
    ) -> None:
        """Initialize consolidation service.

        Args:
            repository: Memory repository
            embedding_service: Embedding service
        """
        self.repository = repository
        self.embedding_service = embedding_service

    async def consolidate(
        self,
        memory_ids: list[str],
        summary_strategy: str = "auto",
        preserve_originals: bool = True,
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Consolidate multiple memories into a single summarized memory.

        Args:
            memory_ids: List of memory IDs to consolidate (2-50)
            summary_strategy: Strategy for summarization (auto/extractive)
            preserve_originals: Whether to keep original memories
            tags: Tags for consolidated memory (merges if None)
            metadata: Additional metadata

        Returns:
            Consolidation result with new memory info

        Raises:
            ValueError: If memory count out of range
            NotFoundError: If any memory doesn't exist
            NotImplementedError: If abstractive strategy requested
        """
        # Validation
        if len(memory_ids) < self.MIN_MEMORIES:
            raise ValueError(
                f"At least {self.MIN_MEMORIES} memories required, got {len(memory_ids)}"
            )

        if len(memory_ids) > self.MAX_MEMORIES:
            raise ValueError(
                f"Maximum {self.MAX_MEMORIES} memories allowed, got {len(memory_ids)}"
            )

        if summary_strategy not in ["auto", "extractive", "abstractive"]:
            raise ValueError(
                f"Invalid strategy: {summary_strategy}. "
                f"Must be one of: auto, extractive, abstractive"
            )

        # Fetch memories
        memories = await self._fetch_memories(memory_ids)

        # Combine content
        combined_content = self._combine_content(memories)

        # Summarize
        summarized_content = await self._summarize(combined_content, summary_strategy)

        # Prepare consolidated memory
        now = datetime.now(timezone.utc)

        # Determine tags
        final_tags = tags if tags is not None else self._merge_tags(memories)

        # Prepare metadata
        final_metadata = metadata or {}
        final_metadata.update(
            {
                "consolidated_from": memory_ids,
                "source_count": len(memory_ids),
                "consolidation_strategy": summary_strategy,
                "consolidated_at": now.isoformat(),
            }
        )

        # Create consolidated memory
        consolidated_memory = Memory(
            id=str(uuid.uuid4()),
            content=summarized_content,
            content_type=memories[0].content_type,  # Use first memory's type
            memory_tier=MemoryTier.LONG_TERM,
            tags=final_tags,
            metadata=final_metadata,
            agent_id=memories[0].agent_id,  # Use first memory's agent
            created_at=now,
            updated_at=now,
            consolidated_from=memory_ids,
        )

        # Generate embedding
        embedding = await self.embedding_service.generate(summarized_content)

        # Store consolidated memory
        created_memory = await self.repository.create(consolidated_memory, embedding)

        # Delete originals if requested
        if not preserve_originals:
            await self.repository.delete_many(ids=memory_ids)

        return {
            "consolidated_id": created_memory.id,
            "source_count": len(memory_ids),
            "source_ids": memory_ids,
            "summary_length": len(summarized_content),
            "created_at": created_memory.created_at.isoformat(),
            "preserved_originals": preserve_originals,
        }

    async def _fetch_memories(self, memory_ids: list[str]) -> list[Memory]:
        """Fetch and validate all memories.

        Args:
            memory_ids: List of memory IDs

        Returns:
            List of Memory objects

        Raises:
            NotFoundError: If any memory doesn't exist
        """
        from llm_memory.exceptions import NotFoundError

        memories = []
        for memory_id in memory_ids:
            memory = await self.repository.find_by_id(memory_id)
            if memory is None:
                raise NotFoundError(f"Memory not found: {memory_id}")
            memories.append(memory)

        return memories

    def _combine_content(self, memories: list[Memory]) -> str:
        """Combine memory contents with separators.

        Args:
            memories: List of memories

        Returns:
            Combined content string
        """
        return "\n\n---\n\n".join([m.content for m in memories])

    def _merge_tags(self, memories: list[Memory]) -> list[str]:
        """Merge tags from all memories (deduplicated).

        Args:
            memories: List of memories

        Returns:
            Merged tags list
        """
        all_tags: set[str] = set()
        for m in memories:
            all_tags.update(m.tags)
        return sorted(all_tags)

    async def _summarize(
        self,
        text: str,
        strategy: str,
    ) -> str:
        """Generate summary based on strategy.

        Args:
            text: Text to summarize
            strategy: Summary strategy (auto/extractive/abstractive)

        Returns:
            Summarized text

        Raises:
            NotImplementedError: If abstractive requested
        """
        if strategy == "abstractive":
            raise NotImplementedError(
                "Abstractive summarization requires external LLM API. "
                "This feature will be available in v1.2.0"
            )

        # auto or extractive
        if len(text) <= self.MAX_SUMMARY_LENGTH:
            return text

        return extractive_summary(text, self.MAX_SUMMARY_LENGTH)
