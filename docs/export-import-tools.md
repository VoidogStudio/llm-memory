# Export/Import Tools

Export/Import Tools are a set of tools for database backup and restore.

**Added in v1.2.0**

## Overview

| Tool | Description |
|------|-------------|
| `database_export` | Export database to JSONL format |
| `database_import` | Import from JSONL file |

---

## database_export

Export database to JSONL format. Partial export is possible with filtering.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `output_path` | string | Yes | - | Output file path |
| `include_embeddings` | boolean | No | `true` | Include embedding vectors |
| `memory_tier` | string | No | `null` | Export specific tier only |
| `created_after` | string | No | `null` | After this date (ISO format) |
| `created_before` | string | No | `null` | Before this date (ISO format) |
| `format` | string | No | `"jsonl"` | Output format (only jsonl currently) |

### Response

```json
{
  "exported_at": "2025-01-15T10:30:00Z",
  "schema_version": 3,
  "counts": {
    "memories": 1500,
    "knowledge_documents": 50,
    "knowledge_chunks": 2500,
    "agents": 5,
    "messages": 100,
    "memory_links": 200,
    "decay_config": 1
  },
  "file_path": "/path/to/backup.jsonl",
  "file_size_bytes": 5242880
}
```

### Examples

```python
# Export entire database
database_export(
    output_path="./backup.jsonl",
    include_embeddings=True
)

# Export without embeddings (smaller file size)
database_export(
    output_path="./backup-no-emb.jsonl",
    include_embeddings=False
)

# Export long-term memories only
database_export(
    output_path="./long_term_backup.jsonl",
    memory_tier="long_term"
)

# Filter by date range
database_export(
    output_path="./2025-backup.jsonl",
    created_after="2025-01-01T00:00:00Z",
    created_before="2025-12-31T23:59:59Z"
)
```

### Validation

- `output_path` is required
- `format` only supports `"jsonl"`
- Dates must be ISO 8601 format

### Security

- Path traversal (`../`) is rejected
- Writing outside allowed directories returns error

---

## database_import

Import from JSONL file into database.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `input_path` | string | Yes | - | Input file path |
| `mode` | string | No | `"merge"` | Import mode |
| `on_conflict` | string | No | `"skip"` | Conflict behavior |
| `regenerate_embeddings` | boolean | No | `false` | Regenerate embeddings |

### Import Modes

| Mode | Description |
|------|-------------|
| `merge` | Add to existing data (skip/update duplicates) |
| `replace` | Delete all existing data then import |

### Conflict Behavior

| Value | Description |
|-------|-------------|
| `skip` | Skip existing records |
| `update` | Overwrite existing records |
| `error` | Raise error and abort |

### Response

```json
{
  "imported_at": "2025-01-15T11:00:00Z",
  "schema_version": 3,
  "mode": "merge",
  "counts": {
    "memories": 1500,
    "knowledge_documents": 50,
    "knowledge_chunks": 2500,
    "agents": 5,
    "messages": 100,
    "memory_links": 200,
    "decay_config": 1
  },
  "skipped_count": 100,
  "error_count": 0,
  "errors": []
}
```

### Examples

```python
# Merge mode import (skip existing)
database_import(
    input_path="./backup.jsonl",
    mode="merge",
    on_conflict="skip"
)

# Merge mode import (update existing)
database_import(
    input_path="./backup.jsonl",
    mode="merge",
    on_conflict="update"
)

# Full restore (delete existing)
database_import(
    input_path="./backup.jsonl",
    mode="replace"
)

# Regenerate embeddings on import
database_import(
    input_path="./backup-no-emb.jsonl",
    regenerate_embeddings=True
)
```

### Validation

- `input_path` is required
- `mode` must be `"merge"` or `"replace"`
- `on_conflict` must be `"skip"`, `"update"`, or `"error"`
- Error if file does not exist
- Error if schema version is incompatible

### Security

- Path traversal (`../`) is rejected
- Reading from outside allowed directories returns error

---

## JSONL Format

Exported JSONL file format:

```jsonl
{"schema_version": 3, "exported_at": "2025-01-15T10:30:00Z", "counts": {...}}
{"type": "memory", "id": "uuid-1", "content": "...", "embedding": [...], ...}
{"type": "memory", "id": "uuid-2", "content": "...", "embedding": [...], ...}
{"type": "knowledge_document", "id": "doc-1", "title": "...", ...}
{"type": "knowledge_chunk", "id": "chunk-1", "content": "...", ...}
{"type": "agent", "id": "agent-1", "name": "...", ...}
{"type": "message", "id": "msg-1", "content": "...", ...}
{"type": "memory_link", "id": "link-1", "source_id": "...", ...}
{"type": "decay_config", "enabled": true, "threshold": 0.1, ...}
```

### Record Types

| Type | Description |
|------|-------------|
| `memory` | Memory entry |
| `knowledge_document` | Knowledge document |
| `knowledge_chunk` | Document chunk |
| `agent` | Agent |
| `message` | Message |
| `memory_link` | Memory link |
| `decay_config` | Decay settings |

---

## Use Cases

### Regular Backup

```python
from datetime import datetime

# Daily backup
date_str = datetime.now().strftime("%Y%m%d")
database_export(
    output_path=f"./backups/backup-{date_str}.jsonl",
    include_embeddings=True
)
```

### Data Migration Between Environments

```python
# Export from production
database_export(output_path="./prod-data.jsonl")

# Import to development
database_import(
    input_path="./prod-data.jsonl",
    mode="replace"  # Delete existing
)
```

### Partial Restore

```python
# Restore long-term memories only
database_import(
    input_path="./long_term_backup.jsonl",
    mode="merge",
    on_conflict="update"  # Update existing
)
```

### Changing Embedding Model

```python
# Export without embeddings
database_export(
    output_path="./backup-no-emb.jsonl",
    include_embeddings=False
)

# Regenerate embeddings with new model
database_import(
    input_path="./backup-no-emb.jsonl",
    mode="replace",
    regenerate_embeddings=True
)
```

---

## Schema Version

| Version | Compatibility |
|---------|---------------|
| 1 | v0.1.0 |
| 2 | v1.0.0, v1.1.0 |
| 3 | v1.2.0 |

Older schema version files can be imported (forward compatibility).
Newer schema version files cannot be imported.

---

## Error Response

```json
{
  "error": true,
  "error_type": "ValidationError",
  "message": "Path traversal detected in ../backup.jsonl"
}
```

### Error Types

- `ValidationError` - Invalid parameter
- `IOError` - File read/write error
- `SchemaError` - Incompatible schema version

---

## Related Links

- [Memory Tools](memory-tools.md)
- [Knowledge Tools](knowledge-tools.md)
- [Tools List](tools-reference.md)
