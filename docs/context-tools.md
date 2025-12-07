# Context Tools

Context Tools are a set of tools for building optimal memory context within token budgets, with intelligent caching and related memory discovery.

## Overview

| Tool | Description |
|------|-------------|
| `memory_context_build` | Build optimal memory context within token budget **v1.5.0** |
| `memory_cache_clear` | Clear the semantic cache **v1.5.0** |
| `memory_cache_stats` | Get semantic cache statistics **v1.5.0** |

---

## memory_context_build

Builds an optimal set of memories within a specified token budget. Combines semantic search with related memory discovery via graph traversal, and optionally summarizes long memories to fit the budget.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query for finding relevant memories |
| `token_budget` | integer | Yes | - | Maximum token count for the result |
| `top_k` | integer | No | `20` | Maximum number of memories to consider |
| `include_related` | boolean | No | `true` | Include related memories via link traversal |
| `max_depth` | integer | No | `2` | Maximum link traversal depth (1-5) |
| `auto_summarize` | boolean | No | `true` | Automatically summarize long memories |
| `min_similarity` | float | No | `0.5` | Minimum similarity threshold (0.0-1.0) |
| `namespace` | string | No | auto-detect | Memory namespace |
| `use_cache` | boolean | No | `true` | Use semantic cache for results |
| `strategy` | string | No | `"relevance"` | Sorting strategy |

### Strategy Options

| Strategy | Description |
|----------|-------------|
| `relevance` | Sort by semantic similarity score (default) |
| `importance` | Sort by memory importance score |
| `recency` | Sort by creation time (newest first) |

### Response

```json
{
  "memories": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "User prefers dark mode",
      "tokens": 5,
      "similarity": 0.92,
      "source": "direct",
      "summarized": false
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "content": "Related UI preference...",
      "tokens": 12,
      "similarity": 0.85,
      "source": "related",
      "summarized": false
    }
  ],
  "total_tokens": 17,
  "token_budget": 1000,
  "memory_count": 2,
  "cache_hit": false,
  "truncated": false
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `memories` | array | List of context memories |
| `memories[].id` | string | Memory ID |
| `memories[].content` | string | Memory content (possibly summarized) |
| `memories[].tokens` | integer | Token count for this memory |
| `memories[].similarity` | float | Similarity score to query |
| `memories[].source` | string | `"direct"` or `"related"` |
| `memories[].summarized` | boolean | Whether content was summarized |
| `total_tokens` | integer | Total tokens in result |
| `token_budget` | integer | Requested token budget |
| `memory_count` | integer | Number of memories returned |
| `cache_hit` | boolean | Whether result came from cache |
| `truncated` | boolean | Whether memories were truncated to fit budget |

### Example

```python
# Basic usage
memory_context_build(
    query="user preferences",
    token_budget=4000
)

# With related memories and custom strategy
memory_context_build(
    query="authentication flow",
    token_budget=8000,
    include_related=True,
    max_depth=3,
    strategy="importance",
    auto_summarize=True
)

# Without cache
memory_context_build(
    query="recent changes",
    token_budget=2000,
    use_cache=False,
    strategy="recency"
)
```

### Token Counting

Token counting uses one of two methods:

1. **tiktoken** (accurate) - If `tiktoken` is installed (`pip install llm-memory[tokenizer]`)
2. **Estimation** (fallback) - Character-based estimation with CJK awareness

A 10% buffer is applied by default to prevent budget overflow.

### Graph Traversal

When `include_related=true`, the tool performs BFS (Breadth-First Search) traversal of memory links:

1. Finds direct matches via semantic search
2. Traverses links from matched memories up to `max_depth` levels
3. Deduplicates and scores all discovered memories
4. Fits results within token budget

### Auto-summarization

When `auto_summarize=true` and a memory exceeds the remaining budget:

1. Extractive summarization is applied
2. Key sentences are preserved based on importance
3. Summarized content is marked with `summarized: true`

---

## memory_cache_clear

Clears the semantic cache. Use this when you want to force fresh results or after significant data changes.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pattern` | string | No | `null` | Optional pattern to match cache keys (not yet implemented) |

### Response

```json
{
  "cleared": true,
  "entries_removed": 42
}
```

### Example

```python
# Clear entire cache
memory_cache_clear()
```

---

## memory_cache_stats

Returns statistics about the semantic cache.

### Parameters

None.

### Response

```json
{
  "enabled": true,
  "size": 42,
  "max_size": 1000,
  "hit_count": 156,
  "miss_count": 89,
  "hit_rate": 0.637,
  "ttl_seconds": 3600,
  "memory_usage_bytes": 2048576
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Whether caching is enabled |
| `size` | integer | Current number of cache entries |
| `max_size` | integer | Maximum cache entries allowed |
| `hit_count` | integer | Number of cache hits |
| `miss_count` | integer | Number of cache misses |
| `hit_rate` | float | Cache hit rate (0.0-1.0) |
| `ttl_seconds` | integer | Time-to-live for cache entries |
| `memory_usage_bytes` | integer | Estimated memory usage |

### Example

```python
# Get cache statistics
stats = memory_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
```

---

## Configuration

Context tools can be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MEMORY_CACHE_ENABLED` | `true` | Enable/disable semantic cache |
| `LLM_MEMORY_CACHE_MAX_SIZE` | `1000` | Maximum cache entries |
| `LLM_MEMORY_CACHE_TTL_SECONDS` | `3600` | Cache entry TTL (1 hour) |
| `LLM_MEMORY_CACHE_SIMILARITY_THRESHOLD` | `0.95` | Similarity threshold for cache hits |
| `LLM_MEMORY_TOKEN_COUNTER_MODEL` | `"gpt-4"` | Model for tiktoken counting |
| `LLM_MEMORY_TOKEN_BUFFER_RATIO` | `0.1` | Buffer ratio (10%) |
| `LLM_MEMORY_GRAPH_MAX_DEPTH` | `3` | Default max traversal depth |
| `LLM_MEMORY_GRAPH_MAX_RESULTS` | `50` | Default max related memories |

---

## Use Cases

### LLM Context Window Optimization

```python
# Build context for Claude/GPT with 8K token limit
context = memory_context_build(
    query="current project status",
    token_budget=6000,  # Leave room for system prompt
    strategy="importance"
)

# Use in prompt
prompt = f"""
Based on the following context:
{[m['content'] for m in context['memories']]}

Answer the user's question...
"""
```

### RAG (Retrieval-Augmented Generation)

```python
# Get relevant context for RAG
context = memory_context_build(
    query=user_question,
    token_budget=4000,
    include_related=True,
    max_depth=2
)

# Pass to LLM
response = llm.generate(
    system="Answer based on the provided context.",
    context=context['memories'],
    question=user_question
)
```

### Cache Management

```python
# Monitor cache performance
stats = memory_cache_stats()
if stats['hit_rate'] < 0.5:
    print("Low cache hit rate - consider adjusting similarity threshold")

# Clear cache after bulk updates
memory_batch_store(memories=[...])
memory_cache_clear()
```

---

## Related Links

- [Tools Reference](tools-reference.md)
- [Memory Tools](memory-tools.md)
- [Linking Tools](linking-tools.md)
- [Similarity Tools](similarity-tools.md)
