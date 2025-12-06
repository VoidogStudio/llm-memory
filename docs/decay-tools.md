# Decay Tools

Memory Decay Tools are a set of tools for automatically deleting (decaying) unused or low-importance memories.

**Added in v1.2.0**

## Overview

| Tool | Description |
|------|-------------|
| `memory_decay_configure` | Configure decay settings |
| `memory_decay_run` | Run decay (dry-run supported) |
| `memory_decay_status` | Get decay statistics and settings |

---

## memory_decay_configure

Configure memory decay settings.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enabled` | boolean | No | `true` | Enable/disable decay |
| `threshold` | float | No | `0.1` | Importance threshold for deletion (0.0-1.0) |
| `grace_period_days` | integer | No | `7` | Protection period after creation (days) |
| `auto_run_interval_hours` | integer | No | `24` | Auto-run interval (hours) |
| `max_delete_per_run` | integer | No | `100` | Maximum deletions per run |

### Response

```json
{
  "success": true,
  "config": {
    "enabled": true,
    "threshold": 0.1,
    "grace_period_days": 7,
    "auto_run_interval_hours": 24,
    "max_delete_per_run": 100
  }
}
```

### Examples

```python
# Enable decay with settings
memory_decay_configure(
    enabled=True,
    threshold=0.1,           # Delete below 0.1 score
    grace_period_days=7,     # 7 day protection
    max_delete_per_run=50
)

# Disable decay
memory_decay_configure(enabled=False)
```

### Validation

- `threshold` must be in range 0.0-1.0
- `grace_period_days` must be 0 or greater
- `max_delete_per_run` must be 1 or greater

---

## memory_decay_run

Run memory decay. Preview deletion targets with dry-run mode.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `dry_run` | boolean | No | `false` | Preview only (don't delete) |
| `threshold` | float | No | `null` | Temporary threshold override |
| `grace_period_days` | integer | No | `null` | Temporary grace period override |
| `max_delete` | integer | No | `null` | Temporary max delete override |

### Response

```json
{
  "success": true,
  "dry_run": false,
  "deleted_count": 5,
  "deleted_ids": [
    "uuid-1",
    "uuid-2",
    "uuid-3",
    "uuid-4",
    "uuid-5"
  ],
  "threshold_used": 0.1,
  "grace_period_used": 7,
  "execution_time_ms": 150
}
```

Dry-run mode (returns count and IDs that would be deleted):

```json
{
  "success": true,
  "dry_run": true,
  "deleted_count": 5,
  "deleted_ids": [
    "uuid-1",
    "uuid-2",
    "uuid-3",
    "uuid-4",
    "uuid-5"
  ],
  "threshold_used": 0.1,
  "grace_period_used": 7
}
```

### Examples

```python
# Preview (dry-run)
result = memory_decay_run(dry_run=True)
print(f"Deletion candidates: {result['deleted_count']} items")

# Execute
memory_decay_run(dry_run=False)

# Execute with temporary higher threshold
memory_decay_run(
    dry_run=False,
    threshold=0.2,  # Delete below 0.2 score
    max_delete=10   # Max 10 items
)
```

### Validation

- `threshold` override must be in range 0.0-1.0
- `grace_period_days` override must be 0 or greater
- `max_delete` override must be 1 or greater

---

## memory_decay_status

Get decay statistics and current settings.

### Parameters

None

### Response

```json
{
  "success": true,
  "config": {
    "enabled": true,
    "threshold": 0.1,
    "grace_period_days": 7,
    "auto_run_interval_hours": 24,
    "max_delete_per_run": 100
  },
  "statistics": {
    "total_memories": 1500,
    "below_threshold": 45,
    "within_grace_period": 12,
    "decay_candidates": 33,
    "last_run_at": "2025-01-15T10:00:00Z",
    "last_run_deleted": 10
  }
}
```

### Example

```python
# Check statistics
status = memory_decay_status()
print(f"Decay candidates: {status['statistics']['decay_candidates']} items")
print(f"Last run: {status['statistics']['last_run_at']}")
```

---

## Decay Algorithm

Conditions for a memory to be a decay target:

1. **Importance score below threshold**: `importance_score < threshold`
2. **Past grace period**: `created_at < now - grace_period_days`
3. **No expiration set**: `expires_at IS NULL` or `expires_at > now`

### Importance Score Calculation

Importance scores are calculated from the following factors:

- **Access frequency**: More frequently accessed memories score higher
- **Last access time**: Recently accessed memories score higher
- **Manual override**: Values set with `memory_set_score`

```
score = frequency_factor * 0.4 + recency_factor * 0.6
```

---

## Use Cases

### Regular Cleanup

```python
# Set up daily auto-cleanup
memory_decay_configure(
    enabled=True,
    threshold=0.1,
    grace_period_days=30,    # 30 day grace period
    auto_run_interval_hours=24,
    max_delete_per_run=100
)
```

### Conservative Decay

```python
# Delete only very low score memories
memory_decay_configure(
    threshold=0.05,          # Only below 5%
    grace_period_days=90,    # 90 day protection
    max_delete_per_run=10    # Delete gradually
)
```

### Manual Bulk Cleanup

```python
# Bulk delete old memories
memory_decay_run(
    dry_run=False,
    threshold=0.3,           # Raise threshold
    grace_period_days=0,     # No protection period
    max_delete=1000
)
```

---

## Error Response

```json
{
  "error": true,
  "error_type": "ValidationError",
  "message": "threshold must be between 0.0 and 1.0"
}
```

### Error Types

- `ValidationError` - Invalid parameter
- `ConfigurationError` - Decay is disabled

---

## Related Links

- [Memory Tools](memory-tools.md)
- [Importance Scoring](memory-tools.md#memory_get_score)
- [Tools List](tools-reference.md)
