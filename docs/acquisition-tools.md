# Acquisition Tools

Acquisition Tools are a set of tools for automatically acquiring, syncing, and maintaining knowledge from projects and sessions.

## Overview

| Tool | Description |
|------|-------------|
| `project_scan` | Scan project directory and extract knowledge **v1.6.0** |
| `knowledge_sync` | Sync external documentation sources **v1.6.0** |
| `session_learn` | Record session learnings with deduplication **v1.6.0** |
| `knowledge_check_staleness` | Detect stale or outdated knowledge **v1.6.0** |
| `knowledge_refresh_stale` | Refresh, archive, or delete stale knowledge **v1.6.0** |

---

## project_scan

Scans a project directory and extracts knowledge from source files, configuration, and documentation. Automatically detects project type and applies appropriate .gitignore patterns.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Path to project directory to scan |
| `namespace` | string | No | project name | Target namespace for stored knowledge |
| `include_patterns` | string[] | No | `null` | Additional file patterns to include (gitignore format) |
| `exclude_patterns` | string[] | No | `null` | Additional file patterns to exclude (gitignore format) |
| `max_file_size_kb` | integer | No | `100` | Maximum file size to process in KB (1-10000) |
| `force_rescan` | boolean | No | `false` | Force rescan even if already scanned |

### Response

```json
{
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_path": "/path/to/project",
  "namespace": "my-project",
  "status": "completed",
  "statistics": {
    "files_scanned": 42,
    "files_skipped": 15,
    "memories_created": 38,
    "memories_updated": 4,
    "total_size_bytes": 125000
  },
  "detected_config": {
    "project_type": "python",
    "project_name": "my-project",
    "version": "1.0.0",
    "description": "My project description"
  },
  "scanned_at": "2025-12-07T12:00:00Z"
}
```

### Example

```python
# Basic project scan
project_scan(
    project_path="/path/to/my-project"
)

# Scan with custom patterns
project_scan(
    project_path="/path/to/project",
    namespace="custom-namespace",
    include_patterns=["*.sql", "*.graphql"],
    exclude_patterns=["*_test.py", "*.spec.ts"],
    max_file_size_kb=500,
    force_rescan=True
)
```

---

## knowledge_sync

Syncs knowledge from external documentation sources. Supports local files/directories with hash-based change detection for incremental updates.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source_type` | string | Yes | - | Source type: `local_file`, `local_directory`, `url`, `github_repo` |
| `source_path` | string | Yes | - | Path or URL to the source |
| `namespace` | string | No | auto-detect | Target namespace |
| `category` | string | No | `"external_docs"` | Document category for organization |
| `include_patterns` | string[] | No | `null` | File patterns to include (for directories) |
| `exclude_patterns` | string[] | No | `null` | File patterns to exclude (for directories) |
| `chunk_size` | integer | No | `500` | Characters per chunk (50-5000) |
| `chunk_overlap` | integer | No | `50` | Overlap between chunks |
| `update_mode` | string | No | `"smart"` | Update mode: `smart` (only changed) or `full` (all) |

### Source Types

| Type | Description | Status |
|------|-------------|--------|
| `local_file` | Single local file | Implemented |
| `local_directory` | Local directory (recursive) | Implemented |
| `url` | Remote URL | Not implemented (v1.7.0) |
| `github_repo` | GitHub repository | Not implemented (v1.7.0) |

### Response

```json
{
  "sync_id": "660e8400-e29b-41d4-a716-446655440001",
  "source_type": "local_directory",
  "source_path": "./docs",
  "namespace": "my-project",
  "status": "completed",
  "statistics": {
    "documents_processed": 12,
    "documents_added": 8,
    "documents_updated": 3,
    "documents_unchanged": 1,
    "chunks_created": 45
  },
  "documents": [
    {
      "path": "docs/readme.md",
      "status": "added",
      "chunks": 5,
      "hash": "abc123..."
    }
  ],
  "synced_at": "2025-12-07T12:00:00Z"
}
```

### Example

```python
# Sync a single file
knowledge_sync(
    source_type="local_file",
    source_path="./README.md"
)

# Sync a directory with custom chunking
knowledge_sync(
    source_type="local_directory",
    source_path="./docs",
    category="documentation",
    include_patterns=["*.md", "*.rst"],
    exclude_patterns=["_build/*"],
    chunk_size=1000,
    chunk_overlap=100,
    update_mode="smart"
)
```

---

## session_learn

Records learning content from the current session with automatic deduplication. Detects similar existing learnings and prevents duplicates.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `content` | string | Yes | - | Learning content to record |
| `category` | string | Yes | - | Learning category (see below) |
| `context` | string | No | `null` | Additional context about the learning |
| `confidence` | float | No | `0.8` | Confidence score (0.0-1.0) |
| `namespace` | string | No | auto-detect | Target namespace |
| `related_files` | string[] | No | `null` | List of related file paths |
| `tags` | string[] | No | `null` | Additional tags for categorization |

### Learning Categories

| Category | Description |
|----------|-------------|
| `error_resolution` | Solutions to errors and debugging insights |
| `design_decision` | Architectural and design choices |
| `best_practice` | Coding patterns and conventions |
| `user_preference` | User-specific preferences and settings |

### Response

```json
{
  "learning_id": "770e8400-e29b-41d4-a716-446655440002",
  "memory_id": "880e8400-e29b-41d4-a716-446655440003",
  "content": "pytest実行時のImportError解決方法...",
  "category": "error_resolution",
  "action": "created",
  "similar_learnings": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440004",
      "content": "Similar learning...",
      "similarity": 0.72,
      "category": "error_resolution"
    }
  ],
  "recorded_at": "2025-12-07T12:00:00Z"
}
```

### Action Values

| Action | Description |
|--------|-------------|
| `created` | New learning was created |
| `updated` | Existing similar learning was updated |
| `skipped` | Too similar to existing learning, skipped |

### Example

```python
# Record an error resolution
session_learn(
    content="pytest ImportError: sys.path issue resolved by adding __init__.py to test directories",
    category="error_resolution",
    context="Encountered during test setup",
    confidence=0.9,
    related_files=["tests/conftest.py", "tests/__init__.py"],
    tags=["pytest", "import", "testing"]
)

# Record a design decision
session_learn(
    content="Chose SQLite over PostgreSQL for single-user CLI tool to simplify deployment",
    category="design_decision",
    context="Architecture review session",
    confidence=0.95,
    tags=["database", "architecture"]
)
```

---

## knowledge_check_staleness

Checks for stale or outdated knowledge based on source file changes and access patterns. Uses AND logic: items are stale when source has changed AND not accessed recently.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `namespace` | string | No | `null` | Target namespace (null for all) |
| `stale_days` | integer | No | `30` | Days threshold for staleness (>=1) |
| `check_source_changes` | boolean | No | `true` | Check if source files changed |
| `categories` | string[] | No | `null` | Specific categories to check |
| `include_auto_scan` | boolean | No | `true` | Include project scan results |
| `include_sync` | boolean | No | `true` | Include synced knowledge |
| `include_learning` | boolean | No | `true` | Include session learnings |
| `limit` | integer | No | `100` | Maximum results (1-1000) |

### Response

```json
{
  "checked_at": "2025-12-07T12:00:00Z",
  "namespace": "my-project",
  "statistics": {
    "total_checked": 150,
    "stale_count": 12,
    "source_changed_count": 5,
    "not_accessed_count": 7
  },
  "stale_memories": [
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440005",
      "content_preview": "API authentication flow...",
      "source_path": "docs/auth.md",
      "reason": "source_changed",
      "last_accessed": "2025-11-01T10:00:00Z",
      "created_at": "2025-10-15T08:00:00Z"
    }
  ],
  "recommendations": [
    {
      "action": "refresh",
      "count": 5,
      "reason": "Source files have been modified"
    },
    {
      "action": "archive",
      "count": 7,
      "reason": "Not accessed in 30+ days"
    }
  ]
}
```

### Example

```python
# Basic staleness check
knowledge_check_staleness()

# Check with specific criteria
knowledge_check_staleness(
    namespace="my-project",
    stale_days=14,
    categories=["documentation", "code_comment"],
    include_learning=False,
    limit=50
)
```

---

## knowledge_refresh_stale

Takes action on stale knowledge items: refresh from source, archive (lower importance), or delete. Supports dry-run mode for safe preview.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `memory_ids` | string[] | No | `null` | Specific memory IDs (null for all stale) |
| `namespace` | string | No | `null` | Target namespace |
| `action` | string | No | `"refresh"` | Action to take (see below) |
| `dry_run` | boolean | No | `true` | Preview mode - no changes made |

### Actions

| Action | Description |
|--------|-------------|
| `refresh` | Re-import from source file (if available) |
| `archive` | Lower importance score to 0.1 |
| `delete` | Permanently delete the memory |

### Response

```json
{
  "action": "refresh",
  "dry_run": false,
  "namespace": "my-project",
  "statistics": {
    "processed": 5,
    "succeeded": 4,
    "failed": 1,
    "skipped": 0
  },
  "affected_memories": [
    {
      "id": "bb0e8400-e29b-41d4-a716-446655440006",
      "status": "refreshed",
      "source_path": "docs/api.md"
    },
    {
      "id": "cc0e8400-e29b-41d4-a716-446655440007",
      "status": "failed",
      "error": "Source file not found"
    }
  ],
  "processed_at": "2025-12-07T12:00:00Z"
}
```

### Example

```python
# Preview what would be refreshed (dry-run)
knowledge_refresh_stale(
    namespace="my-project",
    action="refresh",
    dry_run=True
)

# Actually refresh stale items
knowledge_refresh_stale(
    namespace="my-project",
    action="refresh",
    dry_run=False
)

# Archive specific memories
knowledge_refresh_stale(
    memory_ids=["id1", "id2", "id3"],
    action="archive",
    dry_run=False
)

# Delete old learnings
knowledge_refresh_stale(
    namespace="my-project",
    action="delete",
    dry_run=False
)
```

---

## Workflow Examples

### Initial Project Setup

```python
# 1. Scan project to import structure and docs
project_scan(project_path="/path/to/project")

# 2. Sync additional external documentation
knowledge_sync(
    source_type="local_directory",
    source_path="./external-docs"
)
```

### Ongoing Learning Capture

```python
# Record insights as you work
session_learn(
    content="Custom hook pattern for state management",
    category="best_practice",
    related_files=["src/hooks/useCustomState.ts"]
)
```

### Knowledge Maintenance

```python
# 1. Check for stale knowledge
result = knowledge_check_staleness(stale_days=14)

# 2. Preview refresh action
knowledge_refresh_stale(action="refresh", dry_run=True)

# 3. Execute refresh
knowledge_refresh_stale(action="refresh", dry_run=False)
```

---

## Error Handling

All tools return errors in a unified format:

```json
{
  "error": true,
  "error_type": "ValidationError",
  "message": "project_path cannot be empty"
}
```

### Error Types

| Type | Description |
|------|-------------|
| `ValidationError` | Invalid input parameter |
| `FileNotFoundError` | File or directory not found |
| `NotImplementedError` | Feature not yet implemented |
| `ScanError` | Error during project scan |
| `SyncError` | Error during knowledge sync |
| `LearningError` | Error recording learning |
| `StalenessCheckError` | Error checking staleness |
| `RefreshError` | Error refreshing knowledge |
