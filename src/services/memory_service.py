"""Memory service for business logic."""

from datetime import datetime, timedelta, timezone
from typing import Any

from src.config import get_settings
from src.db.repositories.memory_repository import MemoryRepository
from src.models.memory import (
    ContentType,
    Memory,
    MemoryTier,
    SearchResult,
)
from src.services.embedding_service import EmbeddingService
from src.services.namespace_service import NamespaceService
from src.services.tokenization_service import TokenizationService


class MemoryService:
    """Service for memory operations."""

    def __init__(
        self,
        repository: MemoryRepository,
        embedding_service: EmbeddingService,
        namespace_service: NamespaceService,
    ) -> None:
        """Initialize memory service.

        Args:
            repository: Memory repository
            embedding_service: Embedding service
            namespace_service: Namespace service
        """
        self.repository = repository
        self.embedding_service = embedding_service
        self.namespace_service = namespace_service

    async def store(
        self,
        content: str,
        content_type: ContentType = ContentType.TEXT,
        memory_tier: MemoryTier = MemoryTier.LONG_TERM,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        agent_id: str | None = None,
        ttl_seconds: int | None = None,
        namespace: str | None = None,
    ) -> Memory:
        """Store a new memory entry.

        Args:
            content: Memory content
            content_type: Content type
            memory_tier: Memory tier
            tags: Tags for categorization
            metadata: Additional metadata
            agent_id: Agent ID
            ttl_seconds: Time-to-live in seconds
            namespace: Target namespace

        Returns:
            Created memory object
        """
        # Resolve namespace
        explicit_namespace = namespace
        namespace = await self.namespace_service.resolve_namespace(namespace)
        self.namespace_service.validate_shared_write(namespace, explicit_namespace is not None)

        # Create memory object
        now = datetime.now(timezone.utc)
        expires_at = None

        if ttl_seconds:
            expires_at = now + timedelta(seconds=ttl_seconds)

        memory = Memory(
            content=content,
            content_type=content_type,
            memory_tier=memory_tier,
            tags=tags or [],
            metadata=metadata or {},
            agent_id=agent_id,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            namespace=namespace,
        )

        # Generate embedding
        embedding = await self.embedding_service.generate(content)

        # Store in repository
        return await self.repository.create(memory, embedding)

    async def search(
        self,
        query: str,
        top_k: int = 10,
        memory_tier: MemoryTier | None = None,
        tags: list[str] | None = None,
        content_type: str | None = None,
        min_similarity: float = 0.0,
        search_mode: str = "semantic",
        keyword_weight: float = 0.3,
        sort_by: str = "similarity",
        importance_weight: float = 0.3,
        namespace: str | None = None,
        search_scope: str = "current",
    ) -> list[SearchResult]:
        """Search memories using semantic similarity, keyword, or hybrid search.

        Args:
            query: Search query
            top_k: Number of results
            memory_tier: Filter by tier
            tags: Filter by tags
            content_type: Filter by content type
            min_similarity: Minimum similarity threshold
            search_mode: Search mode (semantic/keyword/hybrid)
            keyword_weight: Weight for keyword scores in hybrid mode
            sort_by: Sort by (similarity/importance/combined)
            importance_weight: Weight for importance in combined sort

        Returns:
            List of search results
        """
        # Resolve namespace for all search modes
        resolved_namespace = await self.namespace_service.resolve_namespace(namespace)

        # Generate query embedding (use is_query=True for search queries)
        embedding = await self.embedding_service.generate(query, is_query=True)

        # Perform search based on mode
        if search_mode == "hybrid":
            tokenizer = TokenizationService()
            tokenized_query = tokenizer.tokenize_query(query)

            results = await self.repository.hybrid_search(
                query=tokenized_query,
                embedding=embedding,
                top_k=top_k,
                keyword_weight=keyword_weight,
                memory_tier=memory_tier,
                tags=tags,
                content_type=content_type,
                namespace=resolved_namespace,
                search_scope=search_scope,
            )
        elif search_mode == "keyword":
            tokenizer = TokenizationService()
            tokenized_query = tokenizer.tokenize_query(query)

            keyword_tuples = await self.repository.keyword_search(
                query=tokenized_query,
                top_k=top_k,
                memory_tier=memory_tier,
                tags=tags,
                content_type=content_type,
                namespace=resolved_namespace,
                search_scope=search_scope,
            )

            # Convert to SearchResult
            results = []
            for memory_id, score in keyword_tuples:
                memory = await self.repository.find_by_id(memory_id)
                if memory:
                    results.append(
                        SearchResult(
                            memory=memory,
                            similarity=0.0,
                            keyword_score=abs(score),
                        )
                    )
        else:  # semantic (default)
            results = await self.repository.vector_search(
                embedding=embedding,
                top_k=top_k,
                memory_tier=memory_tier,
                tags=tags,
                content_type=content_type,
                namespace=resolved_namespace,
                search_scope=search_scope,
            )

        # Filter by minimum similarity (only for semantic/hybrid)
        if min_similarity > 0.0 and search_mode in ["semantic", "hybrid"]:
            results = [r for r in results if r.similarity >= min_similarity]

        # Sort results
        if sort_by == "importance":
            results.sort(key=lambda x: x.memory.importance_score, reverse=True)
        elif sort_by == "combined":
            # Combined score: weighted combination of similarity and importance
            for result in results:
                primary_score = result.combined_score or result.similarity
                combined = (
                    (1.0 - importance_weight) * primary_score
                    + importance_weight * result.memory.importance_score
                )
                result.combined_score = combined
            results.sort(key=lambda x: x.combined_score or 0.0, reverse=True)

        return results

    async def get(self, memory_id: str, namespace: str | None = None) -> Memory | None:
        """Get memory by ID.

        Args:
            memory_id: Memory ID
            namespace: Namespace for validation (optional)

        Returns:
            Memory object or None if not found
        """
        memory = await self.repository.find_by_id(memory_id)

        # Log access for importance scoring (this also updates access_count and last_accessed_at)
        if memory:
            await self.repository.log_access(memory.id, 'get')
            # Re-fetch to get updated access_count and last_accessed_at
            memory = await self.repository.find_by_id(memory_id)

        return memory

    async def update(
        self,
        memory_id: str,
        content: str | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        memory_tier: MemoryTier | None = None,
    ) -> Memory | None:
        """Update memory entry.

        Args:
            memory_id: Memory ID
            content: New content
            tags: New tags
            metadata: New metadata
            memory_tier: New tier

        Returns:
            Updated memory or None if not found
        """
        updates = {}

        if content is not None:
            updates["content"] = content

        if tags is not None:
            updates["tags"] = tags

        if metadata is not None:
            updates["metadata"] = metadata

        if memory_tier is not None:
            updates["memory_tier"] = memory_tier

        # Update memory first
        memory = await self.repository.update(memory_id, updates)

        # If content changed, regenerate and update embedding
        if content is not None and memory is not None:
            new_embedding = await self.embedding_service.generate(content)
            # Update embedding in repository
            await self.repository.update_embedding(memory_id, new_embedding)

        return memory

    async def delete(
        self,
        memory_id: str | None = None,
        ids: list[str] | None = None,
        memory_tier: MemoryTier | None = None,
        older_than: datetime | None = None,
    ) -> list[str]:
        """Delete memories.

        Args:
            memory_id: Single memory ID
            ids: List of memory IDs
            memory_tier: Delete by tier
            older_than: Delete older than datetime

        Returns:
            List of deleted IDs
        """
        if memory_id:
            deleted = await self.repository.delete(memory_id)
            return [memory_id] if deleted else []

        if ids or memory_tier or older_than:
            return await self.repository.delete_many(
                ids=ids, memory_tier=memory_tier, older_than=older_than
            )

        return []

    async def list_memories(
        self,
        memory_tier: MemoryTier | None = None,
        tags: list[str] | None = None,
        content_type: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Memory], int]:
        """List memories with filters.

        Args:
            memory_tier: Filter by tier
            tags: Filter by tags
            content_type: Filter by content type
            created_after: Created after datetime
            created_before: Created before datetime
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (memories list, total count)
        """
        return await self.repository.find_by_filters(
            memory_tier=memory_tier,
            tags=tags,
            content_type=content_type,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            offset=offset,
        )

    async def cleanup_expired(self) -> int:
        """Clean up expired memories.

        Returns:
            Number of deleted memories
        """
        return await self.repository.cleanup_expired()

    def _create_memory_from_item(
        self,
        item: dict[str, Any],
        resolved_namespace: str,
    ) -> Memory:
        """Create Memory object from batch item.

        Args:
            item: Dictionary containing memory parameters
            resolved_namespace: Resolved namespace for the memory

        Returns:
            Memory object ready to be stored
        """
        now = datetime.now(timezone.utc)
        ttl_seconds = item.get("ttl_seconds")
        expires_at = now + timedelta(seconds=ttl_seconds) if ttl_seconds else None

        return Memory(
            content=item["content"],
            content_type=ContentType(item.get("content_type", "text")),
            memory_tier=MemoryTier(item.get("memory_tier", "long_term")),
            tags=item.get("tags", []),
            metadata=item.get("metadata", {}),
            agent_id=item.get("agent_id"),
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            namespace=resolved_namespace,
        )

    def _build_update_dict(self, update: dict[str, Any]) -> dict[str, Any]:
        """Build update dictionary from raw update parameters.

        Args:
            update: Dictionary containing update parameters

        Returns:
            Dictionary with validated update fields
        """
        update_dict: dict[str, Any] = {}

        if "content" in update:
            update_dict["content"] = update["content"]

        if "tags" in update:
            update_dict["tags"] = update["tags"]

        if "metadata" in update:
            update_dict["metadata"] = update["metadata"]

        if "memory_tier" in update:
            update_dict["memory_tier"] = MemoryTier(update["memory_tier"])

        return update_dict

    async def batch_store(
        self,
        items: list[dict[str, Any]],
        on_error: str = "rollback",
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Store multiple memories with batch embedding generation.

        Args:
            items: List of memory parameters
            on_error: Error handling (rollback/continue/stop)
            namespace: Target namespace for all items

        Returns:
            {success_count, error_count, created_ids, errors}

        Raises:
            ValueError: If items exceeds configured batch_max_size or is empty
        """
        settings = get_settings()
        max_batch_size = settings.batch_max_size

        if len(items) > max_batch_size:
            raise ValueError(
                f"Batch size exceeds maximum of {max_batch_size}, got {len(items)}"
            )

        if not items:
            raise ValueError("Items list cannot be empty or must contain at least 1 item")

        # Resolve namespace once for the batch
        explicit_namespace = namespace
        resolved_namespace = await self.namespace_service.resolve_namespace(namespace)
        self.namespace_service.validate_shared_write(resolved_namespace, explicit_namespace is not None)

        # Extract contents for batch embedding
        contents = [item.get("content", "") for item in items]

        # Validate all items upfront before processing
        validation_error = None
        for i, item in enumerate(items):
            # Validate required content field
            if not item.get("content"):
                if on_error == "rollback":
                    validation_error = ValueError(f"Item at index {i} missing required field: content")
                    break

            # Validate content_type enum if provided
            if "content_type" in item:
                try:
                    ContentType(item["content_type"])
                except ValueError:
                    if on_error == "rollback":
                        validation_error = ValueError(
                            f"Item at index {i} has invalid content_type: {item['content_type']}"
                        )
                        break

            # Validate memory_tier enum if provided
            if "memory_tier" in item:
                try:
                    MemoryTier(item["memory_tier"])
                except ValueError:
                    if on_error == "rollback":
                        validation_error = ValueError(
                            f"Item at index {i} has invalid memory_tier: {item['memory_tier']}"
                        )
                        break

        # If validation failed in rollback mode, return error result
        if validation_error and on_error == "rollback":
            return {
                "success_count": 0,
                "error_count": 1,
                "created_ids": [],
                "errors": [{"index": 0, "error": str(validation_error)}],
            }

        # Generate embeddings in batch
        embeddings = await self.embedding_service.generate_batch(contents)

        # Process each item based on on_error mode
        created_ids = []
        errors = []

        if on_error == "rollback":
            # Rollback mode: Use transaction, fail on first error
            try:
                async with self.repository.db.transaction():
                    for item, embedding in zip(items, embeddings, strict=True):
                        memory = self._create_memory_from_item(item, resolved_namespace)
                        created = await self.repository.create(
                            memory, embedding, use_transaction=False
                        )
                        created_ids.append(created.id)

            except Exception:
                # Rollback happens automatically, re-raise the error
                raise

        elif on_error == "stop":
            # Stop mode: Use transaction, stop on first error but return partial results
            try:
                async with self.repository.db.transaction():
                    for i, (item, embedding) in enumerate(
                        zip(items, embeddings, strict=True)
                    ):
                        try:
                            memory = self._create_memory_from_item(item, resolved_namespace)
                            created = await self.repository.create(
                                memory, embedding, use_transaction=False
                            )
                            created_ids.append(created.id)

                        except Exception as e:
                            error_info = {"index": i, "error": str(e)}
                            errors.append(error_info)
                            # Stop processing and commit what we have so far
                            break

            except Exception:
                # If transaction itself fails, rollback
                raise

        else:  # continue
            # Continue mode: Use transaction, continue on errors
            async with self.repository.db.transaction():
                for i, (item, embedding) in enumerate(zip(items, embeddings, strict=True)):
                    try:
                        memory = self._create_memory_from_item(item, resolved_namespace)
                        created = await self.repository.create(
                            memory, embedding, use_transaction=False
                        )
                        created_ids.append(created.id)

                    except Exception as e:
                        error_info = {"index": i, "error": str(e)}
                        errors.append(error_info)
                        # Continue processing remaining items

        return {
            "success_count": len(created_ids),
            "error_count": len(errors),
            "created_ids": created_ids,
            "errors": errors,
        }

    async def batch_update(
        self,
        updates: list[dict[str, Any]],
        on_error: str = "rollback",
    ) -> dict[str, Any]:
        """Update multiple memories with batch embedding regeneration.

        Args:
            updates: List of {id: str, ...update fields}
            on_error: Error handling (rollback/continue/stop)

        Returns:
            {success_count, error_count, updated_ids, errors}

        Raises:
            ValueError: If updates exceeds configured batch_max_size or is empty
        """
        settings = get_settings()
        max_batch_size = settings.batch_max_size

        if len(updates) > max_batch_size:
            raise ValueError(
                f"Batch size exceeds maximum of {max_batch_size}, got {len(updates)}"
            )

        if not updates:
            raise ValueError("Updates list cannot be empty or must contain at least 1 item")

        # Identify which items need embedding regeneration
        needs_embedding = []
        for i, update in enumerate(updates):
            if "content" in update and update["content"]:
                needs_embedding.append((i, update["content"]))

        # Generate embeddings for changed content
        embedding_map = {}
        if needs_embedding:
            indices, contents = zip(*needs_embedding, strict=True)
            embeddings = await self.embedding_service.generate_batch(list(contents))
            embedding_map = dict(zip(indices, embeddings, strict=True))

        # Process each update based on on_error mode
        updated_ids = []
        errors = []

        if on_error == "rollback":
            # Rollback mode: Use transaction, fail on first error
            try:
                async with self.repository.db.transaction():
                    for i, update in enumerate(updates):
                        memory_id = update.get("id")
                        if not memory_id:
                            raise ValueError(
                                f"Update at index {i} missing required field: id"
                            )

                        update_dict = self._build_update_dict(update)
                        memory = await self.repository.update(
                            memory_id, update_dict, use_transaction=False
                        )

                        if memory is None:
                            raise ValueError(f"Memory not found: {memory_id}")

                        if i in embedding_map:
                            await self.repository.update_embedding(
                                memory_id, embedding_map[i]
                            )

                        updated_ids.append(memory_id)

            except Exception:
                # Rollback happens automatically, re-raise the error
                raise

        elif on_error == "stop":
            # Stop mode: Use transaction, stop on first error but return partial results
            try:
                async with self.repository.db.transaction():
                    for i, update in enumerate(updates):
                        try:
                            memory_id = update.get("id")
                            if not memory_id:
                                raise ValueError(
                                    f"Update at index {i} missing required field: id"
                                )

                            update_dict = self._build_update_dict(update)
                            memory = await self.repository.update(memory_id, update_dict)

                            if memory is None:
                                raise ValueError(f"Memory not found: {memory_id}")

                            if i in embedding_map:
                                await self.repository.update_embedding(
                                    memory_id, embedding_map[i]
                                )

                            updated_ids.append(memory_id)

                        except Exception as e:
                            error_info = {
                                "id": update.get("id", f"index_{i}"),
                                "error": str(e),
                            }
                            errors.append(error_info)
                            # Stop processing and commit what we have so far
                            break

            except Exception:
                # If transaction itself fails, rollback
                raise

        else:  # continue
            # Continue mode: Use transaction, continue on errors
            async with self.repository.db.transaction():
                for i, update in enumerate(updates):
                    try:
                        memory_id = update.get("id")
                        if not memory_id:
                            raise ValueError(
                                f"Update at index {i} missing required field: id"
                            )

                        update_dict = self._build_update_dict(update)
                        memory = await self.repository.update(
                            memory_id, update_dict, use_transaction=False
                        )

                        if memory is None:
                            raise ValueError(f"Memory not found: {memory_id}")

                        if i in embedding_map:
                            await self.repository.update_embedding(
                                memory_id, embedding_map[i]
                            )

                        updated_ids.append(memory_id)

                    except Exception as e:
                        error_info = {"id": update.get("id", f"index_{i}"), "error": str(e)}
                        errors.append(error_info)
                        # Continue processing remaining items

        return {
            "success_count": len(updated_ids),
            "error_count": len(errors),
            "updated_ids": updated_ids,
            "errors": errors,
        }
