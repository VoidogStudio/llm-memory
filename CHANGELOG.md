# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2025-12-06

### Added

- **Memory Decay** (`memory_decay_configure`, `memory_decay_run`, `memory_decay_status`)
  - Gradual forgetting of unused/low-importance memories
  - Configurable decay threshold and grace period
  - Dry-run mode for safe preview before deletion
  - Automatic decay logging with statistics

- **Memory Linking** (`memory_link`, `memory_unlink`, `memory_get_links`)
  - Create associations between related memories
  - Bidirectional links with automatic reverse creation
  - Link types: `related`, `parent`, `child`, `similar`, `reference`
  - Query links by direction (outgoing/incoming/both)

- **Smart Chunking** (enhanced `knowledge_import`)
  - Context-aware document splitting strategies
  - New `strategy` parameter: `fixed`, `sentence`, `paragraph`, `semantic`
  - Hierarchical section path tracking (markdown headers)
  - Previous/next chunk navigation metadata

- **Export/Import** (`database_export`, `database_import`)
  - Full database backup in JSONL format
  - Selective export with tier/date filters
  - Import modes: `replace` (full restore) or `merge` (incremental)
  - Conflict handling: `skip`, `update`, or `error`
  - Optional embedding regeneration on import

### Changed

- Database schema upgraded to v3 (automatic migration from v2)
- New tables: `memory_links`, `decay_config`, `decay_log`
- New columns in `knowledge_chunks`: `section_path`, `has_previous`, `has_next`
- Tool count increased from 19 to 27

### Technical Details

- 192 total tests (190 pass, 2 performance tests skipped)
- Backward compatible with v1.1.0 databases
- All v1.2.0 features available via MCP tools

---

## [1.1.0] - 2025-12-06

### Added

- **Memory Consolidation** (`memory_consolidate`)
  - Auto-summarize and merge related memories
  - Extractive summarization algorithm
  - Configurable preservation of original memories
  - Tag merging from source memories

- **Importance Scoring** (`memory_get_score`, `memory_set_score`)
  - Access pattern-based importance calculation
  - Recency + frequency scoring algorithm
  - Manual score override with audit trail
  - Access logging with rate limiting (60-second window)

- **Hybrid Search** (enhanced `memory_search`)
  - New `search_mode` parameter: `semantic`, `keyword`, `hybrid`
  - FTS5 full-text search for keyword matching
  - Reciprocal Rank Fusion (RRF) for result combining
  - `sort_by` parameter: `relevance`, `importance`, `created_at`
  - `keyword_weight` parameter for hybrid balance (0.0-1.0)

- **Batch Operations** (`memory_batch_store`, `memory_batch_update`)
  - Bulk store up to 100 memories in single call
  - Bulk update with `on_error` modes: `rollback`, `continue`, `stop`
  - Partial failure reporting

- **Japanese Tokenization Support** (optional)
  - SudachiPy morphological analysis for FTS5
  - Install with `pip install llm-memory[japanese]`
  - Automatic fallback to unicode61 tokenizer

### Changed

- Database schema upgraded to v2 (automatic migration)
- New tables: `memories_fts`, `memory_access_log`
- New columns: `importance_score`, `access_count`, `last_accessed_at`, `consolidated_from`
- Tool count increased from 14 to 19

### Technical Details

- 54 new tests (100% pass rate)
- Backward compatible with v1.0.0 databases
- Performance targets: batch 100 items < 5s, hybrid search < 500ms

---

## [1.0.0] - 2025-12-05

First stable release with comprehensive documentation and full test coverage.

### Added

- **Complete API Documentation** - Detailed docs for all 14 MCP tools
  - [Tools Reference](docs/tools/README.md)
  - [Memory Tools](docs/tools/memory-tools.md)
  - [Knowledge Tools](docs/tools/knowledge-tools.md)
  - [Agent Tools](docs/tools/agent-tools.md)

- **Full Verification Test Suite** - `tests/test_full_flow.py`
  - 19 comprehensive tests covering all tools
  - Cross-tool integration tests
  - Complete workflow simulation
  - TTL and cleanup verification

### Changed

- Enhanced README with comprehensive usage examples
- Improved configuration documentation
- Added architecture and content type documentation

### Fixed

- TTL auto-cleanup now runs reliably in background
- Datetime handling unified to UTC timezone
- Improved error messages with consistent format

---

## [0.1.0] - 2025-12-05

Initial public release.

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
- Maximum chunk size: 2,000 characters

---

## Roadmap

### v2.0.0

- **PostgreSQL Support** - pgvector backend for scale
- **Memory Encryption** - Encrypt sensitive data at rest
- **Multi-tenant** - Isolated memory spaces per user
- **Streaming** - Real-time memory updates

---

[Unreleased]: https://github.com/VoidogStudio/llm-memory/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/VoidogStudio/llm-memory/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/VoidogStudio/llm-memory/releases/tag/v0.1.0
