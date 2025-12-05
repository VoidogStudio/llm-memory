# Agent Tools

Agent Toolsは、エージェント間のメッセージパッシングとコンテキスト共有を行うためのツール群です。

## 概要

| ツール | 説明 |
|--------|------|
| `agent_register` | エージェントを登録 |
| `agent_get` | エージェント情報を取得 |
| `agent_send_message` | メッセージを送信（ダイレクトまたはブロードキャスト） |
| `agent_receive_messages` | メッセージを受信 |
| `context_share` | コンテキストを共有 |
| `context_read` | 共有コンテキストを読み取り |

---

## agent_register

新しいエージェントを登録するか、既存のエージェントを取得します。

### パラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `agent_id` | string | Yes | 一意のエージェント識別子 |
| `name` | string | Yes | エージェントの表示名 |
| `description` | string | No | エージェントの説明 |

### レスポンス

```json
{
  "id": "coder",
  "name": "Coding Agent",
  "description": "Handles code implementation tasks",
  "created_at": "2025-01-15T10:30:00Z",
  "registered": true
}
```

### 使用例

```python
agent_register(
    agent_id="coder",
    name="Coding Agent",
    description="Handles code implementation tasks"
)
```

### バリデーション

- `agent_id` は空にできません
- `name` は空にできません

---

## agent_get

IDでエージェントの情報を取得します。

### パラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `agent_id` | string | Yes | 取得するエージェントID |

### レスポンス

```json
{
  "id": "coder",
  "name": "Coding Agent",
  "description": "Handles code implementation tasks",
  "created_at": "2025-01-15T10:30:00Z",
  "last_active_at": "2025-01-15T12:45:00Z"
}
```

### エラー

- `NotFoundError` - エージェントが見つからない場合

---

## agent_send_message

他のエージェントにメッセージを送信、またはブロードキャストします。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `sender_id` | string | Yes | - | 送信元エージェントID |
| `content` | string | Yes | - | メッセージ内容 |
| `receiver_id` | string | No | `null` | 宛先エージェントID（nullでブロードキャスト） |
| `message_type` | string | No | `"direct"` | メッセージタイプ |
| `metadata` | object | No | `null` | 追加メタデータ |

### 列挙値

**message_type:**
- `direct` - 特定のエージェントへの直接メッセージ
- `broadcast` - 全エージェントへのブロードキャスト
- `context` - コンテキスト更新通知

### レスポンス

```json
{
  "id": "772a0622-g49d-63f6-c938-668877662222",
  "sent": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### 使用例

```python
# ダイレクトメッセージ
agent_send_message(
    sender_id="coder",
    receiver_id="reviewer",
    content="Code implementation complete. Ready for review.",
    message_type="direct"
)

# ブロードキャスト
agent_send_message(
    sender_id="director",
    content="Starting new task: implement user authentication",
    message_type="broadcast"
)

# メタデータ付き
agent_send_message(
    sender_id="coder",
    receiver_id="tester",
    content="Feature implemented",
    metadata={"feature_id": "AUTH-001", "files_changed": 3}
)
```

### バリデーション

- `content` は空にできません
- `message_type` は `direct`, `broadcast`, `context` のいずれか

---

## agent_receive_messages

エージェント宛のメッセージを受信します。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `agent_id` | string | Yes | - | 受信エージェントID |
| `status` | string | No | `"pending"` | ステータスでフィルタ |
| `mark_as_read` | boolean | No | `true` | 自動的に既読にする |
| `limit` | integer | No | `50` | 最大メッセージ数 |

### 列挙値

**status:**
- `pending` - 未読メッセージ
- `read` - 既読メッセージ
- `all` - すべてのメッセージ

### レスポンス

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

### 使用例

```python
# 未読メッセージを取得して既読にする
agent_receive_messages(
    agent_id="reviewer",
    status="pending",
    mark_as_read=True
)

# 全メッセージを取得（既読にしない）
agent_receive_messages(
    agent_id="reviewer",
    status="all",
    mark_as_read=False,
    limit=100
)
```

---

## context_share

他のエージェントとコンテキスト値を共有します。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `key` | string | Yes | - | コンテキストキー（一意識別子） |
| `value` | any | Yes | - | 保存する値（JSONシリアライズ可能） |
| `agent_id` | string | Yes | - | オーナーエージェントID |
| `access_level` | string | No | `"public"` | アクセスレベル |
| `allowed_agents` | string[] | No | `null` | アクセス許可エージェントリスト（restricted用） |

### 列挙値

**access_level:**
- `public` - 全エージェントがアクセス可能
- `restricted` - `allowed_agents` に指定されたエージェントのみアクセス可能

### レスポンス

```json
{
  "key": "current_task",
  "stored": true,
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### 使用例

```python
# パブリックコンテキスト
context_share(
    key="current_task",
    value={"task_id": "TASK-001", "status": "in_progress"},
    agent_id="director",
    access_level="public"
)

# 制限付きコンテキスト
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

共有コンテキスト値を読み取ります。

### パラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `key` | string | Yes | 読み取るコンテキストキー |
| `agent_id` | string | Yes | 読み取りエージェントID（アクセスチェック用） |

### レスポンス

```json
{
  "key": "current_task",
  "value": {"task_id": "TASK-001", "status": "in_progress"},
  "owner_agent_id": "director",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### 使用例

```python
context_read(
    key="current_task",
    agent_id="coder"
)
```

### エラー

- `NotFoundError` - コンテキストが見つからない、またはアクセス拒否

---

## ユースケース

### マルチエージェント協調

```python
# 1. ディレクターがタスクを割り当て
agent_send_message(
    sender_id="director",
    receiver_id="coder",
    content="Implement user authentication feature"
)

# 2. コンテキストを共有
context_share(
    key="task_requirements",
    value={
        "feature": "authentication",
        "deadline": "2025-01-20",
        "priority": "high"
    },
    agent_id="director"
)

# 3. コーダーがメッセージを受信
messages = agent_receive_messages(agent_id="coder")

# 4. コーダーが要件を読み取り
requirements = context_read(key="task_requirements", agent_id="coder")

# 5. 完了通知
agent_send_message(
    sender_id="coder",
    receiver_id="reviewer",
    content="Implementation complete, ready for review"
)
```

### ワークフロー管理

```python
# ステータス更新のブロードキャスト
agent_send_message(
    sender_id="director",
    message_type="broadcast",
    content="Pipeline stage: testing"
)

# 共有進捗状況
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

## メッセージステータスフロー

```
pending → read → archived
   ↓
(mark_as_read=true で自動遷移)
```

---

## アクセス制御

### Public（パブリック）
- 全エージェントがコンテキストを読み取り可能
- デフォルトのアクセスレベル

### Restricted（制限付き）
- `allowed_agents` に指定されたエージェントのみ読み取り可能
- オーナーエージェントは常にアクセス可能

---

## エラーレスポンス

```json
{
  "error": true,
  "error_type": "NotFoundError",
  "message": "Agent not found: unknown_agent"
}
```

### エラータイプ

- `ValidationError` - 入力バリデーションエラー
- `NotFoundError` - リソースが見つからない、またはアクセス拒否
