# Structured Memory Schema Tools (v1.7.0)

Schema tools allow you to define custom memory structures with type validation, enabling type-safe memory storage and retrieval.

## Overview

| Tool | Description |
|------|-------------|
| `memory_schema_register` | Register a new memory schema |
| `memory_schema_list` | List all registered schemas |
| `memory_schema_get` | Get detailed schema information |
| `memory_store_typed` | Store memory with schema validation |
| `memory_search_typed` | Search memories by schema type and field values |

---

## memory_schema_register

Register a new memory schema with field definitions and validation rules.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | - | Schema name (unique within namespace) |
| `fields` | array | Yes | - | Array of field definitions |
| `namespace` | string | No | auto-detect | Namespace for the schema |
| `description` | string | No | "" | Schema description |

### Field Definition

Each field in the `fields` array has the following structure:

| Property | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `name` | string | Yes | - | Field name |
| `type` | string | Yes | - | Field type: `string`, `number`, `boolean`, `datetime`, `array`, `object` |
| `required` | boolean | No | false | Whether field is required |
| `default` | any | No | null | Default value if not provided |
| `description` | string | No | "" | Field description |

### Returns

```json
{
  "success": true,
  "schema": {
    "id": "schema-uuid",
    "name": "error_log",
    "namespace": "my-project",
    "version": 1,
    "fields": [
      {"name": "error_type", "type": "string", "required": true},
      {"name": "message", "type": "string", "required": true},
      {"name": "stack_trace", "type": "string", "required": false},
      {"name": "severity", "type": "number", "required": false, "default": 1}
    ],
    "description": "Schema for error logs",
    "created_at": "2025-12-09T12:00:00Z"
  }
}
```

### Example

```python
# Register an error log schema
memory_schema_register(
    name="error_log",
    fields=[
        {"name": "error_type", "type": "string", "required": True},
        {"name": "message", "type": "string", "required": True},
        {"name": "stack_trace", "type": "string", "required": False},
        {"name": "severity", "type": "number", "default": 1}
    ],
    description="Schema for error logs"
)

# Register a decision schema
memory_schema_register(
    name="design_decision",
    fields=[
        {"name": "title", "type": "string", "required": True},
        {"name": "context", "type": "string", "required": True},
        {"name": "decision", "type": "string", "required": True},
        {"name": "alternatives", "type": "array", "required": False},
        {"name": "consequences", "type": "string", "required": False}
    ],
    description="Architecture Decision Record (ADR)"
)
```

---

## memory_schema_list

List all registered schemas, optionally filtered by namespace.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `namespace` | string | No | auto-detect | Filter by namespace |
| `include_fields` | boolean | No | false | Include field definitions |

### Returns

```json
{
  "schemas": [
    {
      "id": "schema-uuid-1",
      "name": "error_log",
      "namespace": "my-project",
      "version": 1,
      "description": "Schema for error logs",
      "created_at": "2025-12-09T12:00:00Z"
    },
    {
      "id": "schema-uuid-2",
      "name": "design_decision",
      "namespace": "my-project",
      "version": 1,
      "description": "Architecture Decision Record (ADR)",
      "created_at": "2025-12-09T11:00:00Z"
    }
  ],
  "total": 2
}
```

### Example

```python
# List all schemas in current namespace
memory_schema_list()

# List with field definitions
memory_schema_list(include_fields=True)
```

---

## memory_schema_get

Get detailed information about a specific schema.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | - | Schema name |
| `namespace` | string | No | auto-detect | Namespace to search in |
| `version` | integer | No | latest | Specific schema version |

### Returns

```json
{
  "id": "schema-uuid",
  "name": "error_log",
  "namespace": "my-project",
  "version": 1,
  "fields": [
    {"name": "error_type", "type": "string", "required": true, "description": ""},
    {"name": "message", "type": "string", "required": true, "description": ""},
    {"name": "stack_trace", "type": "string", "required": false, "description": ""},
    {"name": "severity", "type": "number", "required": false, "default": 1, "description": ""}
  ],
  "description": "Schema for error logs",
  "created_at": "2025-12-09T12:00:00Z",
  "updated_at": "2025-12-09T12:00:00Z"
}
```

### Example

```python
# Get schema details
memory_schema_get(name="error_log")
```

---

## memory_store_typed

Store a memory with schema validation. The structured content is validated against the specified schema before storage.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `schema_name` | string | Yes | - | Name of the schema to validate against |
| `structured_content` | object | Yes | - | Content matching the schema |
| `namespace` | string | No | auto-detect | Namespace for the memory |
| `content` | string | No | auto-generate | Text content (generated from structured if not provided) |
| `tags` | array | No | [] | Tags for the memory |
| `metadata` | object | No | {} | Additional metadata |

### Returns

```json
{
  "success": true,
  "memory": {
    "id": "memory-uuid",
    "content": "Error: TypeError - Cannot read property 'x' of undefined",
    "content_type": "json",
    "schema_id": "schema-uuid",
    "structured_content": {
      "error_type": "TypeError",
      "message": "Cannot read property 'x' of undefined",
      "severity": 2
    },
    "tags": ["error", "frontend"],
    "namespace": "my-project",
    "created_at": "2025-12-09T12:00:00Z"
  }
}
```

### Example

```python
# Store a typed error log
memory_store_typed(
    schema_name="error_log",
    structured_content={
        "error_type": "TypeError",
        "message": "Cannot read property 'x' of undefined",
        "severity": 2
    },
    tags=["error", "frontend"]
)

# Store a design decision
memory_store_typed(
    schema_name="design_decision",
    structured_content={
        "title": "Use SQLite for storage",
        "context": "Need embedded database for single-file deployment",
        "decision": "SQLite with sqlite-vec extension",
        "alternatives": ["PostgreSQL", "DuckDB", "LanceDB"],
        "consequences": "Limited concurrent writes, excellent read performance"
    },
    tags=["architecture", "database"]
)
```

### Validation Errors

If the structured content doesn't match the schema, an error is returned:

```json
{
  "error": true,
  "error_type": "ValidationError",
  "message": "Required field 'message' is missing"
}
```

---

## memory_search_typed

Search memories by schema type and field conditions.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `schema_name` | string | Yes | - | Schema name to filter by |
| `field_conditions` | object | No | {} | Field value conditions |
| `namespace` | string | No | auto-detect | Namespace to search in |
| `top_k` | integer | No | 10 | Maximum results to return |
| `sort_by` | string | No | "created_at" | Sort field |
| `sort_order` | string | No | "desc" | Sort order: "asc" or "desc" |

### Field Conditions

Field conditions support exact matching:

```python
field_conditions={
    "error_type": "TypeError",
    "severity": 2
}
```

### Returns

```json
{
  "memories": [
    {
      "id": "memory-uuid-1",
      "content": "Error: TypeError - Cannot read property 'x' of undefined",
      "schema_id": "schema-uuid",
      "structured_content": {
        "error_type": "TypeError",
        "message": "Cannot read property 'x' of undefined",
        "severity": 2
      },
      "tags": ["error", "frontend"],
      "created_at": "2025-12-09T12:00:00Z"
    }
  ],
  "total": 1
}
```

### Example

```python
# Search for all TypeErrors
memory_search_typed(
    schema_name="error_log",
    field_conditions={"error_type": "TypeError"}
)

# Search for high-severity errors
memory_search_typed(
    schema_name="error_log",
    field_conditions={"severity": 3},
    sort_by="created_at",
    sort_order="desc"
)

# List all design decisions
memory_search_typed(
    schema_name="design_decision",
    top_k=20
)
```

---

## Use Cases

### 1. Error Tracking

```python
# Register schema
memory_schema_register(
    name="error",
    fields=[
        {"name": "type", "type": "string", "required": True},
        {"name": "message", "type": "string", "required": True},
        {"name": "file", "type": "string"},
        {"name": "line", "type": "number"},
        {"name": "resolved", "type": "boolean", "default": False}
    ]
)

# Store errors
memory_store_typed(
    schema_name="error",
    structured_content={
        "type": "ImportError",
        "message": "No module named 'foo'",
        "file": "main.py",
        "line": 5,
        "resolved": False
    }
)

# Find unresolved errors
memory_search_typed(
    schema_name="error",
    field_conditions={"resolved": False}
)
```

### 2. Architecture Decision Records (ADR)

```python
# Register ADR schema
memory_schema_register(
    name="adr",
    fields=[
        {"name": "number", "type": "number", "required": True},
        {"name": "title", "type": "string", "required": True},
        {"name": "status", "type": "string", "required": True},
        {"name": "context", "type": "string", "required": True},
        {"name": "decision", "type": "string", "required": True}
    ]
)

# Store ADR
memory_store_typed(
    schema_name="adr",
    structured_content={
        "number": 1,
        "title": "Use Event Sourcing",
        "status": "accepted",
        "context": "Need audit trail for all changes",
        "decision": "Implement event sourcing pattern"
    }
)
```

---

## Related Links

- [Tools Reference](tools-reference.md)
- [Memory Tools](memory-tools.md)
- [Versioning Tools](versioning-tools.md) (v1.7.0)
- [Dependency Tools](dependency-tools.md) (v1.7.0)
