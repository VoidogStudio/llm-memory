"""Context building service for intelligent memory retrieval."""

from typing import Literal

from src.models.context import ContextMemory, ContextResult
from src.models.memory import Memory
from src.services.embedding_service import EmbeddingService
from src.services.graph_traversal_service import GraphTraversalService
from src.services.memory_service import MemoryService
from src.services.semantic_cache import SemanticCache
from src.utils.summarization import extractive_summary_by_tokens
from src.utils.token_counter import get_token_count

Strategy = Literal["relevance", "recency", "importance", "graph"]


class ContextBuildingService:
    """Service for building optimal context within token budget."""

    def __init__(
        self,
        memory_service: MemoryService,
        graph_service: GraphTraversalService,
        cache: SemanticCache,
        embedding_service: EmbeddingService,
        token_buffer_ratio: float = 0.1,
    ) -> None:
        """Initialize context building service.

        Args:
            memory_service: Memory service for searching
            graph_service: Graph traversal service
            cache: Semantic cache
            embedding_service: Embedding service
            token_buffer_ratio: Safety buffer ratio for token budget (0.0-0.3)
        """
        self.memory_service = memory_service
        self.graph_service = graph_service
        self.cache = cache
        self.embedding_service = embedding_service
        self.token_buffer_ratio = token_buffer_ratio

    async def build_context(
        self,
        query: str,
        token_budget: int,
        top_k: int = 20,
        include_related: bool = True,
        max_depth: int = 2,
        auto_summarize: bool = True,
        min_similarity: float = 0.5,
        namespace: str | None = None,
        use_cache: bool = True,
        strategy: Strategy = "relevance",
        link_types: list[str] | None = None,
    ) -> ContextResult:
        """Build optimal context within token budget.

        Args:
            query: Search query
            token_budget: Maximum tokens for context (100-128000)
            top_k: Number of candidate memories (1-100)
            include_related: Include related memories via graph traversal
            max_depth: Maximum traversal depth (1-5)
            auto_summarize: Automatically summarize large memories
            min_similarity: Minimum similarity threshold (0.0-1.0)
            namespace: Target namespace
            use_cache: Use semantic cache
            strategy: Selection strategy
            link_types: Filter by specific link types

        Returns:
            ContextResult with memories and statistics

        Raises:
            ValueError: If parameters are out of valid range
        """
        # Validate parameters
        if not 100 <= token_budget <= 128000:
            raise ValueError("token_budget must be between 100 and 128000")
        if not 1 <= top_k <= 100:
            raise ValueError("top_k must be between 1 and 100")
        if not 1 <= max_depth <= 5:
            raise ValueError("max_depth must be between 1 and 5")
        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between 0.0 and 1.0")

        # Calculate effective token budget (with safety buffer)
        effective_budget = int(token_budget * (1.0 - self.token_buffer_ratio))

        # Check cache if enabled
        if use_cache:
            cached_result, cache_hit = await self.cache.get(query, namespace)
            if cache_hit:
                # Return cached result with cache_hit flag set
                cached_result.cache_hit = True
                return cached_result

        # Fetch direct memories via semantic search
        direct_memories = await self._fetch_direct_memories(
            query, top_k, min_similarity, namespace
        )

        # Fetch related memories if enabled
        related_memories: list[tuple[Memory, int, str | None]] = []
        if include_related and direct_memories:
            direct_ids = [mem.id for mem, _ in direct_memories]
            related_memories = await self._fetch_related_memories(
                direct_ids, max_depth, link_types
            )

        # Merge and deduplicate
        all_memories = self._merge_and_deduplicate(direct_memories, related_memories)

        # Score and sort based on strategy
        sorted_memories = self._score_and_sort(all_memories, strategy)

        # Summarize if needed and auto_summarize is enabled
        if auto_summarize:
            sorted_memories = await self._summarize_if_needed(
                sorted_memories, effective_budget
            )

        # Fit to token budget
        final_memories = self._fit_to_budget(sorted_memories, effective_budget)

        # Calculate statistics
        total_tokens = sum(mem.tokens for mem in final_memories)
        summarized_count = sum(1 for mem in final_memories if mem.summarized)
        related_count = sum(1 for mem in final_memories if mem.source == "related")

        # Create result
        result = ContextResult(
            memories=final_memories,
            total_tokens=total_tokens,
            token_budget=token_budget,
            memories_count=len(final_memories),
            summarized_count=summarized_count,
            related_count=related_count,
            cache_hit=False,
        )

        # Cache result if enabled
        if use_cache:
            await self.cache.put(query, result, namespace)

        return result

    async def _fetch_direct_memories(
        self,
        query: str,
        top_k: int,
        min_similarity: float,
        namespace: str | None,
    ) -> list[tuple[Memory, float]]:
        """Fetch direct memories via semantic search.

        Args:
            query: Search query
            top_k: Number of results
            min_similarity: Minimum similarity
            namespace: Target namespace

        Returns:
            List of (Memory, similarity) tuples
        """
        search_results = await self.memory_service.search(
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
            namespace=namespace,
        )

        return [(result.memory, result.similarity) for result in search_results]

    async def _fetch_related_memories(
        self,
        direct_memory_ids: list[str],
        max_depth: int,
        link_types: list[str] | None,
    ) -> list[tuple[Memory, int, str | None]]:
        """Fetch related memories via graph traversal.

        Args:
            direct_memory_ids: List of direct memory IDs
            max_depth: Maximum traversal depth
            link_types: Filter by specific link types

        Returns:
            List of (Memory, depth, link_type) tuples
        """
        all_related: dict[str, tuple[Memory, int, str | None]] = {}

        for memory_id in direct_memory_ids:
            try:
                traversal_results = await self.graph_service.traverse(
                    start_memory_id=memory_id,
                    max_depth=max_depth,
                    max_results=50,
                    link_types=link_types,
                )

                for memory, node in traversal_results:
                    # Skip direct memories (depth 0)
                    if node.depth == 0:
                        continue

                    # Keep closest depth if duplicate
                    if memory.id not in all_related or node.depth < all_related[memory.id][1]:
                        all_related[memory.id] = (memory, node.depth, node.link_type)

            except ValueError:
                # Memory not found, skip
                continue

        # Exclude direct memories from related
        direct_ids_set = set(direct_memory_ids)
        return [
            (mem, depth, link_type)
            for mem, depth, link_type in all_related.values()
            if mem.id not in direct_ids_set
        ]

    def _merge_and_deduplicate(
        self,
        direct: list[tuple[Memory, float]],
        related: list[tuple[Memory, int, str | None]],
    ) -> list[ContextMemory]:
        """Merge direct and related memories, removing duplicates.

        Args:
            direct: Direct memories with similarity scores
            related: Related memories with depth and link type

        Returns:
            List of ContextMemory objects
        """
        memory_map: dict[str, ContextMemory] = {}

        # Add direct memories
        for memory, similarity in direct:
            tokens = get_token_count(memory.content)
            memory_map[memory.id] = ContextMemory(
                id=memory.id,
                content=memory.content,
                original_tokens=tokens,
                tokens=tokens,
                summarized=False,
                similarity=similarity,
                importance_score=memory.importance_score,
                source="direct",
                depth=0,
                link_type=None,
            )

        # Add related memories (skip if already in direct)
        for memory, depth, link_type in related:
            if memory.id not in memory_map:
                tokens = get_token_count(memory.content)
                memory_map[memory.id] = ContextMemory(
                    id=memory.id,
                    content=memory.content,
                    original_tokens=tokens,
                    tokens=tokens,
                    summarized=False,
                    similarity=0.0,  # No direct similarity for related memories
                    importance_score=memory.importance_score,
                    source="related",
                    depth=depth,
                    link_type=link_type,
                )

        return list(memory_map.values())

    def _score_and_sort(
        self,
        memories: list[ContextMemory],
        strategy: Strategy,
    ) -> list[ContextMemory]:
        """Score and sort memories based on strategy.

        Args:
            memories: List of memories
            strategy: Selection strategy

        Returns:
            Sorted list of memories
        """
        if strategy == "relevance":
            # Sort by similarity (direct) or inverse depth (related)
            return sorted(
                memories,
                key=lambda m: m.similarity if m.source == "direct" else 1.0 / (m.depth + 1),
                reverse=True,
            )
        elif strategy == "recency":
            # LIMITATION: ContextMemory doesn't have created_at field.
            # Falls back to similarity-based sorting as proxy for recency.
            # To enable true recency sorting, add created_at to ContextMemory dataclass.
            return sorted(memories, key=lambda m: m.similarity, reverse=True)
        elif strategy == "importance":
            return sorted(memories, key=lambda m: m.importance_score, reverse=True)
        elif strategy == "graph":
            # Depth first, then similarity
            return sorted(memories, key=lambda m: (m.depth, -m.similarity))
        else:
            return memories

    async def _summarize_if_needed(
        self,
        memories: list[ContextMemory],
        token_budget: int,
    ) -> list[ContextMemory]:
        """Summarize memories if total exceeds budget.

        Args:
            memories: List of memories
            token_budget: Token budget

        Returns:
            List of memories (possibly summarized)
        """
        total_tokens = sum(mem.tokens for mem in memories)

        # If within budget, no summarization needed
        if total_tokens <= token_budget:
            return memories

        # Summarize larger memories first
        sorted_by_size = sorted(memories, key=lambda m: m.tokens, reverse=True)

        for memory in sorted_by_size:
            if total_tokens <= token_budget:
                break

            # Only summarize if memory is large enough (>200 tokens)
            if memory.tokens > 200:
                # Target: reduce to 60% of original (minimum 10% retention)
                target_tokens = max(int(memory.tokens * 0.6), int(memory.original_tokens * 0.1))

                try:
                    summarized_content, _, new_tokens = extractive_summary_by_tokens(
                        memory.content, target_tokens
                    )

                    # Update memory
                    token_reduction = memory.tokens - new_tokens
                    memory.content = summarized_content
                    memory.tokens = new_tokens
                    memory.summarized = True
                    total_tokens -= token_reduction

                except Exception:
                    # Summarization failed, keep original
                    continue

        return memories

    def _fit_to_budget(
        self,
        memories: list[ContextMemory],
        token_budget: int,
    ) -> list[ContextMemory]:
        """Select memories that fit within token budget.

        Args:
            memories: Sorted list of memories
            token_budget: Token budget

        Returns:
            List of memories within budget
        """
        selected: list[ContextMemory] = []
        cumulative_tokens = 0

        for memory in memories:
            if cumulative_tokens + memory.tokens <= token_budget:
                selected.append(memory)
                cumulative_tokens += memory.tokens
            else:
                # Budget exceeded, stop adding
                break

        return selected
