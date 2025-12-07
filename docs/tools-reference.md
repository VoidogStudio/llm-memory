# LLM Memory MCP Tools Reference

LLM Memory provides 32 MCP tools that give LLMs persistent memory, knowledge base, and inter-agent communication capabilities.

## Tool List

### Memory Management (11 tools)

Tools for storing, searching, updating, and deleting memories.

| Tool | Description | Documentation |
|------|-------------|---------------|
| `memory_store` | Store memory (auto-generates embeddings) | [Details](memory-tools.md#memory_store) |
| `memory_search` | Semantic/keyword/hybrid search | [Details](memory-tools.md#memory_search) |
| `memory_get` | Get memory by ID | [Details](memory-tools.md#memory_get) |
| `memory_update` | Update memory | [Details](memory-tools.md#memory_update) |
| `memory_delete` | Delete memory | [Details](memory-tools.md#memory_delete) |
| `memory_list` | List with filtering | [Details](memory-tools.md#memory_list) |
| `memory_batch_store` | Batch store multiple memories (max 100) | [Details](memory-tools.md#memory_batch_store) |
| `memory_batch_update` | Batch update multiple memories | [Details](memory-tools.md#memory_batch_update) |
| `memory_get_score` | Get importance score | [Details](memory-tools.md#memory_get_score) |
| `memory_set_score` | Manually set importance score | [Details](memory-tools.md#memory_set_score) |
| `memory_consolidate` | Consolidate and summarize related memories | [Details](memory-tools.md#memory_consolidate) |

Details: [Memory Tools](memory-tools.md)

### Memory Decay (3 tools) **v1.2.0**

Tools for managing automatic deletion (decay) of unused memories.

| Tool | Description | Documentation |
|------|-------------|---------------|
| `memory_decay_configure` | Configure decay settings | [Details](decay-tools.md#memory_decay_configure) |
| `memory_decay_run` | Run decay (dry-run supported) | [Details](decay-tools.md#memory_decay_run) |
| `memory_decay_status` | Get decay statistics | [Details](decay-tools.md#memory_decay_status) |

Details: [Decay Tools](decay-tools.md)

### Memory Linking (3 tools) **v1.2.0**

Tools for managing relationships between memories.

| Tool | Description | Documentation |
|------|-------------|---------------|
| `memory_link` | Create link between memories | [Details](linking-tools.md#memory_link) |
| `memory_unlink` | Delete link | [Details](linking-tools.md#memory_unlink) |
| `memory_get_links` | Get links | [Details](linking-tools.md#memory_get_links) |

Details: [Linking Tools](linking-tools.md)

### Similarity Tools (2 tools) **v1.4.0**

Tools for finding similar and duplicate memories.

| Tool | Description | Documentation |
|------|-------------|---------------|
| `memory_similar` | Find semantically similar memories | [Details](similarity-tools.md#memory_similar) |
| `memory_deduplicate` | Detect and merge duplicate memories | [Details](similarity-tools.md#memory_deduplicate) |

Details: [Similarity Tools](similarity-tools.md)

### Context Tools (3 tools) **v1.5.0**

Tools for building optimal memory context within token budgets.

| Tool | Description | Documentation |
|------|-------------|---------------|
| `memory_context_build` | Build optimal memory context within token budget | [Details](context-tools.md#memory_context_build) |
| `memory_cache_clear` | Clear the semantic cache | [Details](context-tools.md#memory_cache_clear) |
| `memory_cache_stats` | Get semantic cache statistics | [Details](context-tools.md#memory_cache_stats) |

Details: [Context Tools](context-tools.md)

### Knowledge Base (2 tools)

Tools for importing documents and performing semantic search.

| Tool | Description | Documentation |
|------|-------------|---------------|
| `knowledge_import` | Import document with smart chunking | [Details](knowledge-tools.md#knowledge_import) |
| `knowledge_query` | Semantic search in knowledge base | [Details](knowledge-tools.md#knowledge_query) |

Details: [Knowledge Tools](knowledge-tools.md)

### Export/Import (2 tools) **v1.2.0**

Tools for database backup and restore.

| Tool | Description | Documentation |
|------|-------------|---------------|
| `database_export` | Export database to JSONL | [Details](export-import-tools.md#database_export) |
| `database_import` | Import from JSONL | [Details](export-import-tools.md#database_import) |

Details: [Export/Import Tools](export-import-tools.md)

### Agent Communication (6 tools)

Tools for inter-agent messaging and context sharing.

| Tool | Description | Documentation |
|------|-------------|---------------|
| `agent_register` | Register agent | [Details](agent-tools.md#agent_register) |
| `agent_get` | Get agent info | [Details](agent-tools.md#agent_get) |
| `agent_send_message` | Send message | [Details](agent-tools.md#agent_send_message) |
| `agent_receive_messages` | Receive messages | [Details](agent-tools.md#agent_receive_messages) |
| `context_share` | Share context | [Details](agent-tools.md#context_share) |
| `context_read` | Read shared context | [Details](agent-tools.md#context_read) |

Details: [Agent Tools](agent-tools.md)

---

## Quick Start

### Basic Memory Operations

```python
# Store memory
memory_store(
    content="User prefers dark mode",
    memory_tier="long_term",
    tags=["preferences", "ui"]
)

# Semantic search
memory_search(query="user preferences", top_k=5)

# Get memory
memory_get(id="550e8400-e29b-41d4-a716-446655440000")
```

### Basic Knowledge Base Operations

```python
# Import document
knowledge_import(
    title="API Documentation",
    content=document_text,
    category="docs",
    chunk_size=500
)

# Query
knowledge_query(query="authentication")
```

### Context Building Operations (v1.5.0)

```python
# Build optimal context within token budget
memory_context_build(
    query="user preferences",
    token_budget=4000,
    include_related=True,
    auto_summarize=True
)

# Get cache statistics
memory_cache_stats()

# Clear cache
memory_cache_clear()
```

### Basic Agent Communication Operations

```python
# Register agent
agent_register(agent_id="coder", name="Coding Agent")

# Send message
agent_send_message(
    sender_id="coder",
    receiver_id="reviewer",
    content="Code ready for review"
)

# Receive messages
agent_receive_messages(agent_id="reviewer")

# Share context
context_share(
    key="current_task",
    value={"status": "in_progress"},
    agent_id="director"
)
```

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           MCP Tools Layer (32 tools)                       │
├─────────────┬─────────────┬─────────────┬─────────────┬──────────────────┤
│ Memory (11) │ Decay (3)   │ Linking (3) │Similarity(2)│ Context (3)      │
│             │   v1.2.0    │   v1.2.0    │   v1.4.0    │   v1.5.0         │
├─────────────┴─────────────┴─────────────┴─────────────┴──────────────────┤
│  Knowledge (2)  │  Export/Import (2) v1.2.0  │  Agent Tools (6)          │
├───────────────────────────────────────────────────────────────────────────┤
│                           Services Layer                                   │
│  MemoryService │ DecayService │ LinkingService │ NamespaceService v1.4.0  │
│  ImportanceService │ ConsolidationService │ LSHIndex v1.4.0 │ AgentService│
│  ContextBuildingService v1.5.0 │ GraphTraversalService v1.5.0             │
│  SemanticCache v1.5.0 │ TokenCounter v1.5.0                               │
├───────────────────────────────────────────────────────────────────────────┤
│                          Repository Layer                                  │
│  MemoryRepo (+ FTS5, Hybrid Search, Namespace) │ KnowledgeRepo │ AgentRepo│
├───────────────────────────────────────────────────────────────────────────┤
│                           Database Layer                                   │
│      SQLite + sqlite-vec + FTS5 (Vector + Keyword) - Schema v5            │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Memory Tiers

| Tier | Description | Use Case |
|------|-------------|----------|
| `short_term` | Short-term memory | Temporary info with TTL |
| `long_term` | Long-term memory | Persistent important info |
| `working` | Working memory | Session work data |

### Content Types

| Type | Description |
|------|-------------|
| `text` | Plain text |
| `image` | Image reference |
| `code` | Source code |
| `json` | JSON data |
| `yaml` | YAML data |

### Message Types

| Type | Description |
|------|-------------|
| `direct` | One-to-one direct message |
| `broadcast` | Broadcast to all agents |
| `context` | Context update notification |

### Access Levels

| Level | Description |
|-------|-------------|
| `public` | Accessible by all agents |
| `restricted` | Accessible only by specified agents |

---

## Error Handling

All tools return a unified error format:

```json
{
  "error": true,
  "error_type": "ValidationError",
  "message": "Content cannot be empty"
}
```

### Error Types

| Type | Description |
|------|-------------|
| `ValidationError` | Input parameter validation error |
| `NotFoundError` | Specified resource not found |
| `BatchOperationError` | Error during batch operation (v1.3.0) |

---

## Limitations

| Item | Limit | Notes |
|------|-------|-------|
| Recommended max memories | 100,000 | |
| Concurrent writes | Single | SQLite limitation |
| Max chunk size | 2,000 characters | |
| `top_k` range | 1-1,000 | |
| `chunk_size` range | 100-10,000 | |
| Batch operation size | 1-1,000 | Configurable via `LLM_MEMORY_BATCH_MAX_SIZE` (v1.3.0) |
| Max content length | 1,000,000 chars | Configurable via `LLM_MEMORY_MAX_CONTENT_LENGTH` (v1.3.0) |

---

## Related Links

- [Memory Tools Details](memory-tools.md)
- [Decay Tools Details](decay-tools.md) (v1.2.0)
- [Linking Tools Details](linking-tools.md) (v1.2.0)
- [Similarity Tools Details](similarity-tools.md) (v1.4.0)
- [Context Tools Details](context-tools.md) (v1.5.0)
- [Knowledge Tools Details](knowledge-tools.md)
- [Export/Import Tools Details](export-import-tools.md) (v1.2.0)
- [Agent Tools Details](agent-tools.md)
- [Main README](../README.md)
