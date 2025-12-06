"""Similarity and deduplication MCP tools."""

from typing import Any

from src.services.lsh_index import LSH_AVAILABLE
from src.services.memory_service import MemoryService
from src.tools import create_error_response


async def memory_similar(
    service: MemoryService,
    id: str,
    top_k: int = 10,
    min_similarity: float = 0.7,
    namespace: str | None = None,
    search_scope: str = "current",
    exclude_linked: bool = True,
) -> dict[str, Any]:
    """Find memories similar to a specified memory.

    Args:
        service: Memory service instance
        id: Base memory ID to find similar memories for
        top_k: Maximum number of results to return (1-1000)
        min_similarity: Minimum similarity threshold (0.0-1.0)
        namespace: Target namespace (default: auto-detect)
        search_scope: Search scope (current/shared/all)
        exclude_linked: Exclude already linked memories

    Returns:
        Similar memories with similarity scores
    """
    # Parameter validation
    if top_k < 1 or top_k > 1000:
        return create_error_response(
            message="top_k must be between 1 and 1000",
            error_type="ValidationError",
        )

    if min_similarity < 0.0 or min_similarity > 1.0:
        return create_error_response(
            message="min_similarity must be between 0.0 and 1.0",
            error_type="ValidationError",
        )

    if search_scope not in ("current", "shared", "all"):
        return create_error_response(
            message="search_scope must be one of: current, shared, all",
            error_type="ValidationError",
        )

    # Resolve namespace
    namespace = await service.namespace_service.resolve_namespace(namespace)

    # Get base memory
    base_memory = await service.get(id, namespace=namespace)
    if not base_memory:
        return create_error_response(
            message=f"Memory not found: {id}",
            error_type="NotFoundError",
        )

    # Find similar memories
    try:
        similar_results = await service.repository.find_similar_memories(
            memory_id=id,
            top_k=top_k,
            min_similarity=min_similarity,
            namespace=namespace,
            search_scope=search_scope,
            exclude_linked=exclude_linked,
        )

        # Format response
        similar_memories = []
        for result in similar_results:
            similar_memories.append(
                {
                    "id": result.memory.id,
                    "content": result.memory.content,
                    "similarity": result.similarity,
                    "namespace": result.memory.namespace,
                    "is_linked": False,  # Will be updated if we have linking info
                }
            )

        return {
            "base_memory_id": id,
            "similar_memories": similar_memories,
            "total_found": len(similar_memories),
            "returned": len(similar_memories),
        }

    except Exception as e:
        return create_error_response(
            message=f"Error finding similar memories: {str(e)}",
            error_type="RuntimeError",
        )


async def memory_deduplicate(
    service: MemoryService,
    namespace: str | None = None,
    similarity_threshold: float = 0.95,
    dry_run: bool = True,
    merge_strategy: str = "keep_newest",
    merge_metadata: bool = True,
    limit: int = 1000,
    use_lsh: bool = True,
) -> dict[str, Any]:
    """Detect and optionally merge duplicate memories.

    Args:
        service: Memory service instance
        namespace: Target namespace (default: auto-detect)
        similarity_threshold: Similarity threshold for duplicates (0.0-1.0)
        dry_run: Preview mode without actual deletion (default: True)
        merge_strategy: Strategy for choosing primary (keep_newest/keep_oldest/highest_importance)
        merge_metadata: Merge metadata from duplicates into primary
        limit: Maximum memories to process (1-10000)
        use_lsh: Use LSH optimization for faster duplicate detection

    Returns:
        Duplicate groups and merge results
    """
    # Parameter validation
    if similarity_threshold < 0.0 or similarity_threshold > 1.0:
        return create_error_response(
            message="similarity_threshold must be between 0.0 and 1.0",
            error_type="ValidationError",
        )

    if merge_strategy not in ("keep_newest", "keep_oldest", "highest_importance"):
        return create_error_response(
            message="merge_strategy must be one of: keep_newest, keep_oldest, highest_importance",
            error_type="ValidationError",
        )

    if limit < 1 or limit > 10000:
        return create_error_response(
            message="limit must be between 1 and 10000",
            error_type="ValidationError",
        )

    # Resolve namespace
    namespace = await service.namespace_service.resolve_namespace(namespace)

    # Check LSH availability
    if use_lsh and not LSH_AVAILABLE:
        use_lsh = False

    try:
        # Find duplicates
        duplicate_groups = await service.repository.find_duplicates(
            namespace=namespace,
            similarity_threshold=similarity_threshold,
            limit=limit,
            use_lsh=use_lsh,
        )

        total_duplicates = sum(len(group["duplicate_ids"]) for group in duplicate_groups)

        # If not dry_run, perform merges
        merged_count = 0
        if not dry_run and duplicate_groups:
            for group in duplicate_groups:
                try:
                    # Get all memories in group
                    all_ids = [group["primary_id"]] + group["duplicate_ids"]
                    memories = []
                    for mem_id in all_ids:
                        mem = await service.get(mem_id, namespace=namespace)
                        if mem:
                            memories.append(mem)

                    if len(memories) < 2:
                        continue

                    # Determine primary based on strategy
                    if merge_strategy == "keep_newest":
                        primary = max(memories, key=lambda m: m.created_at)
                    elif merge_strategy == "keep_oldest":
                        primary = min(memories, key=lambda m: m.created_at)
                    else:  # highest_importance
                        primary = max(memories, key=lambda m: m.importance_score)

                    # Get duplicates (all except primary)
                    duplicates = [m for m in memories if m.id != primary.id]

                    # Merge metadata if requested
                    if merge_metadata:
                        for dup in duplicates:
                            # Merge tags
                            primary.tags = list(set(primary.tags + dup.tags))
                            # Merge metadata
                            primary.metadata.update(dup.metadata)

                        # Update primary memory
                        await service.update(
                            primary.id,
                            tags=primary.tags,
                            metadata=primary.metadata,
                            namespace=namespace,
                        )

                    # Delete duplicates
                    for dup in duplicates:
                        await service.delete([dup.id], namespace=namespace)
                        merged_count += 1

                except Exception:
                    # Log error but continue with other groups
                    continue

        return {
            "duplicate_groups": duplicate_groups,
            "total_groups": len(duplicate_groups),
            "total_duplicates": total_duplicates,
            "merged": merged_count if not dry_run else 0,
            "dry_run": dry_run,
            "algorithm": "lsh" if use_lsh else "brute_force",
        }

    except Exception as e:
        return create_error_response(
            message=f"Error detecting duplicates: {str(e)}",
            error_type="RuntimeError",
        )
