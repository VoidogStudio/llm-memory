"""Memory consolidation MCP tools."""

from typing import Any

from llm_memory.services.consolidation_service import ConsolidationService
from llm_memory.tools import create_error_response


async def memory_consolidate(
    service: ConsolidationService,
    memory_ids: list[str],
    summary_strategy: str = "auto",
    preserve_originals: bool = True,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Consolidate multiple memories into a single summarized memory.

    Args:
        service: Consolidation service instance
        memory_ids: List of memory IDs to consolidate (2-50)
        summary_strategy: Summarization strategy (auto/extractive)
        preserve_originals: Keep original memories (default True)
        tags: Tags for consolidated memory
        metadata: Additional metadata

    Returns:
        Consolidation result
    """
    try:
        result = await service.consolidate(
            memory_ids=memory_ids,
            summary_strategy=summary_strategy,
            preserve_originals=preserve_originals,
            tags=tags,
            metadata=metadata,
        )
        return result
    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
            details={
                "memory_ids": memory_ids,
                "count": len(memory_ids),
                "strategy": summary_strategy,
            },
        )
    except NotImplementedError as e:
        return create_error_response(
            message=str(e),
            error_type="NotImplementedError",
            details={"strategy": summary_strategy},
        )
    except Exception as e:
        return create_error_response(
            message=f"Consolidation failed: {str(e)}",
            error_type="ConsolidationError",
        )
