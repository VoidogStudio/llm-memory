# Memory Versioning Tools (v1.7.0)

Memory versioning tools allow you to track the history of memory changes, compare versions, and rollback to previous states.

## Overview

| Tool | Description |
|------|-------------|
| `memory_version_history` | Get complete version history for a memory |
| `memory_version_get` | Retrieve a specific version of a memory |
| `memory_version_rollback` | Restore a memory to a previous version |
| `memory_version_diff` | Compare two versions and view changes |

---

## memory_version_history

Get the complete version history for a memory, including all snapshots and change reasons.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_id` | string | Yes | - | UUID of the memory |
| `limit` | integer | No | 10 | Maximum number of versions to return |
| `namespace` | string | No | auto-detect | Namespace to search in |

### Returns

```json
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_version": 3,
  "total_versions": 3,
  "versions": [
    {
      "version": 3,
      "content": "Updated content",
      "content_type": "text",
      "tags": ["updated"],
      "metadata": {},
      "created_at": "2025-12-09T12:00:00Z",
      "change_reason": "Content update via memory_update"
    },
    {
      "version": 2,
      "content": "Previous content",
      "content_type": "text",
      "tags": ["original"],
      "metadata": {},
      "created_at": "2025-12-08T10:00:00Z",
      "change_reason": "Tag modification"
    },
    {
      "version": 1,
      "content": "Initial content",
      "content_type": "text",
      "tags": [],
      "metadata": {},
      "created_at": "2025-12-07T08:00:00Z",
      "change_reason": "Initial creation"
    }
  ]
}
```

### Example

```python
# Get version history for a memory
memory_version_history(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    limit=5
)
```

---

## memory_version_get

Retrieve a specific version of a memory by version number.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_id` | string | Yes | - | UUID of the memory |
| `version` | integer | Yes | - | Version number to retrieve |
| `namespace` | string | No | auto-detect | Namespace to search in |

### Returns

```json
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": 2,
  "content": "Previous content",
  "content_type": "text",
  "tags": ["original"],
  "metadata": {},
  "created_at": "2025-12-08T10:00:00Z",
  "change_reason": "Tag modification"
}
```

### Example

```python
# Get version 2 of a memory
memory_version_get(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    version=2
)
```

---

## memory_version_rollback

Restore a memory to a previous version. This creates a new version with the content from the target version.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_id` | string | Yes | - | UUID of the memory |
| `target_version` | integer | Yes | - | Version number to rollback to |
| `reason` | string | No | "Rollback" | Reason for the rollback |
| `namespace` | string | No | auto-detect | Namespace to search in |

### Returns

```json
{
  "success": true,
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "previous_version": 3,
  "new_version": 4,
  "rolled_back_to": 2,
  "reason": "Reverting incorrect changes"
}
```

### Example

```python
# Rollback to version 2
memory_version_rollback(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    target_version=2,
    reason="Reverting incorrect changes"
)
```

### Notes

- Rollback does not delete version history; it creates a new version
- The new version's content will match the target version
- Original version history is preserved for audit purposes

---

## memory_version_diff

Compare two versions of a memory and view the differences.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_id` | string | Yes | - | UUID of the memory |
| `old_version` | integer | Yes | - | Older version number |
| `new_version` | integer | Yes | - | Newer version number |
| `namespace` | string | No | auto-detect | Namespace to search in |

### Returns

```json
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "old_version": 1,
  "new_version": 2,
  "changes": {
    "content": {
      "old": "Initial content",
      "new": "Updated content"
    },
    "tags": {
      "added": ["updated"],
      "removed": []
    },
    "metadata": {
      "added": {},
      "removed": {},
      "changed": {}
    }
  },
  "old_created_at": "2025-12-07T08:00:00Z",
  "new_created_at": "2025-12-08T10:00:00Z"
}
```

### Example

```python
# Compare version 1 and version 3
memory_version_diff(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    old_version=1,
    new_version=3
)
```

---

## Automatic Versioning

Memory versioning happens automatically when you use `memory_update`. Each update creates a new version snapshot before applying changes.

```python
# This automatically creates a version snapshot
memory_update(
    id="550e8400-e29b-41d4-a716-446655440000",
    content="New content"
)
```

### Version Retention

By default, the system retains the last 10 versions per memory. This can be configured via `LLM_MEMORY_VERSION_RETENTION` environment variable.

---

## Related Links

- [Tools Reference](tools-reference.md)
- [Memory Tools](memory-tools.md)
- [Schema Tools](schema-tools.md) (v1.7.0)
- [Dependency Tools](dependency-tools.md) (v1.7.0)
