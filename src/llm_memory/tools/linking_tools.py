"""Memory linking MCP tools."""

from typing import Any

from llm_memory.models.linking import LinkType
from llm_memory.services.linking_service import LinkingService
from llm_memory.tools import create_error_response


async def memory_link(
    service: LinkingService,
    source_id: str,
    target_id: str,
    link_type: str = "related",
    bidirectional: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a link between two memories.

    Args:
        service: Linking service instance
        source_id: Source memory ID
        target_id: Target memory ID
        link_type: Link type (related/parent/child/similar/reference)
        bidirectional: Create reverse link automatically
        metadata: Optional link metadata

    Returns:
        Created link information
    """
    # Validate link_type
    try:
        ltype = LinkType(link_type)
    except ValueError:
        return create_error_response(
            message=f"Invalid link_type: {link_type}. Must be one of: related, parent, child, similar, reference",
            error_type="ValidationError",
        )

    # Validate IDs are not empty
    if not source_id or not target_id:
        return create_error_response(
            message="source_id and target_id cannot be empty",
            error_type="ValidationError",
        )

    # Create link
    try:
        link = await service.create_link(
            source_id=source_id,
            target_id=target_id,
            link_type=ltype,
            bidirectional=bidirectional,
            metadata=metadata,
            use_transaction=False,
        )

        return {
            "link_id": link.id,
            "source_id": link.source_id,
            "target_id": link.target_id,
            "link_type": link.link_type.value,
            "bidirectional": bidirectional,
            "created_at": link.created_at.isoformat(),
        }
    except ValueError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )
    except RuntimeError as e:
        return create_error_response(
            message=str(e),
            error_type="NotFoundError",
        )


async def memory_unlink(
    service: LinkingService,
    source_id: str,
    target_id: str,
    link_type: str | None = None,
) -> dict[str, Any]:
    """Remove link(s) between two memories.

    Args:
        service: Linking service instance
        source_id: Source memory ID
        target_id: Target memory ID
        link_type: Specific type to remove (None = all)

    Returns:
        Deletion count
    """
    # Validate IDs are not empty
    if not source_id or not target_id:
        return create_error_response(
            message="source_id and target_id cannot be empty",
            error_type="ValidationError",
        )

    # Validate link_type if provided
    ltype = None
    if link_type:
        try:
            ltype = LinkType(link_type)
        except ValueError:
            return create_error_response(
                message=f"Invalid link_type: {link_type}. Must be one of: related, parent, child, similar, reference",
                error_type="ValidationError",
            )

    result = await service.delete_link(
        source_id=source_id,
        target_id=target_id,
        link_type=ltype,
        use_transaction=False,
    )

    # Service now returns a dict, pass it through
    return result


async def memory_get_links(
    service: LinkingService,
    memory_id: str,
    link_type: str | None = None,
    direction: str = "both",
) -> dict[str, Any]:
    """Get links for a memory.

    Args:
        service: Linking service instance
        memory_id: Memory ID
        link_type: Filter by link type
        direction: Direction filter (outgoing/incoming/both)

    Returns:
        List of links
    """
    # Validate memory_id
    if not memory_id:
        return create_error_response(
            message="memory_id cannot be empty",
            error_type="ValidationError",
        )

    # Validate direction
    if direction not in ["outgoing", "incoming", "both"]:
        return create_error_response(
            message=f"Invalid direction: {direction}. Must be one of: outgoing, incoming, both",
            error_type="ValidationError",
        )

    # Validate link_type if provided
    ltype = None
    if link_type:
        try:
            ltype = LinkType(link_type)
        except ValueError:
            return create_error_response(
                message=f"Invalid link_type: {link_type}. Must be one of: related, parent, child, similar, reference",
                error_type="ValidationError",
            )

    result = await service.get_links(
        memory_id=memory_id,
        link_type=ltype,
        direction=direction,
    )

    # Service now returns a dict with memory_id, links (list of dicts), total
    # Transform links to match API spec (add link_id field)
    formatted_links = [
        {
            "link_id": link["id"],
            "source_id": link["source_id"],
            "target_id": link["target_id"],
            "link_type": link["link_type"],
            "metadata": link["metadata"],
            "created_at": link["created_at"],
        }
        for link in result["links"]
    ]

    return {
        "memory_id": result["memory_id"],
        "links": formatted_links,
        "total": result["total"],
    }
