# Dependency Tracking Tools (v1.7.0)

Dependency tracking tools allow you to analyze the impact of memory changes and propagate updates to dependent memories.

## Overview

| Tool | Description |
|------|-------------|
| `memory_dependency_analyze` | Analyze impact of changes on dependent memories |
| `memory_dependency_propagate` | Propagate updates to dependent memories |

Additionally, the `memory_link` tool has been extended with cascade options. See [Linking Tools](linking-tools.md) for details.

---

## memory_dependency_analyze

Analyze the impact of potential changes to a memory by traversing its dependency graph.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_id` | string | Yes | - | UUID of the memory to analyze |
| `cascade_type` | string | No | "both" | Type of cascade: "update", "delete", or "both" |
| `max_depth` | integer | No | 3 | Maximum traversal depth (1-5) |
| `namespace` | string | No | auto-detect | Namespace to search in |

### Returns

```json
{
  "source_memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "cascade_type": "both",
  "max_depth": 3,
  "affected_memories": [
    {
      "memory_id": "uuid-1",
      "content_preview": "Derived configuration...",
      "link_type": "DEPENDS_ON",
      "cascade_on_update": true,
      "cascade_on_delete": true,
      "depth": 1,
      "path": ["550e8400-e29b-41d4-a716-446655440000", "uuid-1"]
    },
    {
      "memory_id": "uuid-2",
      "content_preview": "Related documentation...",
      "link_type": "DERIVED_FROM",
      "cascade_on_update": true,
      "cascade_on_delete": false,
      "depth": 2,
      "path": ["550e8400-e29b-41d4-a716-446655440000", "uuid-1", "uuid-2"]
    }
  ],
  "total_affected": 2,
  "circular_dependencies": []
}
```

### Example

```python
# Analyze impact of updating a configuration memory
memory_dependency_analyze(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    cascade_type="update",
    max_depth=3
)

# Analyze impact of deleting a memory
memory_dependency_analyze(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    cascade_type="delete"
)
```

### Circular Dependency Detection

If circular dependencies are detected, they are reported in the response:

```json
{
  "circular_dependencies": [
    {
      "cycle": ["uuid-1", "uuid-2", "uuid-3", "uuid-1"],
      "length": 3
    }
  ]
}
```

---

## memory_dependency_propagate

Propagate change notifications to dependent memories. This creates notifications that can be processed by downstream systems.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_id` | string | Yes | - | UUID of the changed memory |
| `notification_type` | string | Yes | - | Type: "update", "delete", or "stale" |
| `metadata` | object | No | {} | Additional notification metadata |
| `namespace` | string | No | auto-detect | Namespace to search in |

### Notification Types

| Type | Description |
|------|-------------|
| `update` | Source memory was updated |
| `delete` | Source memory was deleted |
| `stale` | Source memory is marked stale |

### Returns

```json
{
  "success": true,
  "source_memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "notification_type": "update",
  "notifications_created": 5,
  "affected_memories": [
    {
      "memory_id": "uuid-1",
      "notification_id": "notif-uuid-1"
    },
    {
      "memory_id": "uuid-2",
      "notification_id": "notif-uuid-2"
    }
  ]
}
```

### Example

```python
# Notify dependents of an update
memory_dependency_propagate(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    notification_type="update",
    metadata={"reason": "Configuration change", "version": 3}
)

# Notify dependents of deletion
memory_dependency_propagate(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    notification_type="delete"
)

# Mark dependent memories as potentially stale
memory_dependency_propagate(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    notification_type="stale",
    metadata={"reason": "Source file changed"}
)
```

---

## Extended memory_link Tool

The `memory_link` tool now supports cascade options for dependency tracking:

### New Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `cascade_on_update` | boolean | No | false | Notify target when source is updated |
| `cascade_on_delete` | boolean | No | false | Notify target when source is deleted |
| `strength` | float | No | 1.0 | Link strength (0.0-1.0) |

### New Link Types

Two new link types are available for dependency relationships:

| Type | Description |
|------|-------------|
| `DEPENDS_ON` | Target depends on source |
| `DERIVED_FROM` | Target is derived from source |

### Example

```python
# Create a dependency link with cascade options
memory_link(
    source_id="config-memory-id",
    target_id="derived-memory-id",
    link_type="DEPENDS_ON",
    cascade_on_update=True,
    cascade_on_delete=True,
    strength=1.0,
    bidirectional=False
)

# Create a weaker derived-from relationship
memory_link(
    source_id="original-doc-id",
    target_id="summary-doc-id",
    link_type="DERIVED_FROM",
    cascade_on_update=True,
    cascade_on_delete=False,
    strength=0.8
)
```

---

## Workflow Example

### 1. Set Up Dependencies

```python
# Store base configuration
config_id = memory_store(
    content="Database configuration: host=localhost, port=5432",
    tags=["config", "database"]
)["id"]

# Store derived setting
derived_id = memory_store(
    content="Connection string derived from config",
    tags=["config", "derived"]
)["id"]

# Create dependency link
memory_link(
    source_id=config_id,
    target_id=derived_id,
    link_type="DEPENDS_ON",
    cascade_on_update=True,
    cascade_on_delete=True
)
```

### 2. Analyze Impact Before Changes

```python
# Before updating config, check impact
analysis = memory_dependency_analyze(
    memory_id=config_id,
    cascade_type="update"
)

print(f"This change will affect {analysis['total_affected']} memories")
```

### 3. Update and Propagate

```python
# Update the config
memory_update(
    id=config_id,
    content="Database configuration: host=db.example.com, port=5432"
)

# Propagate the change
memory_dependency_propagate(
    memory_id=config_id,
    notification_type="update",
    metadata={"change": "host updated"}
)
```

---

## Database Schema

The dependency tracking system uses a notifications table:

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT | Notification UUID |
| `source_memory_id` | TEXT | Source memory that changed |
| `target_memory_id` | TEXT | Affected memory |
| `notification_type` | TEXT | Type of notification |
| `metadata` | TEXT | JSON metadata |
| `created_at` | TEXT | Creation timestamp |
| `processed_at` | TEXT | Processing timestamp (null if pending) |

---

## Related Links

- [Tools Reference](tools-reference.md)
- [Linking Tools](linking-tools.md)
- [Versioning Tools](versioning-tools.md) (v1.7.0)
- [Schema Tools](schema-tools.md) (v1.7.0)
