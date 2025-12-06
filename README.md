# LLM Memory

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Persistent memory and knowledge management for LLMs via Model Context Protocol (MCP).

## Features

- **Semantic Search** - Vector similarity search with sqlite-vec (cosine distance)
- **Hybrid Search** - Combine keyword (FTS5) and semantic search
- **Multi-Tier Memory** - Short-term (with TTL), long-term, and working memory
- **Multi-Project Namespace** - Logical separation of memories per project (v1.4.0)
- **Auto-detection** - Automatic namespace from git URL or directory name (v1.4.0)
- **Cross-project Sharing** - Share knowledge via `shared` namespace (v1.4.0)
- **Similarity Detection** - Find similar and duplicate memories (v1.4.0)
- **LSH Index** - O(N) optimization for duplicate detection (v1.4.0)
- **Importance Scoring** - Access pattern-based memory prioritization
- **Memory Consolidation** - Auto-summarize related memories
- **Memory Decay** - Gradual forgetting of unused memories (v1.2.0)
- **Memory Linking** - Associations between related memories (v1.2.0)
- **Smart Chunking** - Context-aware document splitting (v1.2.0)
- **Export/Import** - Database backup and restore (v1.2.0)
- **Batch Operations** - Bulk store/update up to 100 memories
- **Knowledge Base** - Document chunking and retrieval
- **Agent Communication** - Message passing and context sharing between agents
- **Flexible Embeddings** - Local (Sentence Transformers) or OpenAI
- **Japanese Support** - Optional SudachiPy tokenization for FTS5
- **TTL Auto-Cleanup** - Automatic expiration of short-term memories

## Installation

```bash
git clone https://github.com/VoidogStudio/llm-memory.git
cd llm-memory
pip install -e ".[local]"      # With local embeddings (recommended)
# pip install -e ".[openai]"   # With OpenAI embeddings
# pip install -e ".[japanese]" # With Japanese tokenization (SudachiPy)
# pip install -e ".[all]"      # All features
```

Verify installation:

```bash
llm-memory --help
```

## MCP Server Setup

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "llm-memory": {
      "command": "llm-memory",
      "env": {
        "LLM_MEMORY_DB_PATH": "~/llm-memory/memory.db",
        "LLM_MEMORY_EMBEDDING_PROVIDER": "local"
      }
    }
  }
}
```

**For source install**, use full path to the command:

```json
{
  "mcpServers": {
    "llm-memory": {
      "command": "/path/to/llm-memory/.venv/bin/llm-memory",
      "env": {
        "LLM_MEMORY_DB_PATH": "~/llm-memory/memory.db",
        "LLM_MEMORY_EMBEDDING_PROVIDER": "local"
      }
    }
  }
}
```

### Claude Code

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "llm-memory": {
      "command": "llm-memory",
      "env": {
        "LLM_MEMORY_DB_PATH": "./data/memory.db",
        "LLM_MEMORY_EMBEDDING_PROVIDER": "local"
      }
    }
  }
}
```

## MCP Tools (29)

### Memory Management (11)

| Tool | Description |
|------|-------------|
| `memory_store` | Store memory with automatic embedding generation |
| `memory_search` | Semantic similarity search with filters |
| `memory_get` | Get memory by ID |
| `memory_update` | Update content, tags, metadata, or tier |
| `memory_delete` | Delete by ID, tier, or age |
| `memory_list` | List with filtering and pagination |
| `memory_batch_store` | Bulk store multiple memories (up to 100) |
| `memory_batch_update` | Bulk update multiple memories |
| `memory_get_score` | Get importance score for a memory |
| `memory_set_score` | Manually set importance score |
| `memory_consolidate` | Merge related memories with summarization |

### Memory Decay (3) - v1.2.0

| Tool | Description |
|------|-------------|
| `memory_decay_configure` | Configure decay settings (threshold, grace period) |
| `memory_decay_run` | Execute decay with dry-run support |
| `memory_decay_status` | Get decay statistics and configuration |

### Memory Linking (3) - v1.2.0

| Tool | Description |
|------|-------------|
| `memory_link` | Create bidirectional links between memories |
| `memory_unlink` | Remove links between memories |
| `memory_get_links` | Query links by direction and type |

### Similarity Tools (2) - v1.4.0

| Tool | Description |
|------|-------------|
| `memory_similar` | Find semantically similar memories |
| `memory_deduplicate` | Detect and merge duplicate memories |

### Knowledge Base (2)

| Tool | Description |
|------|-------------|
| `knowledge_import` | Import documents with smart chunking strategies |
| `knowledge_query` | Query with semantic search and filters |

### Export/Import (2) - v1.2.0

| Tool | Description |
|------|-------------|
| `database_export` | Export database to JSONL with filters |
| `database_import` | Import with merge/replace modes |

### Agent Communication (6)

| Tool | Description |
|------|-------------|
| `agent_register` | Register agent with ID, name, description |
| `agent_get` | Get agent information |
| `agent_send_message` | Send direct or broadcast message |
| `agent_receive_messages` | Receive and manage messages |
| `context_share` | Share context with access control |
| `context_read` | Read shared context |

## Configuration

All settings can be configured via environment variables with the `LLM_MEMORY_` prefix.

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MEMORY_DATABASE_PATH` | `./data/llm_memory.db` | Database file path |
| `LLM_MEMORY_EMBEDDING_PROVIDER` | `local` | `local` or `openai` |
| `LLM_MEMORY_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Local embedding model |
| `LLM_MEMORY_EMBEDDING_DIMENSIONS` | `384` | Embedding vector dimensions (1-4096) |
| `LLM_MEMORY_CLEANUP_INTERVAL_SECONDS` | `300` | TTL cleanup interval (min 60s) |
| `LLM_MEMORY_OPENAI_API_KEY` | - | Required for OpenAI embeddings |

### Performance Settings (v1.3.0)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MEMORY_BATCH_MAX_SIZE` | `100` | Maximum batch operation size (1-1000) |
| `LLM_MEMORY_SEARCH_DEFAULT_TOP_K` | `10` | Default search results (1-1000) |
| `LLM_MEMORY_EMBEDDING_BATCH_SIZE` | `32` | Embedding generation batch size |
| `LLM_MEMORY_MAX_CONTENT_LENGTH` | `1000000` | Max content length in chars (1MB) |

### Importance & Decay Settings (v1.3.0)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MEMORY_IMPORTANCE_MAX_ACCESSES` | `100` | Max access count for scoring |
| `LLM_MEMORY_ACCESS_LOG_RATE_LIMIT_SECONDS` | `60` | Rate limit for access logging |
| `LLM_MEMORY_RRF_CONSTANT` | `60` | Reciprocal Rank Fusion constant |

### Consolidation Settings (v1.3.0)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MEMORY_CONSOLIDATION_MIN_MEMORIES` | `2` | Min memories for consolidation |
| `LLM_MEMORY_CONSOLIDATION_MAX_MEMORIES` | `50` | Max memories per consolidation |

### Namespace Settings (v1.4.0)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MEMORY_DEFAULT_NAMESPACE` | `default` | Fallback namespace if auto-detection fails |
| `LLM_MEMORY_LSH_NUM_FUNCTIONS` | `5` | Number of LSH hash functions |
| `LLM_MEMORY_SIMILARITY_THRESHOLD` | `0.85` | Default similarity threshold |

## Usage Examples

### Memory Management

```python
# Store a memory with TTL (auto-expires)
memory_store(
    content="User prefers dark mode",
    memory_tier="short_term",
    ttl_seconds=3600,
    tags=["preferences", "ui"]
)

# Store long-term memory
memory_store(
    content="User's favorite programming language is Python",
    memory_tier="long_term",
    tags=["preferences", "coding"],
    metadata={"confidence": 0.95}
)

# Semantic search with filters
memory_search(
    query="user preferences",
    top_k=5,
    memory_tier="long_term",
    min_similarity=0.5
)

# Update memory tier (promote to long-term)
memory_update(
    id="memory-uuid",
    memory_tier="long_term"
)

# Delete old memories
memory_delete(older_than="2024-01-01T00:00:00Z")
```

### Hybrid Search (v1.1.0)

```python
# Keyword search (FTS5)
memory_search(
    query="dark mode settings",
    search_mode="keyword",
    top_k=10
)

# Hybrid search (keyword + semantic)
memory_search(
    query="user interface preferences",
    search_mode="hybrid",
    keyword_weight=0.3,  # 30% keyword, 70% semantic
    sort_by="importance"
)
```

### Batch Operations (v1.1.0)

```python
# Bulk store memories
memory_batch_store(
    items=[
        {"content": "First memory", "tags": ["batch"]},
        {"content": "Second memory", "tags": ["batch"]},
        {"content": "Third memory", "tags": ["batch"]}
    ],
    on_error="rollback"  # or "continue", "stop"
)

# Bulk update
memory_batch_update(
    updates=[
        {"id": "uuid-1", "tags": ["updated"]},
        {"id": "uuid-2", "metadata": {"reviewed": True}}
    ]
)
```

### Importance Scoring (v1.1.0)

```python
# Get importance score (based on access patterns)
memory_get_score(id="memory-uuid")

# Manually set score (0.0 - 1.0)
memory_set_score(
    id="memory-uuid",
    score=0.9,
    reason="Critical user preference"
)
```

### Memory Consolidation (v1.1.0)

```python
# Merge related memories into one
memory_consolidate(
    memory_ids=["uuid-1", "uuid-2", "uuid-3"],
    summary_strategy="extractive",
    preserve_originals=True,
    tags=["consolidated"]
)
```

### Memory Decay (v1.2.0)

```python
# Configure decay settings
memory_decay_configure(
    enabled=True,
    threshold=0.1,           # Delete memories with score < 0.1
    grace_period_days=7,     # Don't touch memories < 7 days old
    max_delete_per_run=100
)

# Preview what would be deleted (dry run)
memory_decay_run(dry_run=True)

# Execute decay
memory_decay_run(dry_run=False)

# Check decay status
memory_decay_status()
```

### Memory Linking (v1.2.0)

```python
# Create bidirectional link between memories
memory_link(
    source_id="uuid-1",
    target_id="uuid-2",
    link_type="related",     # related/parent/child/similar/reference
    bidirectional=True
)

# Get all links for a memory
memory_get_links(
    memory_id="uuid-1",
    direction="both"         # outgoing/incoming/both
)

# Remove link
memory_unlink(
    source_id="uuid-1",
    target_id="uuid-2"
)
```

### Namespace & Multi-Project (v1.4.0)

```python
# Store memory with explicit namespace
memory_store(
    content="Project-specific configuration",
    namespace="my-project",
    tags=["config"]
)

# Store to shared namespace (cross-project)
memory_store(
    content="Common coding guidelines",
    namespace="shared",
    tags=["guidelines"]
)

# Search within current namespace
memory_search(
    query="configuration",
    namespace="my-project",
    search_scope="current"
)

# Search including shared namespace
memory_search(
    query="guidelines",
    search_scope="shared"  # current + shared
)

# Search across all namespaces
memory_search(
    query="important",
    search_scope="all"
)
```

### Similarity & Deduplication (v1.4.0)

```python
# Find similar memories
memory_similar(
    memory_id="uuid-1",
    top_k=5,
    min_similarity=0.85
)

# Preview duplicates (dry run)
memory_deduplicate(
    namespace="my-project",
    similarity_threshold=0.95,
    dry_run=True
)

# Merge duplicates
memory_deduplicate(
    namespace="my-project",
    similarity_threshold=0.95,
    dry_run=False,
    merge_strategy="keep_newest"
)
```

### Smart Chunking (v1.2.0)

```python
# Import with semantic chunking
knowledge_import(
    title="Technical Documentation",
    content=markdown_content,
    strategy="semantic",     # fixed/sentence/paragraph/semantic
    chunk_size=500
)

# Import with paragraph-based chunking
knowledge_import(
    title="Article",
    content=article_text,
    strategy="paragraph"
)
```

### Export/Import (v1.2.0)

```python
# Export entire database
database_export(
    output_path="./backup.jsonl",
    include_embeddings=True
)

# Export with filters
database_export(
    output_path="./long_term_backup.jsonl",
    memory_tier="long_term",
    created_after="2025-01-01T00:00:00Z"
)

# Import (merge mode - add new, skip existing)
database_import(
    input_path="./backup.jsonl",
    mode="merge",
    on_conflict="skip"
)

# Import (replace mode - full restore)
database_import(
    input_path="./backup.jsonl",
    mode="replace"
)
```

### Knowledge Base

```python
# Import a document
knowledge_import(
    title="API Documentation",
    content=document_text,
    category="docs",
    chunk_size=500,
    chunk_overlap=50
)

# Query with category filter
knowledge_query(
    query="authentication methods",
    category="docs",
    top_k=3
)
```

### Agent Communication

```python
# Register agents
agent_register(agent_id="coder", name="Coding Agent")
agent_register(agent_id="reviewer", name="Review Agent")

# Send direct message
agent_send_message(
    sender_id="coder",
    receiver_id="reviewer",
    content="Code ready for review",
    metadata={"files_changed": 5}
)

# Broadcast to all agents
agent_send_message(
    sender_id="director",
    content="Starting new task",
    message_type="broadcast"
)

# Share context with access control
context_share(
    key="current_task",
    value={"task_id": "123", "status": "in_progress"},
    agent_id="director",
    access_level="restricted",
    allowed_agents=["coder", "reviewer"]
)

# Read shared context
context_read(key="current_task", agent_id="coder")
```

## Architecture

### Memory Tiers

| Tier | Description | Use Case |
|------|-------------|----------|
| `short_term` | Temporary with TTL | Session data, temporary context |
| `long_term` | Persistent storage | User preferences, important facts |
| `working` | Active session context | Current task state |

### Content Types

| Type | Description |
|------|-------------|
| `text` | Plain text (default) |
| `code` | Source code |
| `json` | JSON data |
| `yaml` | YAML data |
| `image` | Image reference |

### Technical Stack

- **Database**: SQLite + sqlite-vec for vector operations
- **Async I/O**: aiosqlite for non-blocking operations
- **Models**: Pydantic for data validation
- **Embeddings**: Sentence Transformers or OpenAI
- **Python**: 3.10 - 3.14 compatible

## Documentation

- [Tools Reference](docs/tools/README.md)
- [Memory Tools](docs/tools/memory-tools.md)
- [Decay Tools](docs/tools/decay-tools.md) (v1.2.0)
- [Linking Tools](docs/tools/linking-tools.md) (v1.2.0)
- [Similarity Tools](docs/tools/similarity-tools.md) (v1.4.0)
- [Knowledge Tools](docs/tools/knowledge-tools.md)
- [Export/Import Tools](docs/tools/export-import-tools.md) (v1.2.0)
- [Agent Tools](docs/tools/agent-tools.md)

## Development

```bash
git clone https://github.com/VoidogStudio/llm-memory.git
cd llm-memory
pip install -e .[dev]

# Run tests
pytest

# Run full verification flow
pytest tests/test_full_flow.py -v -s

# Lint
ruff check src/
```

## Limitations

- Recommended max: 100,000 memories
- Single concurrent writer (SQLite limitation, with async lock for safety)
- Maximum chunk size: 2,000 characters
- Embedding dimensions: 384 (local) / 1536 (OpenAI)

## License

MIT

## Links

- [Source](https://github.com/VoidogStudio/llm-memory)
- [Issues](https://github.com/VoidogStudio/llm-memory/issues)
- [Changelog](CHANGELOG.md)
- [MCP Specification](https://modelcontextprotocol.io/)
