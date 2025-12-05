# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-12-05

First public release.

### Added

**Memory Management (6 tools)**

- `memory_store` - Store memories with automatic embedding generation
- `memory_search` - Semantic similarity search
- `memory_get` - Retrieve memory by ID
- `memory_update` - Update content, tags, or metadata
- `memory_delete` - Delete by ID, tier, or age
- `memory_list` - List with filtering and pagination

**Knowledge Base (2 tools)**

- `knowledge_import` - Import documents with automatic chunking
- `knowledge_query` - Query with semantic search

**Agent Communication (6 tools)**

- `agent_register` - Register agent with ID, name, description
- `agent_get` - Get agent information
- `agent_send_message` - Send direct or broadcast messages
- `agent_receive_messages` - Receive and manage messages
- `context_share` - Share context with access control
- `context_read` - Read shared context

**Core Features**

- Multi-tier memory architecture (short_term, long_term, working)
- Multimodal content support (text, code, json, yaml, image)
- Local embeddings via Sentence Transformers (all-MiniLM-L6-v2)
- OpenAI embeddings support (text-embedding-3-small)
- SQLite + sqlite-vec for vector operations
- Async I/O with aiosqlite
- Python 3.10-3.14 support

### Technical Details

- MCP protocol version 1.0.0
- Vector dimensions: 384 (local) / 1536 (OpenAI)

### Known Limitations

- Recommended max: 100,000 memories
- Single concurrent writer (SQLite)
- Maximum chunk size: 2000 characters

---

## Roadmap

### v0.2.0

- **Memory Consolidation** - Auto-summarize related memories to reduce redundancy
- **Importance Scoring** - Automatically prioritize memories based on access patterns
- **Hybrid Search** - Combine keyword and semantic search for better recall
- **Batch Operations** - Bulk store/delete/update for efficiency

### v0.3.0

- **Memory Decay** - Gradual forgetting of unused memories to reduce noise
- **Memory Linking** - Create associations between related memories
- **Smart Chunking** - Context-aware document splitting (by sections, paragraphs)
- **Export/Import** - Backup and restore memory databases

### v1.0.0

- **PostgreSQL Support** - pgvector backend for production scale
- **Memory Encryption** - Encrypt sensitive memories at rest
- **Multi-tenant** - Isolated memory spaces per user/session
- **Stable API** - Production-ready with backwards compatibility

---

[Unreleased]: https://github.com/VoidogStudio/llm-memory/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/VoidogStudio/llm-memory/releases/tag/v0.1.0
