# Memory Tools

Memory Tools are a set of tools for LLMs to manage searchable persistent memory with semantic search capabilities.

## Overview

| Tool | Description |
|------|-------------|
| `memory_store` | Store memory entry (auto-generates embeddings) |
| `memory_search` | Semantic/keyword/hybrid search |
| `memory_get` | Get memory by ID |
| `memory_update` | Update memory |
| `memory_delete` | Delete memory |
| `memory_list` | List with filtering and pagination |
| `memory_batch_store` | Batch store multiple memories (configurable max) **v1.1.0** |
| `memory_batch_update` | Batch update multiple memories (configurable max) **v1.1.0** |
| `memory_get_score` | Get importance score **v1.1.0** |
| `memory_set_score` | Manually set importance score **v1.1.0** |
| `memory_consolidate` | Consolidate and summarize related memories **v1.1.0** |

---

## memory_store

Stores a memory entry and automatically generates an embedding vector.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `content` | string | Yes | - | Content to store |
| `content_type` | string | No | `"text"` | Content type |
| `memory_tier` | string | No | `"long_term"` | Memory tier |
| `tags` | string[] | No | `[]` | Classification tags |
| `metadata` | object | No | `{}` | Additional metadata |
| `agent_id` | string | No | `null` | Agent ID |
| `ttl_seconds` | integer | No | `null` | Time to live (seconds) |

### Enum Values

**content_type:**
- `text` - Text
- `image` - Image
- `code` - Source code
- `json` - JSON
- `yaml` - YAML

**memory_tier:**
- `short_term` - Short-term memory (with TTL, auto-expires)
- `long_term` - Long-term memory (persistent storage)
- `working` - Working memory (for active sessions)

### Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "User prefers dark mode",
  "memory_tier": "long_term",
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Example

```python
memory_store(
    content="User prefers dark mode and large font sizes",
    memory_tier="long_term",
    tags=["preferences", "ui"],
    metadata={"source": "settings_page"}
)
```

### Validation

- `content` cannot be empty
- `ttl_seconds` must be 0 or greater
- Invalid `memory_tier` or `content_type` returns an error

---

## memory_search

Search memories using semantic, keyword, or hybrid search.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query text |
| `top_k` | integer | No | `10` | Maximum results to return |
| `memory_tier` | string | No | `null` | Filter by tier |
| `tags` | string[] | No | `null` | Filter by tags (AND condition) |
| `content_type` | string | No | `null` | Filter by content type |
| `min_similarity` | float | No | `0.0` | Minimum similarity threshold (0.0-1.0) |
| `search_mode` | string | No | `"semantic"` | Search mode **v1.1.0** |
| `keyword_weight` | float | No | `0.3` | Keyword weight in hybrid search **v1.1.0** |
| `sort_by` | string | No | `"relevance"` | Sort order **v1.1.0** |
| `importance_weight` | float | No | `0.0` | Importance score weight **v1.1.0** |

**search_mode:**
- `semantic` - Vector similarity search (default)
- `keyword` - FTS5 keyword search
- `hybrid` - Combined keyword + semantic search

**sort_by:**
- `relevance` - By relevance (default)
- `importance` - By importance score
- `created_at` - By creation date

### Response

```json
{
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "User prefers dark mode",
      "similarity": 0.89,
      "memory_tier": "long_term",
      "tags": ["preferences", "ui"],
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

### Example

```python
memory_search(
    query="user interface preferences",
    top_k=5,
    memory_tier="long_term",
    min_similarity=0.5
)
```

### Validation

- `top_k` must be in range 1-1000
- `min_similarity` must be in range 0.0-1.0

---

## memory_get

Get a specific memory by ID.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Memory ID (UUID) |

### Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "User prefers dark mode",
  "content_type": "text",
  "memory_tier": "long_term",
  "tags": ["preferences", "ui"],
  "metadata": {"source": "settings_page"},
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "expires_at": null
}
```

### Errors

- `NotFoundError` - Memory not found

---

## memory_update

Update an existing memory entry.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Memory ID to update |
| `content` | string | No | New content (regenerates embedding) |
| `tags` | string[] | No | New tag list (replaces existing) |
| `metadata` | object | No | Additional metadata (merges with existing) |
| `memory_tier` | string | No | New tier (for promotion/demotion) |

### Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "updated": true,
  "updated_at": "2025-01-15T11:00:00Z"
}
```

### Examples

```python
# Update tags
memory_update(
    id="550e8400-e29b-41d4-a716-446655440000",
    tags=["preferences", "ui", "theme"]
)

# Promote from short-term to long-term
memory_update(
    id="550e8400-e29b-41d4-a716-446655440000",
    memory_tier="long_term"
)
```

### Errors

- `NotFoundError` - Memory not found

---

## memory_delete

Delete memories by ID or conditions.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | No | Single memory ID to delete |
| `ids` | string[] | No | List of memory IDs to delete |
| `memory_tier` | string | No | Delete all memories in this tier |
| `older_than` | string | No | Delete memories older than this date (ISO format) |

### Response

```json
{
  "deleted_count": 3,
  "deleted_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "661f9511-f38c-52e5-b827-557766551111",
    "772a0622-g49d-63f6-c938-668877662222"
  ]
}
```

### Examples

```python
# Delete single
memory_delete(id="550e8400-e29b-41d4-a716-446655440000")

# Delete multiple
memory_delete(ids=["id1", "id2", "id3"])

# Delete old memories
memory_delete(older_than="2024-01-01T00:00:00Z")

# Delete entire tier
memory_delete(memory_tier="short_term")
```

---

## memory_list

List memories with filtering and pagination.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_tier` | string | No | `null` | Filter by tier |
| `tags` | string[] | No | `null` | Filter by tags (AND condition) |
| `content_type` | string | No | `null` | Filter by content type |
| `created_after` | string | No | `null` | Filter by creation date (ISO format) |
| `created_before` | string | No | `null` | Filter by creation date (ISO format) |
| `limit` | integer | No | `50` | Maximum results (max 1000) |
| `offset` | integer | No | `0` | Pagination offset |

### Response

```json
{
  "memories": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "User prefers dark mode",
      "content_type": "text",
      "memory_tier": "long_term",
      "tags": ["preferences", "ui"],
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

### Examples

```python
# Get long-term memories
memory_list(memory_tier="long_term", limit=20)

# Filter by specific tags
memory_list(tags=["preferences"], created_after="2025-01-01T00:00:00Z")

# Pagination
memory_list(limit=50, offset=50)  # Page 2
```

---

## Memory Tiers

### short_term (Short-term Memory)
- Auto-expires with TTL
- Best for temporary information
- Set expiration with `ttl_seconds` parameter

### long_term (Long-term Memory)
- Persistent storage
- For important information, user preferences, etc.
- Default tier

### working (Working Memory)
- Active session context
- Temporary data during task execution

---

## Error Response

All tools return a unified error format:

```json
{
  "error": true,
  "error_type": "ValidationError",
  "message": "Content cannot be empty"
}
```

### Error Types

- `ValidationError` - Input validation error
- `NotFoundError` - Resource not found

---

## memory_batch_store (v1.1.0)

Batch store multiple memories at once.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `items` | array | Yes | - | List of memories to store (max configurable, default 100) |
| `on_error` | string | No | `"rollback"` | Error handling behavior |

> **Note (v1.3.0)**: Maximum batch size is configurable via `LLM_MEMORY_BATCH_MAX_SIZE` environment variable (default: 100, range: 1-1000).

**items elements:**
- `content` (string, required) - Content
- `content_type` (string) - Content type
- `memory_tier` (string) - Memory tier
- `tags` (string[]) - Tags
- `metadata` (object) - Metadata

**on_error:**
- `rollback` - Roll back all on error
- `continue` - Skip errors and continue
- `stop` - Stop at error point

### Response

```json
{
  "success": true,
  "stored_count": 3,
  "stored_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "errors": []
}
```

### Example

```python
memory_batch_store(
    items=[
        {"content": "First memory", "tags": ["batch"]},
        {"content": "Second memory", "tags": ["batch"]},
        {"content": "Third memory", "tags": ["batch"]}
    ],
    on_error="rollback"
)
```

---

## memory_batch_update (v1.1.0)

Batch update multiple memories at once.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `updates` | array | Yes | - | List of memories to update (max configurable, default 100) |
| `on_error` | string | No | `"rollback"` | Error handling behavior |

> **Note (v1.3.0)**: Maximum batch size is configurable via `LLM_MEMORY_BATCH_MAX_SIZE` environment variable (default: 100, range: 1-1000).

**updates elements:**
- `id` (string, required) - Memory ID
- `content` (string) - New content
- `tags` (string[]) - New tags
- `metadata` (object) - Additional metadata
- `memory_tier` (string) - New tier

### Response

```json
{
  "success": true,
  "updated_count": 2,
  "updated_ids": ["uuid-1", "uuid-2"],
  "errors": []
}
```

### Example

```python
memory_batch_update(
    updates=[
        {"id": "uuid-1", "tags": ["updated", "important"]},
        {"id": "uuid-2", "metadata": {"reviewed": true}}
    ],
    on_error="continue"
)
```

---

## memory_get_score (v1.1.0)

Get the importance score of a memory. Scores are calculated based on access patterns (frequency and last access time).

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Memory ID (UUID) |

### Response

```json
{
  "success": true,
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "importance_score": 0.75,
  "access_count": 12,
  "last_accessed_at": "2025-01-15T14:30:00Z"
}
```

### Example

```python
memory_get_score(id="550e8400-e29b-41d4-a716-446655440000")
```

---

## memory_set_score (v1.1.0)

Manually set the importance score of a memory.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | string | Yes | - | Memory ID (UUID) |
| `score` | float | Yes | - | New score (0.0-1.0) |
| `reason` | string | No | `"Manual override"` | Reason for setting (for audit) |

### Response

```json
{
  "success": true,
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "previous_score": 0.5,
  "new_score": 0.9
}
```

### Example

```python
memory_set_score(
    id="550e8400-e29b-41d4-a716-446655440000",
    score=0.9,
    reason="Critical user preference"
)
```

### Validation

- `score` must be in range 0.0-1.0
- Non-existent ID returns error

---

## memory_consolidate (v1.1.0)

Consolidate multiple related memories into one and generate a summary.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_ids` | string[] | Yes | - | List of memory IDs to consolidate (2-50) |
| `summary_strategy` | string | No | `"extractive"` | Summarization strategy |
| `preserve_originals` | boolean | No | `true` | Whether to keep original memories |
| `tags` | string[] | No | `null` | Tags for consolidated memory |
| `metadata` | object | No | `null` | Metadata for consolidated memory |

**summary_strategy:**
- `extractive` - Extract important sentences for summary

### Response

```json
{
  "success": true,
  "consolidated_memory_id": "new-uuid",
  "original_count": 3,
  "preserved": true,
  "summary_length": 450
}
```

### Examples

```python
# Consolidate related memories (preserve originals)
memory_consolidate(
    memory_ids=["uuid-1", "uuid-2", "uuid-3"],
    summary_strategy="extractive",
    preserve_originals=True,
    tags=["consolidated", "summary"]
)

# Consolidate and delete originals
memory_consolidate(
    memory_ids=["uuid-1", "uuid-2"],
    preserve_originals=False
)
```

### Validation

- `memory_ids` must have 2-50 items
- Non-existent ID returns error
- Single item returns error
