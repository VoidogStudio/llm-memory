# Linking Tools

Memory Linking Tools are a set of tools for managing relationships (links) between memories.

**Added in v1.2.0**

## Overview

| Tool | Description |
|------|-------------|
| `memory_link` | Create bidirectional link between memories |
| `memory_unlink` | Delete link |
| `memory_get_links` | Get links |

---

## memory_link

Create a link between two memories. Bidirectional links are created by default.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source_id` | string | Yes | - | Source memory ID |
| `target_id` | string | Yes | - | Target memory ID |
| `link_type` | string | No | `"related"` | Link type |
| `bidirectional` | boolean | No | `true` | Create bidirectional link |
| `metadata` | object | No | `{}` | Link metadata |

### Link Types

| Type | Description | Reverse |
|------|-------------|---------|
| `related` | Related memories | `related` |
| `parent` | Parent memory | `child` |
| `child` | Child memory | `parent` |
| `similar` | Similar memories | `similar` |
| `reference` | Referenced memory | `reference` |

### Response

```json
{
  "link_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_id": "memory-uuid-1",
  "target_id": "memory-uuid-2",
  "link_type": "related",
  "bidirectional": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Examples

```python
# Create related link
memory_link(
    source_id="uuid-1",
    target_id="uuid-2",
    link_type="related"
)

# Create parent-child relationship
memory_link(
    source_id="parent-uuid",
    target_id="child-uuid",
    link_type="parent"
)
# Reverse child link is automatically created

# One-way link only
memory_link(
    source_id="uuid-1",
    target_id="uuid-2",
    link_type="reference",
    bidirectional=False
)

# Link with metadata
memory_link(
    source_id="uuid-1",
    target_id="uuid-2",
    link_type="similar",
    metadata={"similarity_score": 0.95}
)
```

### Validation

- `source_id` and `target_id` cannot be empty
- Self-referential link (same ID) returns error
- Link to non-existent memory returns error
- Invalid `link_type` returns error

### Errors

- `ValidationError` - Invalid parameter
- `NotFoundError` - Memory not found

---

## memory_unlink

Delete link between memories. For bidirectional links, both directions are deleted.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source_id` | string | Yes | - | Source memory ID |
| `target_id` | string | Yes | - | Target memory ID |
| `link_type` | string | No | `null` | Delete specific type only (omit for all types) |

### Response

```json
{
  "deleted_count": 2,
  "source_id": "uuid-1",
  "target_id": "uuid-2",
  "link_type": null
}
```

### Examples

```python
# Delete all links between two memories
memory_unlink(
    source_id="uuid-1",
    target_id="uuid-2"
)

# Delete specific type only
memory_unlink(
    source_id="uuid-1",
    target_id="uuid-2",
    link_type="related"
)
```

### Validation

- `source_id` and `target_id` cannot be empty
- Invalid `link_type` returns error

---

## memory_get_links

Get links for a memory. Filter by direction and type.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_id` | string | Yes | - | Memory ID |
| `link_type` | string | No | `null` | Filter by type |
| `direction` | string | No | `"both"` | Filter by direction |

### Direction

| Value | Description |
|-------|-------------|
| `outgoing` | Links from this memory to others |
| `incoming` | Links from others to this memory |
| `both` | Both directions |

### Response

```json
{
  "memory_id": "uuid-1",
  "links": [
    {
      "link_id": "link-uuid-1",
      "source_id": "uuid-1",
      "target_id": "uuid-2",
      "link_type": "related",
      "metadata": {},
      "created_at": "2025-01-15T10:30:00Z"
    },
    {
      "link_id": "link-uuid-2",
      "source_id": "uuid-3",
      "target_id": "uuid-1",
      "link_type": "parent",
      "metadata": {},
      "created_at": "2025-01-15T11:00:00Z"
    }
  ],
  "total": 2
}
```

### Examples

```python
# Get all links
links = memory_get_links(memory_id="uuid-1")

# Outgoing links only
memory_get_links(
    memory_id="uuid-1",
    direction="outgoing"
)

# Specific type incoming links only
memory_get_links(
    memory_id="uuid-1",
    link_type="child",
    direction="incoming"
)
```

### Validation

- `memory_id` cannot be empty
- Invalid `direction` or `link_type` returns error

---

## Auto-Deletion of Links

When a memory is deleted, associated links are automatically deleted (CASCADE DELETE).

```python
# Deleting memory also deletes links
memory_delete(id="uuid-1")
# All links associated with uuid-1 are auto-deleted
```

---

## Use Cases

### Building a Knowledge Graph

```python
# Link topic to related memories
memory_link(
    source_id="topic-python",
    target_id="memory-python-tips",
    link_type="parent"
)
memory_link(
    source_id="topic-python",
    target_id="memory-python-best-practices",
    link_type="parent"
)

# Discover related memories
children = memory_get_links(
    memory_id="topic-python",
    link_type="child",
    direction="outgoing"
)
```

### Tracking Similar Memories

```python
# Link highly similar memories
memory_link(
    source_id="uuid-1",
    target_id="uuid-2",
    link_type="similar",
    metadata={"similarity": 0.92}
)

# Search similar memories
similar = memory_get_links(
    memory_id="uuid-1",
    link_type="similar"
)
```

### Managing References

```python
# Link document to source
memory_link(
    source_id="document-uuid",
    target_id="source-uuid",
    link_type="reference",
    bidirectional=False  # One-way only
)
```

---

## Error Response

```json
{
  "error": true,
  "error_type": "ValidationError",
  "message": "Cannot create link to self"
}
```

### Error Types

- `ValidationError` - Invalid parameter (self-reference, empty ID, etc.)
- `NotFoundError` - Memory not found

---

## Related Links

- [Memory Tools](memory-tools.md)
- [Tools List](README.md)
