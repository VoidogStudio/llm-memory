# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.0] - 2025-12-09

### Added

- **Memory Versioning** (4 new tools) - Track and manage memory evolution
  - `memory_version_history` - Get complete version history with timestamps
  - `memory_version_get` - Retrieve specific memory version
  - `memory_version_rollback` - Restore memory to previous version
  - `memory_version_diff` - Compare two versions and view changes
  - Version tracking for all memory updates with automatic snapshots
  - Ability to roll back to any previous state

- **Structured Memory Schema** (5 new tools) - Define and enforce memory structure
  - `memory_schema_register` - Register custom memory schemas
  - `memory_schema_list` - List all registered schemas with metadata
  - `memory_schema_get` - Get detailed schema information
  - `memory_store_typed` - Store memory with schema validation
  - `memory_search_typed` - Search memories with type filtering
  - Schema-based validation and structure enforcement
  - Type-safe memory storage and retrieval

- **Dependency Tracking** (2 new tools + link extension) - Manage memory relationships and impacts
  - `memory_dependency_analyze` - Analyze impact of changes on dependent memories
  - `memory_dependency_propagate` - Automatically propagate updates to dependencies
  - Extended `memory_link` with cascade options (`cascade_on_update`, `cascade_on_delete`, `strength`)
  - New link types: `DEPENDS_ON`, `DERIVED_FROM`
  - Automatic notification of dependent memories
  - Circular dependency detection
  - Safe deletion with dependency awareness

### Changed

- **Database Migration** (v5 → v6)
  - New `memory_versions` table for version history storage
  - New `memory_schemas` table for schema definitions
  - New `dependency_notifications` table for tracking cascading changes
  - Added `version`, `previous_version_id`, `schema_id`, `structured_content` columns to `memories` table
  - Added `cascade_on_update`, `cascade_on_delete`, `strength` columns to `memory_links` table
  - New indexes: `idx_versions_memory`, `idx_schemas_namespace`, `idx_notifications_pending`
  - Migration includes backward compatibility for existing data

### Technical Details

- Total tools increased: 37 → 48 (+11 new tools)
- 402 total tests (399 passed, 3 skipped for performance)
- Test coverage: 80%+ for new features
- All new features include comprehensive error handling
- Automatic schema validation on typed memory operations
- Automatic version snapshots on memory updates

## [1.6.2] - 2025-12-08

### Improved

- **Code optimization** - Eliminated code duplication and improved performance
  - Extracted `_create_memory_from_item()` helper in `MemoryService` for batch operations
  - Extracted `_build_update_dict()` helper in `MemoryService` for update operations
  - Fixed N+1 query problem in `find_duplicates()` by batch fetching embeddings
  - Consolidated repeated imports (numpy, LSHIndex) in `MemoryRepository`
  - Moved `TokenizationService` import to module level in `MemoryService`

### Documentation

- **Python version guidance** - Updated recommended Python version to 3.10-3.13
  - SudachiPy (Japanese tokenization) is not yet available for Python 3.14
  - Python 3.14 still works but uses default unicode61 tokenizer for all text

### Technical Details

- Reduced ~120 lines of duplicated code in batch operations
- O(1) embedding lookup in duplicate detection (was O(N) per memory)
- All 356 tests pass, 3 skipped, 0 warnings

## [1.6.1] - 2025-12-08

### Changed

- **Default embedding model** changed from `all-MiniLM-L6-v2` to `intfloat/multilingual-e5-small`
  - Better multilingual support (100+ languages including Japanese)
  - Same 384 dimensions, compatible with existing databases
  - E5 models use query/passage prefix handling internally (automatic)
  - Previous model still works via `LLM_MEMORY_EMBEDDING_MODEL=all-MiniLM-L6-v2`

### Fixed

- **FTS5 keyword search** - Fixed tokenization mismatch for English text
  - SudachiPy was incorrectly tokenizing pure English text (e.g., "FTS5" → "FTS 5")
  - Added CJK character detection to only use SudachiPy for Japanese/Chinese/Korean text
  - English text now correctly uses FTS5's unicode61 tokenizer

- **Test warnings** - Resolved all pytest warnings
  - Registered `performance` marker in pyproject.toml
  - Fixed SudachiPy deprecated `dict_type` parameter → `dict`
  - Removed unnecessary `@pytest.mark.asyncio` from synchronous tests

### Technical Details

- Added `is_query` parameter to `EmbeddingProvider.embed()` and `embed_batch()` methods
- E5 models automatically add "query: " prefix for search queries and "passage: " prefix for stored documents
- Non-E5 models ignore the prefix parameter for backward compatibility
- Added CJK regex pattern in `TokenizationService` for selective Japanese tokenization
- 356 total tests (all pass, 3 skipped, 0 warnings)
- Test coverage: 68%

## [1.6.0] - 2025-12-07

### Added

- **project_scan** (MCP tool) - Auto-scan project structure, configuration, and documentation
  - Automatic Python project detection (pyproject.toml, setup.py)
  - .gitignore pattern automatic application
  - Configuration file, README, and documentation extraction
  - Project metadata detection (name, version, description)

- **knowledge_sync** (MCP tool) - Sync external documentation sources
  - Local file and directory synchronization
  - Hash-based change detection for incremental sync
  - Support for bulk operations
  - Duplicate prevention across namespaces

- **session_learn** (MCP tool) - Record and deduplicate session learning content
  - 4 categories: error_resolution, design_decision, best_practice, user_preference
  - Automatic similarity detection for deduplication
  - Duplicate prevention mechanism
  - Tagging and filtering by category

- **knowledge_check_staleness** (MCP tool) - Detect stale or outdated knowledge
  - Source file change detection
  - Access time-based staleness judgment
  - AND/OR condition support
  - Configurable freshness threshold

- **knowledge_refresh_stale** (MCP tool) - Update, archive, or delete stale knowledge
  - Stale memory refresh from source
  - Archival with metadata preservation
  - Safe deletion with dry-run support
  - Batch operations

### Changed

- **Configuration** (`src/config/settings.py`)
  - Added `default_namespace` for consistent namespace handling
  - Added `namespace_auto_detect` toggle
  - Added acquisition service settings: `project_scan_enabled`, `knowledge_sync_interval_seconds`
  - Added staleness detection settings: `staleness_threshold_days`, `staleness_enable`

- **Server** (`src/server.py`)
  - Added acquisition tools registration
  - Integrated session learning service

- **Memory Repository** (`src/db/repositories/memory_repository.py`)
  - Added `source_path` field support for knowledge tracking
  - Added staleness query methods

### Dependencies

- Added `pathspec>=0.12.0` for .gitignore pattern matching
- Added `aiofiles>=24.1.0` for async file operations

### Technical Details

- 359 total tests (356 pass, 3 skipped)
- New modules: `project_scan_service.py`, `knowledge_sync_service.py`, `session_learning_service.py`, `staleness_service.py`
- New models: `acquisition.py` with 18 Pydantic classes
- New utilities: `file_scanner.py`, `config_parser.py`, `path_filter.py`, `file_hash_service.py`
- Test coverage: 66%

---

## [1.5.0] - 2025-12-07

### Added

- **memory_context_build** (MCP tool) - Build optimal memory context within token budget
  - Combines semantic search with related memory discovery
  - Automatic token counting with tiktoken (optional) or fallback estimation
  - Multiple sorting strategies: `relevance`, `importance`, `recency`
  - Configurable token buffer ratio (default 10%)

- **Auto-summarization** - Compress long memories to fit token budget
  - Token-aware extractive summarization
  - Preserves key information while reducing size
  - Integrated into context building workflow

- **Graph Traversal** - Collect related memories by following links
  - BFS (Breadth-First Search) algorithm for link traversal
  - Configurable max depth and max results
  - Link type filtering support
  - Circular reference detection

- **Semantic Cache** - Cache similar query results for performance
  - LSH-based similarity matching for cache lookup
  - Configurable TTL and max cache size
  - LRU eviction when cache is full
  - `memory_cache_clear` tool for cache invalidation
  - `memory_cache_stats` tool for monitoring

### Changed

- **Configuration** (`src/config/settings.py`)
  - Added cache settings: `cache_enabled`, `cache_max_size`, `cache_ttl_seconds`, `cache_similarity_threshold`
  - Added token settings: `token_counter_model`, `token_buffer_ratio`
  - Added graph settings: `graph_max_depth`, `graph_max_results`

- **Summarization** (`src/utils/summarization.py`)
  - Added `extractive_summary_by_tokens()` for token-based summarization
  - CJK-aware token estimation

### Technical Details

- 295 total tests (295 pass, 3 skipped)
- New modules: `token_counter.py`, `graph_traversal_service.py`, `semantic_cache.py`, `context_building_service.py`, `context_tools.py`
- New model: `context.py` with `ContextMemory`, `ContextResult`, `CacheEntry`, `CacheStats`
- Optional dependency: `tiktoken>=0.5.0` for accurate token counting
- Test coverage: 69%

---

## [1.4.1] - 2025-12-07

### Changed

- **Source Structure Simplification**
  - Moved `src/llm_memory/` contents directly to `src/`
  - Simplified import paths and project structure
  - Updated pyproject.toml entry point: `src.__main__:cli`

- **Documentation Structure Simplification**
  - Moved `docs/tools/` contents directly to `docs/`
  - Renamed `docs/tools/README.md` to `docs/tools-reference.md`
  - Updated all internal documentation links

---

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

- **Memory Model** (`src/models/memory.py`)
  - Added `namespace` field (defaults to auto-detected value)
  - Added `SearchScope` enum: `current`, `shared`, `all`
  - Memory operations now namespace-aware

- **Memory Repository** (`src/db/repositories/memory_repository.py`)
  - Added `namespace` parameter to all query methods
  - Added `search_similar()` method for similarity detection
  - Added `find_duplicates()` method using LSH index
  - Duplicate detection with configurable threshold

- **Memory Tools** (`src/tools/memory_tools.py`)
  - All memory tools now accept `namespace` parameter
  - `namespace` is auto-detected if not provided
  - Supports `shared` namespace for cross-project sharing

- **Configuration** (`src/config/settings.py`)
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

- **Validation Utilities** (`src/utils/validators.py`)
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

### v1.8.0 - Enhanced Memory Intelligence

- **Memory Clustering** - Automatic grouping of related memories
- **Smart Tags** - AI-assisted tag suggestions
- **Conflict Detection** - Alert on contradictory information
- **Memory Analytics** - Usage patterns and insights dashboard

### v2.0.0 - Enterprise Features

- **PostgreSQL** - pgvector backend for horizontal scaling
- **Memory encryption** - Field-level encryption for sensitive data
- **Multi-tenant** - Isolated memory spaces with access control
- **Streaming** - Real-time memory updates via SSE/WebSocket
- **TUI dashboard** - Terminal UI for management
- **Audit logging** - Track memory access history
- **Conflict detection** - Alert on contradictory information

---

[1.7.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.6.2...v1.7.0
[1.6.2]: https://github.com/VoidogStudio/llm-memory/compare/v1.6.1...v1.6.2
[1.6.1]: https://github.com/VoidogStudio/llm-memory/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.4.1...v1.5.0
[1.4.1]: https://github.com/VoidogStudio/llm-memory/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/VoidogStudio/llm-memory/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/VoidogStudio/llm-memory/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/VoidogStudio/llm-memory/releases/tag/v0.1.0
