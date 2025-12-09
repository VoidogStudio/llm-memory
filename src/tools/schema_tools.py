"""Memory schema MCP tools."""

from typing import Any

from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.schema import SchemaField
from src.services.memory_service import MemoryService
from src.services.schema_service import SchemaService
from src.tools import create_error_response


async def memory_schema_register(
    service: SchemaService,
    name: str,
    fields: list[dict[str, Any]],
    namespace: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Register a new memory schema.

    Args:
        service: Schema service instance
        name: Schema name
        fields: Field definitions
        namespace: Target namespace (default: auto-detect)
        description: Schema description

    Returns:
        Created schema information
    """
    try:
        # Convert field dicts to SchemaField objects
        schema_fields = [SchemaField(**field_dict) for field_dict in fields]

        # Resolve namespace
        if namespace is None:
            namespace = "default"

        # Register schema
        schema = await service.register_schema(
            name=name,
            namespace=namespace,
            fields=schema_fields,
            description=description,
        )

        return {
            "id": schema.id,
            "name": schema.name,
            "namespace": schema.namespace,
            "version": schema.version,
            "fields": [field.model_dump() for field in schema.fields],
            "created_at": schema.created_at.isoformat(),
        }
    except ValidationError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )
    except ConflictError as e:
        return create_error_response(
            message=str(e),
            error_type="ConflictError",
        )


async def memory_schema_list(
    service: SchemaService,
    namespace: str | None = None,
    include_fields: bool = False,
) -> dict[str, Any]:
    """List registered schemas.

    Args:
        service: Schema service instance
        namespace: Target namespace (default: auto-detect, None for all)
        include_fields: Include field definitions

    Returns:
        List of schemas
    """
    try:
        schemas = await service.list_schemas(namespace, include_fields)

        return {
            "schemas": [
                {
                    "id": s.id,
                    "name": s.name,
                    "namespace": s.namespace,
                    "version": s.version,
                    "fields": [field.model_dump() for field in s.fields] if include_fields else None,
                    "created_at": s.created_at.isoformat(),
                }
                for s in schemas
            ],
            "total": len(schemas),
        }
    except ValidationError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )
    except NotFoundError as e:
        return create_error_response(
            message=str(e),
            error_type="NotFoundError",
        )


async def memory_schema_get(
    service: SchemaService,
    name: str,
    namespace: str | None = None,
    version: int | None = None,
) -> dict[str, Any]:
    """Get a specific schema.

    Args:
        service: Schema service instance
        name: Schema name
        namespace: Target namespace
        version: Specific version (default: latest)

    Returns:
        Schema information
    """
    try:
        # Resolve namespace
        if namespace is None:
            namespace = "default"

        schema = await service.get_schema(namespace, name, version)
        if not schema:
            return create_error_response(
                message=f"Schema '{name}' not found in namespace '{namespace}'",
                error_type="NotFoundError",
            )

        return {
            "id": schema.id,
            "name": schema.name,
            "namespace": schema.namespace,
            "version": schema.version,
            "fields": [field.model_dump() for field in schema.fields],
            "created_at": schema.created_at.isoformat(),
            "updated_at": schema.updated_at.isoformat(),
        }
    except ValidationError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )
    except NotFoundError as e:
        return create_error_response(
            message=str(e),
            error_type="NotFoundError",
        )


async def memory_store_typed(
    memory_service: MemoryService,
    schema_service: SchemaService,
    schema_name: str,
    structured_content: dict[str, Any],
    namespace: str | None = None,
    content: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store a memory with structured content validated against a schema.

    Args:
        memory_service: Memory service instance
        schema_service: Schema service instance
        schema_name: Name of the schema to use
        structured_content: Structured data matching schema fields
        namespace: Target namespace
        content: Human-readable content (auto-generated if not provided)
        tags: Tags for categorization
        metadata: Additional metadata

    Returns:
        Created memory information
    """
    try:
        # Resolve namespace
        if namespace is None:
            namespace = "default"

        # Get schema
        schema = await schema_service.get_schema(namespace, schema_name)
        if not schema:
            return create_error_response(
                message=f"Schema '{schema_name}' not found in namespace '{namespace}'",
                error_type="NotFoundError",
            )

        # Validate data
        is_valid, errors = await schema_service.validate_data(schema, structured_content)
        if not is_valid:
            return create_error_response(
                message="Schema validation failed",
                error_type="ValidationError",
                details={"errors": errors},
            )

        # Generate content if not provided
        if content is None:
            # Simple JSON representation
            import json
            content = json.dumps(structured_content, indent=2)

        # Store memory using memory_service's store_typed method
        # This method needs to be added to MemoryService in Phase 5
        memory = await memory_service.store_typed(
            schema_id=schema.id,
            structured_content=structured_content,
            content=content,
            tags=tags or [],
            metadata=metadata or {},
            namespace=namespace,
        )

        return {
            "id": memory.id,
            "schema_id": schema.id,
            "schema_name": schema_name,
            "structured_content": structured_content,
            "content": content,
            "created_at": memory.created_at.isoformat(),
        }
    except NotFoundError as e:
        return create_error_response(
            message=str(e),
            error_type="NotFoundError",
        )
    except ValidationError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )


async def memory_search_typed(
    memory_service: MemoryService,
    schema_service: SchemaService,
    schema_name: str,
    field_conditions: dict[str, Any],
    namespace: str | None = None,
    top_k: int = 10,
    sort_by: str | None = None,
    sort_order: str = "desc",
) -> dict[str, Any]:
    """Search typed memories by field conditions.

    Args:
        memory_service: Memory service instance
        schema_service: Schema service instance
        schema_name: Schema name to filter by
        field_conditions: Field-value conditions
        namespace: Target namespace
        top_k: Maximum results (1-100)
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)

    Returns:
        Search results
    """
    try:
        # Resolve namespace
        if namespace is None:
            namespace = "default"

        # Get schema
        schema = await schema_service.get_schema(namespace, schema_name)
        if not schema:
            return create_error_response(
                message=f"Schema '{schema_name}' not found in namespace '{namespace}'",
                error_type="NotFoundError",
            )

        # Search typed memories using memory_service's search_typed method
        # This method needs to be added to MemoryService in Phase 5
        results = await memory_service.search_typed(
            schema_id=schema.id,
            field_conditions=field_conditions,
            namespace=namespace,
            top_k=top_k,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return {
            "count": len(results),
            "results": [
                {
                    "id": memory.id,
                    "schema_name": schema_name,
                    "structured_content": memory.structured_content,
                    "content": memory.content,
                    "created_at": memory.created_at.isoformat(),
                }
                for memory in results
            ],
        }
    except NotFoundError as e:
        return create_error_response(
            message=str(e),
            error_type="NotFoundError",
        )
    except ValidationError as e:
        return create_error_response(
            message=str(e),
            error_type="ValidationError",
        )
