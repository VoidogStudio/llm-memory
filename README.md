# LLM Memory

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Persistent memory and knowledge management for LLMs via Model Context Protocol (MCP).

## Features

- **Semantic Search** - Vector similarity search with sqlite-vec
- **Multi-Tier Memory** - Short-term, long-term, and working memory
- **Knowledge Base** - Document chunking and retrieval
- **Agent Communication** - Message passing between agents
- **Flexible Embeddings** - Local (Sentence Transformers) or OpenAI

## Installation

```bash
pip install llm-memory[local]   # With local embeddings
pip install llm-memory[openai]  # With OpenAI embeddings
pip install llm-memory[all]     # All features
```

## Quick Start

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
| `memory_store` | Store memory with automatic embedding |
| `memory_search` | Semantic similarity search |
| `memory_get` | Get memory by ID |
| `memory_update` | Update content, tags, metadata |
| `memory_delete` | Delete by ID, tier, or age |
| `memory_list` | List with filtering and pagination |

### Knowledge Base (2)

| Tool | Description |
|------|-------------|
| `knowledge_import` | Import documents with chunking |
| `knowledge_query` | Query with semantic search |

### Agent Communication (6)

| Tool | Description |
|------|-------------|
| `agent_register` | Register agent with ID and name |
| `agent_get` | Get agent information |
| `agent_send_message` | Send direct or broadcast message |
| `agent_receive_messages` | Receive messages |
| `context_share` | Share context with access control |
| `context_read` | Read shared context |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MEMORY_DB_PATH` | `./data/memory.db` | Database path |
| `LLM_MEMORY_EMBEDDING_PROVIDER` | `local` | `local` or `openai` |
| `LLM_MEMORY_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Local model |
| `OPENAI_API_KEY` | - | For OpenAI embeddings |

## Usage

```python
# Store a memory
memory_store(
    content="User prefers dark mode",
    memory_tier="long_term",
    tags=["preferences", "ui"]
)

# Search memories
memory_search(query="user preferences", top_k=5)

# Import document to knowledge base
knowledge_import(
    title="API Docs",
    content=document_text,
    chunk_size=500
)

# Query knowledge base
knowledge_query(query="authentication")

# Register and use agents
agent_register(agent_id="coder", name="Coding Agent")
agent_send_message(
    sender_id="coder",
    receiver_id="reviewer",
    content="Code ready for review"
)
```

## Architecture

### Memory Tiers

- **short_term** - Temporary with TTL (auto-expires)
- **long_term** - Persistent storage
- **working** - Active session context

### Technical Stack

- SQLite + sqlite-vec for vector operations
- Async I/O with aiosqlite
- Pydantic models
- Python 3.10+ (3.14 compatible)

## Development

```bash
git clone https://github.com/VoidogStudio/llm-memory.git
cd llm-memory
pip install -e .[dev]
pytest
```

## Limitations

- Recommended max: 100,000 memories
- Single writer (SQLite limitation)
- Chunk size: 2000 chars max

## License

MIT

## Links

- [Source](https://github.com/VoidogStudio/llm-memory)
- [Issues](https://github.com/VoidogStudio/llm-memory/issues)
- [MCP Specification](https://modelcontextprotocol.io/)
