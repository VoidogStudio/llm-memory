# Similarity Tools (v1.4.0)

Tools for finding similar and duplicate memories.

## Tools Overview

| Tool | Description |
|------|-------------|
| `memory_similar` | Find semantically similar memories |
| `memory_deduplicate` | Detect and merge duplicate memories |

---

## memory_similar

Find memories similar to a specified memory.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_id` | string | Yes | - | ID of the base memory |
| `namespace` | string | No | auto-detected | Target namespace |
| `search_scope` | string | No | `"current"` | Search scope: `current`, `shared`, `all` |
| `top_k` | integer | No | 10 | Number of similar memories to return |
| `min_similarity` | float | No | 0.85 | Minimum similarity threshold (0.0-1.0) |
| `exclude_linked` | boolean | No | true | Exclude already linked memories |

### Response

```json
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "similar_count": 3,
  "similar_memories": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "content": "Similar content here...",
      "similarity": 0.92,
      "namespace": "my-project"
    }
  ]
}
```

### Example

```python
# Find memories similar to a specific memory
memory_similar(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    top_k=5,
    min_similarity=0.8
)

# Search across all namespaces
memory_similar(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    search_scope="all",
    top_k=10
)
```

---

## memory_deduplicate

Detect and optionally merge duplicate memories.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `namespace` | string | No | auto-detected | Target namespace |
| `similarity_threshold` | float | No | 0.95 | Threshold for duplicate detection |
| `dry_run` | boolean | No | true | Preview without merging |
| `merge_strategy` | string | No | `"keep_newest"` | Merge strategy: `keep_newest`, `keep_oldest`, `keep_most_accessed` |
| `limit` | integer | No | 1000 | Maximum memories to process |
| `use_lsh` | boolean | No | true | Use LSH index for faster detection |

### Response

```json
{
  "namespace": "my-project",
  "dry_run": true,
  "duplicate_groups": [
    {
      "primary_id": "550e8400-e29b-41d4-a716-446655440000",
      "duplicate_ids": [
        "550e8400-e29b-41d4-a716-446655440001",
        "550e8400-e29b-41d4-a716-446655440002"
      ],
      "avg_similarity": 0.97
    }
  ],
  "total_duplicates": 2,
  "action": "preview"
}
```

### Example

```python
# Preview duplicates (dry run)
memory_deduplicate(
    namespace="my-project",
    similarity_threshold=0.95,
    dry_run=True
)

# Actually merge duplicates
memory_deduplicate(
    namespace="my-project",
    similarity_threshold=0.95,
    dry_run=False,
    merge_strategy="keep_newest"
)

# Fast detection with LSH
memory_deduplicate(
    namespace="my-project",
    use_lsh=True,
    limit=5000
)
```

---

## Search Scope

The `search_scope` parameter controls which namespaces are searched:

| Scope | Description |
|-------|-------------|
| `current` | Only search in the specified namespace |
| `shared` | Search in current namespace + `shared` namespace |
| `all` | Search across all namespaces |

---

## LSH Index

The LSH (Locality-Sensitive Hashing) index provides O(N) complexity for duplicate detection:

- **Without LSH**: O(N²) - compares every pair
- **With LSH**: O(N) - uses hash-based filtering

Recommended for:
- Large memory sets (1000+ memories)
- Regular deduplication tasks
- Real-time duplicate detection

---

## Best Practices

### Finding Similar Memories

1. **Start with high threshold** - Begin with 0.9+ to find near-duplicates
2. **Lower gradually** - Reduce to 0.7-0.8 for related content
3. **Use `exclude_linked`** - Avoid redundant suggestions

### Deduplication

1. **Always dry run first** - Preview before merging
2. **Use appropriate threshold**:
   - 0.95+ for exact duplicates
   - 0.90-0.95 for near-duplicates
   - 0.80-0.90 for similar content (be careful)
3. **Consider merge strategy**:
   - `keep_newest` - Preserve recent context
   - `keep_oldest` - Preserve original source
   - `keep_most_accessed` - Preserve important memories

---

## Related Links

- [Memory Tools](memory-tools.md)
- [Linking Tools](linking-tools.md)
- [Main README](../README.md)
