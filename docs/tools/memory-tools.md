# Memory Tools

Memory Toolsは、LLMがセマンティック検索可能な永続メモリを管理するためのツール群です。

## 概要

| ツール | 説明 |
|--------|------|
| `memory_store` | メモリエントリを保存（埋め込み自動生成） |
| `memory_search` | セマンティック類似性検索 |
| `memory_get` | IDでメモリを取得 |
| `memory_update` | メモリを更新 |
| `memory_delete` | メモリを削除 |
| `memory_list` | フィルタリングとページネーションでリスト |

---

## memory_store

メモリエントリを保存し、自動的に埋め込みベクトルを生成します。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `content` | string | Yes | - | 保存するコンテンツ |
| `content_type` | string | No | `"text"` | コンテンツタイプ |
| `memory_tier` | string | No | `"long_term"` | メモリ階層 |
| `tags` | string[] | No | `[]` | 分類用タグ |
| `metadata` | object | No | `{}` | 追加メタデータ |
| `agent_id` | string | No | `null` | エージェントID |
| `ttl_seconds` | integer | No | `null` | 有効期限（秒） |

### 列挙値

**content_type:**
- `text` - テキスト
- `image` - 画像
- `code` - ソースコード
- `json` - JSON
- `yaml` - YAML

**memory_tier:**
- `short_term` - 短期メモリ（TTL付き、自動期限切れ）
- `long_term` - 長期メモリ（永続保存）
- `working` - ワーキングメモリ（アクティブセッション用）

### レスポンス

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "User prefers dark mode",
  "memory_tier": "long_term",
  "created_at": "2025-01-15T10:30:00Z"
}
```

### 使用例

```python
memory_store(
    content="User prefers dark mode and large font sizes",
    memory_tier="long_term",
    tags=["preferences", "ui"],
    metadata={"source": "settings_page"}
)
```

### バリデーション

- `content` は空にできません
- `ttl_seconds` は 0 以上である必要があります
- 無効な `memory_tier` または `content_type` はエラーを返します

---

## memory_search

セマンティック類似性を使用してメモリを検索します。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `query` | string | Yes | - | 検索クエリテキスト |
| `top_k` | integer | No | `10` | 返す最大結果数 |
| `memory_tier` | string | No | `null` | 階層でフィルタ |
| `tags` | string[] | No | `null` | タグでフィルタ（AND条件） |
| `content_type` | string | No | `null` | コンテンツタイプでフィルタ |
| `min_similarity` | float | No | `0.0` | 最小類似度閾値（0.0-1.0） |

### レスポンス

```json
{
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "User prefers dark mode",
      "similarity": 0.89,
      "memory_tier": "long_term",
      "tags": ["preferences", "ui"],
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

### 使用例

```python
memory_search(
    query="user interface preferences",
    top_k=5,
    memory_tier="long_term",
    min_similarity=0.5
)
```

### バリデーション

- `top_k` は 1〜1000 の範囲
- `min_similarity` は 0.0〜1.0 の範囲

---

## memory_get

IDで特定のメモリを取得します。

### パラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `id` | string | Yes | メモリID（UUID） |

### レスポンス

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "User prefers dark mode",
  "content_type": "text",
  "memory_tier": "long_term",
  "tags": ["preferences", "ui"],
  "metadata": {"source": "settings_page"},
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "expires_at": null
}
```

### エラー

- `NotFoundError` - メモリが見つからない場合

---

## memory_update

既存のメモリエントリを更新します。

### パラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `id` | string | Yes | 更新するメモリID |
| `content` | string | No | 新しいコンテンツ（埋め込みを再生成） |
| `tags` | string[] | No | 新しいタグリスト（既存を置換） |
| `metadata` | object | No | 追加メタデータ（既存にマージ） |
| `memory_tier` | string | No | 新しい階層（昇格/降格用） |

### レスポンス

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "updated": true,
  "updated_at": "2025-01-15T11:00:00Z"
}
```

### 使用例

```python
# タグを更新
memory_update(
    id="550e8400-e29b-41d4-a716-446655440000",
    tags=["preferences", "ui", "theme"]
)

# 短期から長期へ昇格
memory_update(
    id="550e8400-e29b-41d4-a716-446655440000",
    memory_tier="long_term"
)
```

### エラー

- `NotFoundError` - メモリが見つからない場合

---

## memory_delete

IDまたは条件でメモリを削除します。

### パラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `id` | string | No | 削除する単一メモリID |
| `ids` | string[] | No | 削除するメモリIDのリスト |
| `memory_tier` | string | No | この階層の全メモリを削除 |
| `older_than` | string | No | この日時より古いメモリを削除（ISO形式） |

### レスポンス

```json
{
  "deleted_count": 3,
  "deleted_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "661f9511-f38c-52e5-b827-557766551111",
    "772a0622-g49d-63f6-c938-668877662222"
  ]
}
```

### 使用例

```python
# 単一削除
memory_delete(id="550e8400-e29b-41d4-a716-446655440000")

# 複数削除
memory_delete(ids=["id1", "id2", "id3"])

# 古いメモリを削除
memory_delete(older_than="2024-01-01T00:00:00Z")

# 階層全体を削除
memory_delete(memory_tier="short_term")
```

---

## memory_list

フィルタリングとページネーションでメモリをリストします。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `memory_tier` | string | No | `null` | 階層でフィルタ |
| `tags` | string[] | No | `null` | タグでフィルタ（AND条件） |
| `content_type` | string | No | `null` | コンテンツタイプでフィルタ |
| `created_after` | string | No | `null` | 作成日でフィルタ（ISO形式） |
| `created_before` | string | No | `null` | 作成日でフィルタ（ISO形式） |
| `limit` | integer | No | `50` | 最大結果数（上限1000） |
| `offset` | integer | No | `0` | ページネーションオフセット |

### レスポンス

```json
{
  "memories": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "User prefers dark mode",
      "content_type": "text",
      "memory_tier": "long_term",
      "tags": ["preferences", "ui"],
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

### 使用例

```python
# 長期メモリを取得
memory_list(memory_tier="long_term", limit=20)

# 特定タグでフィルタ
memory_list(tags=["preferences"], created_after="2025-01-01T00:00:00Z")

# ページネーション
memory_list(limit=50, offset=50)  # 2ページ目
```

---

## Memory Tiers

### short_term（短期メモリ）
- TTL付きで自動期限切れ
- 一時的な情報に最適
- `ttl_seconds` パラメータで有効期限を設定

### long_term（長期メモリ）
- 永続的に保存
- 重要な情報、ユーザー設定など
- デフォルトの階層

### working（ワーキングメモリ）
- アクティブなセッションコンテキスト
- タスク実行中の一時データ

---

## エラーレスポンス

すべてのツールは統一されたエラー形式を返します：

```json
{
  "error": true,
  "error_type": "ValidationError",
  "message": "Content cannot be empty"
}
```

### エラータイプ

- `ValidationError` - 入力バリデーションエラー
- `NotFoundError` - リソースが見つからない
