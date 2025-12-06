# Agent Tools

Agent Tools are a set of tools for inter-agent message passing and context sharing.

## Overview

| Tool | Description |
|------|-------------|
| `agent_register` | Register agent |
| `agent_get` | Get agent info |
| `agent_send_message` | Send message (direct or broadcast) |
| `agent_receive_messages` | Receive messages |
| `context_share` | Share context |
| `context_read` | Read shared context |

---

## agent_register

Register a new agent or retrieve an existing agent.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | string | Yes | Unique agent identifier |
| `name` | string | Yes | Agent display name |
| `description` | string | No | Agent description |

### Response

```json
{
  "id": "coder",
  "name": "Coding Agent",
  "description": "Handles code implementation tasks",
  "created_at": "2025-01-15T10:30:00Z",
  "registered": true
}
```

### Example

```python
agent_register(
    agent_id="coder",
    name="Coding Agent",
    description="Handles code implementation tasks"
)
```

### Validation

- `agent_id` cannot be empty
- `name` cannot be empty

---

## agent_get

Get agent information by ID.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | string | Yes | Agent ID to retrieve |

### Response

```json
{
  "id": "coder",
  "name": "Coding Agent",
  "description": "Handles code implementation tasks",
  "created_at": "2025-01-15T10:30:00Z",
  "last_active_at": "2025-01-15T12:45:00Z"
}
```

### Errors

- `NotFoundError` - Agent not found

---

## agent_send_message

Send a message to another agent or broadcast to all agents.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `sender_id` | string | Yes | - | Sender agent ID |
| `content` | string | Yes | - | Message content |
| `receiver_id` | string | No | `null` | Receiver agent ID (null for broadcast) |
| `message_type` | string | No | `"direct"` | Message type |
| `metadata` | object | No | `null` | Additional metadata |

### Enum Values

**message_type:**

- `direct` - Direct message to specific agent
- `broadcast` - Broadcast to all agents
- `context` - Context update notification

### Response

```json
{
  "id": "772a0622-g49d-63f6-c938-668877662222",
  "sent": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Examples

```python
# Direct message
agent_send_message(
    sender_id="coder",
    receiver_id="reviewer",
    content="Code implementation complete. Ready for review.",
    message_type="direct"
)

# Broadcast
agent_send_message(
    sender_id="director",
    content="Starting new task: implement user authentication",
    message_type="broadcast"
)

# With metadata
agent_send_message(
    sender_id="coder",
    receiver_id="tester",
    content="Feature implemented",
    metadata={"feature_id": "AUTH-001", "files_changed": 3}
)
```

### Validation

- `content` cannot be empty
- `message_type` must be one of `direct`, `broadcast`, `context`

---

## agent_receive_messages

Receive messages for an agent.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `agent_id` | string | Yes | - | Receiver agent ID |
| `status` | string | No | `"pending"` | Filter by status |
| `mark_as_read` | boolean | No | `true` | Auto-mark as read |
| `limit` | integer | No | `50` | Maximum messages |

### Enum Values

**status:**

- `pending` - Unread messages
- `read` - Read messages
- `all` - All messages

### Response

```json
{
  "messages": [
    {
      "id": "772a0622-g49d-63f6-c938-668877662222",
      "sender_id": "coder",
      "content": "Feature implemented",
      "message_type": "direct",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

### Examples

```python
# Get unread messages and mark as read
agent_receive_messages(
    agent_id="reviewer",
    status="pending",
    mark_as_read=True
)

# Get all messages (don't mark as read)
agent_receive_messages(
    agent_id="reviewer",
    status="all",
    mark_as_read=False,
    limit=100
)
```

---

## context_share

Share a context value with other agents.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `key` | string | Yes | - | Context key (unique identifier) |
| `value` | any | Yes | - | Value to store (JSON serializable) |
| `agent_id` | string | Yes | - | Owner agent ID |
| `access_level` | string | No | `"public"` | Access level |
| `allowed_agents` | string[] | No | `null` | Allowed agent list (for restricted) |

### Enum Values

**access_level:**

- `public` - Accessible by all agents
- `restricted` - Accessible only by agents in `allowed_agents`

### Response

```json
{
  "key": "current_task",
  "stored": true,
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Examples

```python
# Public context
context_share(
    key="current_task",
    value={"task_id": "TASK-001", "status": "in_progress"},
    agent_id="director",
    access_level="public"
)

# Restricted context
context_share(
    key="sensitive_config",
    value={"api_key_hash": "abc123"},
    agent_id="director",
    access_level="restricted",
    allowed_agents=["coder", "tester"]
)
```

---

## context_read

Read a shared context value.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `key` | string | Yes | Context key to read |
| `agent_id` | string | Yes | Reading agent ID (for access check) |

### Response

```json
{
  "key": "current_task",
  "value": {"task_id": "TASK-001", "status": "in_progress"},
  "owner_agent_id": "director",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Example

```python
context_read(
    key="current_task",
    agent_id="coder"
)
```

### Errors

- `NotFoundError` - Context not found or access denied

---

## Use Cases

### Multi-Agent Collaboration

```python
# 1. Director assigns task
agent_send_message(
    sender_id="director",
    receiver_id="coder",
    content="Implement user authentication feature"
)

# 2. Share context
context_share(
    key="task_requirements",
    value={
        "feature": "authentication",
        "deadline": "2025-01-20",
        "priority": "high"
    },
    agent_id="director"
)

# 3. Coder receives message
messages = agent_receive_messages(agent_id="coder")

# 4. Coder reads requirements
requirements = context_read(key="task_requirements", agent_id="coder")

# 5. Completion notification
agent_send_message(
    sender_id="coder",
    receiver_id="reviewer",
    content="Implementation complete, ready for review"
)
```

### Workflow Management

```python
# Broadcast status update
agent_send_message(
    sender_id="director",
    message_type="broadcast",
    content="Pipeline stage: testing"
)

# Share progress status
context_share(
    key="pipeline_progress",
    value={
        "stage": "testing",
        "completed": ["planning", "design", "implementation"],
        "remaining": ["testing", "review", "deployment"]
    },
    agent_id="director"
)
```

---

## Message Status Flow

```text
pending → read → archived
   ↓
(auto-transitions with mark_as_read=true)
```

---

## Access Control

### Public

- All agents can read the context
- Default access level

### Restricted

- Only agents in `allowed_agents` can read
- Owner agent always has access

---

## Error Response

```json
{
  "error": true,
  "error_type": "NotFoundError",
  "message": "Agent not found: unknown_agent"
}
```

### Error Types

- `ValidationError` - Input validation error
- `NotFoundError` - Resource not found or access denied
