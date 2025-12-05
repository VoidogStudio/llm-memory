"""Knowledge-related MCP tools."""

from typing import Any

from llm_memory.services.knowledge_service import KnowledgeService
from llm_memory.tools import create_error_response


async def knowledge_import(
    service: KnowledgeService,
    title: str,
    content: str,
    source: str | None = None,
    category: str | None = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import a document into the knowledge base.

    Args:
        service: Knowledge service instance
        title: Document title
        content: Full document content
        source: Source URL or file path
        category: Category for organization
        chunk_size: Characters per chunk
        chunk_overlap: Overlap between chunks
        metadata: Additional metadata

    Returns:
        Document ID and chunk count
    """
    # title validation
    if not title or not title.strip():
        return create_error_response(
            message="title cannot be empty",
            error_type="ValidationError",
        )

    # content validation
    if not content or not content.strip():
        return create_error_response(
            message="content cannot be empty",
            error_type="ValidationError",
        )

    # chunk_size validation
    if chunk_size < 100 or chunk_size > 10000:
        return create_error_response(
            message="chunk_size must be between 100 and 10000",
            error_type="ValidationError",
        )

    # chunk_overlap validation
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        return create_error_response(
            message="chunk_overlap must be >= 0 and < chunk_size",
            error_type="ValidationError",
        )

    document, chunk_count = await service.import_document(
        title=title,
        content=content,
        source=source,
        category=category,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        metadata=metadata,
    )

    return {
        "document_id": document.id,
        "title": document.title,
        "chunks_created": chunk_count,
        "created_at": document.created_at.isoformat(),
    }


async def knowledge_query(
    service: KnowledgeService,
    query: str,
    top_k: int = 5,
    category: str | None = None,
    document_id: str | None = None,
    include_document_info: bool = True,
) -> dict[str, Any]:
    """Query the knowledge base.

    Args:
        service: Knowledge service instance
        query: Search query
        top_k: Number of chunks to return
        category: Filter by category
        document_id: Filter by document
        include_document_info: Include document metadata

    Returns:
        Matching chunks with similarity scores
    """
    results = await service.query(
        query=query, top_k=top_k, category=category, document_id=document_id
    )

    formatted_results = []
    for r in results:
        result_dict = {
            "chunk_id": r.chunk.id,
            "content": r.chunk.content,
            "similarity": r.similarity,
        }

        if include_document_info:
            result_dict["document"] = {
                "id": r.document.id,
                "title": r.document.title,
                "category": r.document.category,
            }

        formatted_results.append(result_dict)

    return {"results": formatted_results, "total": len(formatted_results)}
