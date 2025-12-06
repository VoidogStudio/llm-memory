# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.0] - 2025-12-07

### Added

- **Namespace** - Logical separation of memories per project
  - Namespace isolation prevents cross-project contamination
  - Each project can have isolated memory space
  - Configurable namespace detection from git URL or directory name

- **Auto-detection** - Automatic namespace from project context
  - Detects namespace from git remote URL
  - Falls back to directory name-based namespace
  - Manual namespace override via `namespace` parameter

- **Cross-project sharing** - Share knowledge via `shared` namespace
  - Special `shared` namespace for common memories
  - Memories in `shared` namespace accessible to all projects
  - Enables knowledge reuse across project boundaries

- **memory_similar** (MCP tool) - Find similar memories
  - Detects semantically similar memories across namespace
  - Uses configurable similarity threshold (default 0.85)
  - Returns ordered list of similar memories with scores

- **memory_deduplicate** (MCP tool) - Detect and merge duplicate memories
  - Identifies duplicate memories using LSH index
  - Automatic merging with tag consolidation
  - Dry-run mode for safe preview before merge

- **LSH Index** - O(N) optimization for duplicate detection
  - Locality-Sensitive Hashing for fast similarity detection
  - Configurable number of hash functions
  - Significantly faster duplicate detection for large memory sets

### Changed

- **Database Schema v5**
  - Added `namespace` column to `memories` table
  - Added indexes: `idx_memories_namespace`, `idx_memories_namespace_created_at`
  - Automatic migration preserves all existing data with default namespace
  - New databases use namespace from initial creation

- **Memory Model** (`src/llm_memory/models/memory.py`)
  - Added `namespace` field (defaults to auto-detected value)
  - Added `SearchScope` enum: `current`, `shared`, `all`
  - Memory operations now namespace-aware

- **Memory Repository** (`src/llm_memory/db/repositories/memory_repository.py`)
  - Added `namespace` parameter to all query methods
  - Added `search_similar()` method for similarity detection
  - Added `find_duplicates()` method using LSH index
  - Duplicate detection with configurable threshold

- **Memory Tools** (`src/llm_memory/tools/memory_tools.py`)
  - All memory tools now accept `namespace` parameter
  - `namespace` is auto-detected if not provided
  - Supports `shared` namespace for cross-project sharing

- **Configuration** (`src/llm_memory/config/settings.py`)
  - Added namespace-related settings:
    - `default_namespace`: Fallback namespace if not auto-detected
    - `lsh_num_functions`: Number of LSH hash functions (default 5)
    - `similarity_threshold`: Threshold for memory similarity (default 0.85)

### Technical Details

- 193 total tests (191 pass, 2 skipped)
- Added 3 new service modules:
  - `NamespaceService`: Namespace detection and management
  - `LSHIndex`: Locality-Sensitive Hashing implementation
  - `similarity_tools`: MCP tools for similarity and deduplication
- Backward compatible with v1.3.0 databases
- Automatic namespace assignment to existing memories

---

## [1.3.0] - 2025-12-06

### Fixed

- **Transaction Conflict Error** (Critical)
  - Fixed "cannot start a transaction within a transaction" error under high load
  - Added `asyncio.Lock` for exclusive write access
  - Added transaction nesting detection to prevent double `BEGIN` statements
  - Affected tools: `memory_store`, `memory_batch_store`, `memory_batch_update`, `database_import`

- **Similarity Score Returns 0**
  - Fixed similarity scores incorrectly returning 0 for dissimilar content
  - Switched from L2 distance to cosine distance metric (`distance_metric=cosine`)
  - Similarity now correctly ranges 0.0-1.0 (0=opposite, 1=identical)
  - Added database migration v4 for existing databases

### Changed

- **Database Schema v4**
  - Recreated `embeddings` and `chunk_embeddings` virtual tables with cosine distance
  - Automatic migration preserves all existing data
  - New databases use cosine distance from initial creation

- **Configuration Improvements**
  - Added new configurable settings: `batch_max_size`, `max_content_length`, `rrf_constant`, `importance_max_accesses`, `consolidation_min_memories`, `consolidation_max_memories`, `access_log_rate_limit_seconds`
  - Added Pydantic `model_validator` for cross-field validation (OpenAI API key requirement, consolidation min/max consistency)
  - Added range validation (`ge`, `le`) for all numeric settings
  - Replaced hardcoded magic numbers with configurable settings

- **Global Settings Access**
  - Added `get_settings()`, `set_settings()`, `reset_settings()` functions for dependency injection
  - Services now read configuration from global settings singleton

- **Type Safety Improvements**
  - Explicit list conversion in `embeddings/openai.py` for type safety
  - Proper error handling in `embeddings/local.py` dimensions() instead of silent fallback

- **Error Handling Improvements**
  - More specific exception catching in `batch_tools.py` (ValueError, NotFoundError, OSError, RuntimeError)
  - Added logging for error diagnosis in batch operations
  - Replaced silent `except: pass` with debug logging in `server.py`

### Added

- **Validation Utilities** (`src/llm_memory/utils/validators.py`)
  - `validate_uuid()` - UUID format validation
  - `validate_content()` - Content validation with size limits
  - `validate_memory_tier()` - Memory tier enum validation
  - `validate_tags()` - Tag list normalization
  - `validate_positive_int()` - Range-bounded integer validation
  - `validate_batch_ids()` - Batch ID list validation

### Technical Details

- 193 total tests (all pass)
- Bandit security scan: 16 MEDIUM (all are parameterized queries, no actual risk)
- Ruff lint: All checks pass
- Test coverage: 69%

---

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

### v1.5.0 - Intelligent Context

- **memory_context_build** - Build optimal memory set within token budget
- **Auto-summarization** - Compress long memories to specified token count
- **Graph traversal** - Collect related memories by following links
- **Semantic cache** - Cache similar query results and LLM responses

### v1.6.0 - Auto Knowledge Acquisition

- **Project scan** - Auto-import README, docs/, code comments
- **knowledge_sync** - Watch directory and auto-import on changes
- **Session learning** - Auto-extract learnings from conversations
- **Staleness detection** - Auto-mark outdated memories

### v2.0.0 - Enterprise Features

- **PostgreSQL** - pgvector backend for horizontal scaling
- **Memory encryption** - Field-level encryption for sensitive data
- **Multi-tenant** - Isolated memory spaces with access control
- **Streaming** - Real-time memory updates via SSE/WebSocket
- **TUI dashboard** - Terminal UI for management
- **Audit logging** - Track memory access history
- **Conflict detection** - Alert on contradictory information

---

[Unreleased]: https://github.com/VoidogStudio/llm-memory/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/VoidogStudio/llm-memory/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/VoidogStudio/llm-memory/releases/tag/v0.1.0
