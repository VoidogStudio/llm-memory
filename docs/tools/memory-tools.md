# Memory Tools

Memory Toolsは、LLMがセマンティック検索可能な永続メモリを管理するためのツール群です。

## 概要

| ツール | 説明 |
|--------|------|
| `memory_store` | メモリエントリを保存（埋め込み自動生成） |
| `memory_search` | セマンティック/キーワード/ハイブリッド検索 |
| `memory_get` | IDでメモリを取得 |
| `memory_update` | メモリを更新 |
| `memory_delete` | メモリを削除 |
| `memory_list` | フィルタリングとページネーションでリスト |
| `memory_batch_store` | 複数メモリを一括保存（最大100件）**v1.1.0** |
| `memory_batch_update` | 複数メモリを一括更新 **v1.1.0** |
| `memory_get_score` | 重要度スコアを取得 **v1.1.0** |
| `memory_set_score` | 重要度スコアを手動設定 **v1.1.0** |
| `memory_consolidate` | 関連メモリを統合・要約 **v1.1.0** |

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

セマンティック、キーワード、またはハイブリッド検索でメモリを検索します。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `query` | string | Yes | - | 検索クエリテキスト |
| `top_k` | integer | No | `10` | 返す最大結果数 |
| `memory_tier` | string | No | `null` | 階層でフィルタ |
| `tags` | string[] | No | `null` | タグでフィルタ（AND条件） |
| `content_type` | string | No | `null` | コンテンツタイプでフィルタ |
| `min_similarity` | float | No | `0.0` | 最小類似度閾値（0.0-1.0） |
| `search_mode` | string | No | `"semantic"` | 検索モード **v1.1.0** |
| `keyword_weight` | float | No | `0.3` | ハイブリッド検索でのキーワード重み **v1.1.0** |
| `sort_by` | string | No | `"relevance"` | ソート順 **v1.1.0** |
| `importance_weight` | float | No | `0.0` | 重要度スコアの重み付け **v1.1.0** |

**search_mode:**
- `semantic` - ベクトル類似度検索（デフォルト）
- `keyword` - FTS5キーワード検索
- `hybrid` - キーワード+セマンティックの組み合わせ

**sort_by:**
- `relevance` - 関連度順（デフォルト）
- `importance` - 重要度スコア順
- `created_at` - 作成日時順

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

---

## memory_batch_store (v1.1.0)

複数のメモリを一括で保存します。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `items` | array | Yes | - | 保存するメモリのリスト（最大100件） |
| `on_error` | string | No | `"rollback"` | エラー時の動作 |

**items 各要素:**
- `content` (string, 必須) - コンテンツ
- `content_type` (string) - コンテンツタイプ
- `memory_tier` (string) - メモリ階層
- `tags` (string[]) - タグ
- `metadata` (object) - メタデータ

**on_error:**
- `rollback` - エラー時に全てロールバック
- `continue` - エラーをスキップして継続
- `stop` - エラー時点で停止

### レスポンス

```json
{
  "success": true,
  "stored_count": 3,
  "stored_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "errors": []
}
```

### 使用例

```python
memory_batch_store(
    items=[
        {"content": "First memory", "tags": ["batch"]},
        {"content": "Second memory", "tags": ["batch"]},
        {"content": "Third memory", "tags": ["batch"]}
    ],
    on_error="rollback"
)
```

---

## memory_batch_update (v1.1.0)

複数のメモリを一括で更新します。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `updates` | array | Yes | - | 更新するメモリのリスト |
| `on_error` | string | No | `"rollback"` | エラー時の動作 |

**updates 各要素:**
- `id` (string, 必須) - メモリID
- `content` (string) - 新しいコンテンツ
- `tags` (string[]) - 新しいタグ
- `metadata` (object) - 追加メタデータ
- `memory_tier` (string) - 新しい階層

### レスポンス

```json
{
  "success": true,
  "updated_count": 2,
  "updated_ids": ["uuid-1", "uuid-2"],
  "errors": []
}
```

### 使用例

```python
memory_batch_update(
    updates=[
        {"id": "uuid-1", "tags": ["updated", "important"]},
        {"id": "uuid-2", "metadata": {"reviewed": true}}
    ],
    on_error="continue"
)
```

---

## memory_get_score (v1.1.0)

メモリの重要度スコアを取得します。スコアはアクセスパターン（頻度と最終アクセス日時）に基づいて計算されます。

### パラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `id` | string | Yes | メモリID（UUID） |

### レスポンス

```json
{
  "success": true,
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "importance_score": 0.75,
  "access_count": 12,
  "last_accessed_at": "2025-01-15T14:30:00Z"
}
```

### 使用例

```python
memory_get_score(id="550e8400-e29b-41d4-a716-446655440000")
```

---

## memory_set_score (v1.1.0)

メモリの重要度スコアを手動で設定します。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `id` | string | Yes | - | メモリID（UUID） |
| `score` | float | Yes | - | 新しいスコア（0.0〜1.0） |
| `reason` | string | No | `"Manual override"` | 設定理由（監査用） |

### レスポンス

```json
{
  "success": true,
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "previous_score": 0.5,
  "new_score": 0.9
}
```

### 使用例

```python
memory_set_score(
    id="550e8400-e29b-41d4-a716-446655440000",
    score=0.9,
    reason="Critical user preference"
)
```

### バリデーション

- `score` は 0.0〜1.0 の範囲
- 存在しないIDはエラー

---

## memory_consolidate (v1.1.0)

複数の関連メモリを1つに統合し、要約を生成します。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `memory_ids` | string[] | Yes | - | 統合するメモリIDのリスト（2〜50件） |
| `summary_strategy` | string | No | `"extractive"` | 要約戦略 |
| `preserve_originals` | boolean | No | `true` | 元のメモリを保持するか |
| `tags` | string[] | No | `null` | 統合メモリに付与するタグ |
| `metadata` | object | No | `null` | 統合メモリのメタデータ |

**summary_strategy:**
- `extractive` - 重要な文を抽出して要約

### レスポンス

```json
{
  "success": true,
  "consolidated_memory_id": "new-uuid",
  "original_count": 3,
  "preserved": true,
  "summary_length": 450
}
```

### 使用例

```python
# 関連メモリを統合（元は保持）
memory_consolidate(
    memory_ids=["uuid-1", "uuid-2", "uuid-3"],
    summary_strategy="extractive",
    preserve_originals=True,
    tags=["consolidated", "summary"]
)

# 統合して元を削除
memory_consolidate(
    memory_ids=["uuid-1", "uuid-2"],
    preserve_originals=False
)
```

### バリデーション

- `memory_ids` は 2〜50 件
- 存在しないIDはエラー
- 1件のみの場合はエラー
