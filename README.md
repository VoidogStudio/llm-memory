# LLM Memory

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Persistent memory and knowledge management for LLMs via Model Context Protocol (MCP).

## Features

- **Semantic Search** - Vector similarity search with sqlite-vec
- **Multi-Tier Memory** - Short-term (with TTL), long-term, and working memory
- **Knowledge Base** - Document chunking and retrieval
- **Agent Communication** - Message passing and context sharing between agents
- **Flexible Embeddings** - Local (Sentence Transformers) or OpenAI
- **TTL Auto-Cleanup** - Automatic expiration of short-term memories

## Installation

```bash
git clone https://github.com/VoidogStudio/llm-memory.git
cd llm-memory
pip install -e ".[local]"   # With local embeddings (recommended)
# pip install -e ".[openai]"  # With OpenAI embeddings
# pip install -e ".[all]"     # All features
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

## MCP Tools (14)

### Memory Management (6)

| Tool | Description |
|------|-------------|
| `memory_store` | Store memory with automatic embedding generation |
| `memory_search` | Semantic similarity search with filters |
| `memory_get` | Get memory by ID |
| `memory_update` | Update content, tags, metadata, or tier |
| `memory_delete` | Delete by ID, tier, or age |
| `memory_list` | List with filtering and pagination |

### Knowledge Base (2)

| Tool | Description |
|------|-------------|
| `knowledge_import` | Import documents with automatic chunking |
| `knowledge_query` | Query with semantic search and filters |

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

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MEMORY_DB_PATH` | `./data/memory.db` | Database file path |
| `LLM_MEMORY_EMBEDDING_PROVIDER` | `local` | `local` or `openai` |
| `LLM_MEMORY_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Local embedding model |
| `LLM_MEMORY_EMBEDDING_DIMENSIONS` | `384` | Embedding vector dimensions |
| `LLM_MEMORY_CLEANUP_INTERVAL` | `300` | TTL cleanup interval (seconds) |
| `OPENAI_API_KEY` | - | Required for OpenAI embeddings |

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
- [Knowledge Tools](docs/tools/knowledge-tools.md)
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
- Single concurrent writer (SQLite limitation)
- Maximum chunk size: 2,000 characters
- Embedding dimensions: 384 (local) / 1536 (OpenAI)

## License

MIT

## Links

- [Source](https://github.com/VoidogStudio/llm-memory)
- [Issues](https://github.com/VoidogStudio/llm-memory/issues)
- [Changelog](CHANGELOG.md)
- [MCP Specification](https://modelcontextprotocol.io/)
