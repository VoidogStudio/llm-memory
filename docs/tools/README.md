# LLM Memory MCP Tools Reference

LLM Memoryは14個のMCPツールを提供し、LLMに永続メモリ、ナレッジベース、エージェント間通信機能を付与します。

## ツール一覧

### Memory Management（6ツール）

メモリの保存、検索、更新、削除を行うツール群です。

| ツール | 説明 | ドキュメント |
|--------|------|-------------|
| `memory_store` | メモリを保存（埋め込み自動生成） | [詳細](memory-tools.md#memory_store) |
| `memory_search` | セマンティック類似性検索 | [詳細](memory-tools.md#memory_search) |
| `memory_get` | IDでメモリを取得 | [詳細](memory-tools.md#memory_get) |
| `memory_update` | メモリを更新 | [詳細](memory-tools.md#memory_update) |
| `memory_delete` | メモリを削除 | [詳細](memory-tools.md#memory_delete) |
| `memory_list` | フィルタリングでリスト | [詳細](memory-tools.md#memory_list) |

詳細: [Memory Tools](memory-tools.md)

### Knowledge Base（2ツール）

ドキュメントのインポートとセマンティック検索を行うツール群です。

| ツール | 説明 | ドキュメント |
|--------|------|-------------|
| `knowledge_import` | ドキュメントをチャンク分割してインポート | [詳細](knowledge-tools.md#knowledge_import) |
| `knowledge_query` | ナレッジベースをセマンティック検索 | [詳細](knowledge-tools.md#knowledge_query) |

詳細: [Knowledge Tools](knowledge-tools.md)

### Agent Communication（6ツール）

エージェント間のメッセージングとコンテキスト共有を行うツール群です。

| ツール | 説明 | ドキュメント |
|--------|------|-------------|
| `agent_register` | エージェントを登録 | [詳細](agent-tools.md#agent_register) |
| `agent_get` | エージェント情報を取得 | [詳細](agent-tools.md#agent_get) |
| `agent_send_message` | メッセージを送信 | [詳細](agent-tools.md#agent_send_message) |
| `agent_receive_messages` | メッセージを受信 | [詳細](agent-tools.md#agent_receive_messages) |
| `context_share` | コンテキストを共有 | [詳細](agent-tools.md#context_share) |
| `context_read` | 共有コンテキストを読み取り | [詳細](agent-tools.md#context_read) |

詳細: [Agent Tools](agent-tools.md)

---

## クイックスタート

### メモリの基本操作

```python
# メモリを保存
memory_store(
    content="User prefers dark mode",
    memory_tier="long_term",
    tags=["preferences", "ui"]
)

# セマンティック検索
memory_search(query="user preferences", top_k=5)

# メモリを取得
memory_get(id="550e8400-e29b-41d4-a716-446655440000")
```

### ナレッジベースの基本操作

```python
# ドキュメントをインポート
knowledge_import(
    title="API Documentation",
    content=document_text,
    category="docs",
    chunk_size=500
)

# クエリ
knowledge_query(query="authentication")
```

### エージェント通信の基本操作

```python
# エージェントを登録
agent_register(agent_id="coder", name="Coding Agent")

# メッセージを送信
agent_send_message(
    sender_id="coder",
    receiver_id="reviewer",
    content="Code ready for review"
)

# メッセージを受信
agent_receive_messages(agent_id="reviewer")

# コンテキストを共有
context_share(
    key="current_task",
    value={"status": "in_progress"},
    agent_id="director"
)
```

---

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Tools Layer                         │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Memory Tools   │ Knowledge Tools │    Agent Tools          │
│    (6 tools)    │   (2 tools)     │     (6 tools)           │
├─────────────────┴─────────────────┴─────────────────────────┤
│                    Services Layer                            │
│  MemoryService  │ KnowledgeService│   AgentService          │
├─────────────────┴─────────────────┴─────────────────────────┤
│                   Repository Layer                           │
│  MemoryRepo     │ KnowledgeRepo   │   AgentRepo             │
├─────────────────┴─────────────────┴─────────────────────────┤
│                    Database Layer                            │
│              SQLite + sqlite-vec (Vector Search)             │
└─────────────────────────────────────────────────────────────┘
```

---

## データモデル

### Memory Tiers（メモリ階層）

| 階層 | 説明 | 用途 |
|------|------|------|
| `short_term` | 短期メモリ | TTL付き一時情報 |
| `long_term` | 長期メモリ | 永続的な重要情報 |
| `working` | ワーキングメモリ | セッション中の作業データ |

### Content Types（コンテンツタイプ）

| タイプ | 説明 |
|--------|------|
| `text` | プレーンテキスト |
| `image` | 画像参照 |
| `code` | ソースコード |
| `json` | JSONデータ |
| `yaml` | YAMLデータ |

### Message Types（メッセージタイプ）

| タイプ | 説明 |
|--------|------|
| `direct` | 1対1のダイレクトメッセージ |
| `broadcast` | 全エージェントへのブロードキャスト |
| `context` | コンテキスト更新通知 |

### Access Levels（アクセスレベル）

| レベル | 説明 |
|--------|------|
| `public` | 全エージェントがアクセス可能 |
| `restricted` | 指定エージェントのみアクセス可能 |

---

## エラーハンドリング

すべてのツールは統一されたエラーフォーマットを返します：

```json
{
  "error": true,
  "error_type": "ValidationError",
  "message": "Content cannot be empty"
}
```

### エラータイプ

| タイプ | 説明 |
|--------|------|
| `ValidationError` | 入力パラメータのバリデーションエラー |
| `NotFoundError` | 指定されたリソースが見つからない |

---

## 制限事項

| 項目 | 制限 |
|------|------|
| 推奨メモリ数上限 | 100,000 |
| 同時書き込み | 単一（SQLite制限） |
| チャンクサイズ上限 | 2,000文字 |
| `top_k` 範囲 | 1〜1,000 |
| `chunk_size` 範囲 | 100〜10,000 |

---

## 関連リンク

- [Memory Tools詳細](memory-tools.md)
- [Knowledge Tools詳細](knowledge-tools.md)
- [Agent Tools詳細](agent-tools.md)
- [メインREADME](../../README.md)
