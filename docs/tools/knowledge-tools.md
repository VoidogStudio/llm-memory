# Knowledge Tools

Knowledge Toolsは、ドキュメントをチャンク分割してインポートし、セマンティック検索でクエリするためのツール群です。

## 概要

| ツール | 説明 |
|--------|------|
| `knowledge_import` | ドキュメントをチャンク分割してインポート |
| `knowledge_query` | セマンティック検索でクエリ |

---

## knowledge_import

ドキュメントをナレッジベースにインポートします。コンテンツは自動的にチャンク分割され、各チャンクに埋め込みベクトルが生成されます。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `title` | string | Yes | - | ドキュメントタイトル |
| `content` | string | Yes | - | ドキュメント全文 |
| `source` | string | No | `null` | ソースURLまたはファイルパス |
| `category` | string | No | `null` | 分類カテゴリ |
| `chunk_size` | integer | No | `500` | チャンクあたりの文字数 |
| `chunk_overlap` | integer | No | `50` | チャンク間のオーバーラップ文字数 |
| `metadata` | object | No | `{}` | 追加メタデータ |

### レスポンス

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "API Documentation",
  "chunks_created": 15,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### 使用例

```python
knowledge_import(
    title="API Documentation",
    content=long_document_text,
    source="https://example.com/docs/api",
    category="documentation",
    chunk_size=500,
    chunk_overlap=50
)
```

### バリデーション

- `title` は空にできません
- `content` は空にできません
- `chunk_size` は 100〜10000 の範囲
- `chunk_overlap` は 0 以上かつ `chunk_size` 未満

### チャンク分割の仕組み

1. ドキュメントは `chunk_size` 文字ごとに分割されます
2. 各チャンクは `chunk_overlap` 文字分だけ前のチャンクと重複します
3. 重複により文脈の連続性が維持されます

```
Document: [AAAAAABBBBBBCCCCCC]

chunk_size=6, chunk_overlap=2:
  Chunk 1: [AAAAAA]
  Chunk 2:   [AABBBB]  (2文字のオーバーラップ)
  Chunk 3:       [BBCCCC]
```

---

## knowledge_query

ナレッジベースをセマンティック検索でクエリします。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `query` | string | Yes | - | 検索クエリ |
| `top_k` | integer | No | `5` | 返すチャンク数 |
| `category` | string | No | `null` | カテゴリでフィルタ |
| `document_id` | string | No | `null` | ドキュメントIDでフィルタ |
| `include_document_info` | boolean | No | `true` | ドキュメントメタデータを含める |

### レスポンス

```json
{
  "results": [
    {
      "chunk_id": "661f9511-f38c-52e5-b827-557766551111",
      "content": "The authentication endpoint accepts...",
      "similarity": 0.92,
      "document": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "API Documentation",
        "category": "documentation"
      }
    }
  ],
  "total": 1
}
```

### 使用例

```python
# 基本的なクエリ
knowledge_query(query="authentication methods")

# カテゴリでフィルタ
knowledge_query(
    query="error handling",
    category="documentation",
    top_k=10
)

# 特定ドキュメント内を検索
knowledge_query(
    query="rate limiting",
    document_id="550e8400-e29b-41d4-a716-446655440000",
    include_document_info=False
)
```

---

## ユースケース

### ドキュメント検索システム

```python
# 複数のドキュメントをインポート
knowledge_import(
    title="Getting Started Guide",
    content=getting_started_content,
    category="guides"
)

knowledge_import(
    title="API Reference",
    content=api_reference_content,
    category="reference"
)

# ユーザーの質問に基づいて検索
results = knowledge_query(
    query="How do I authenticate API requests?",
    top_k=3
)
```

### コードベースのドキュメント化

```python
knowledge_import(
    title="auth_module.py",
    content=source_code,
    source="/src/auth/auth_module.py",
    category="source_code",
    chunk_size=300,  # コードは小さめのチャンクが有効
    chunk_overlap=30
)
```

### FAQシステム

```python
# FAQ全体をインポート
knowledge_import(
    title="FAQ",
    content=faq_content,
    category="faq",
    chunk_size=200,  # 各FAQエントリが1チャンクになるように
    chunk_overlap=0
)

# 質問に関連するFAQを検索
knowledge_query(query="how to reset password", category="faq")
```

---

## 推奨設定

### チャンクサイズの目安

| コンテンツタイプ | chunk_size | chunk_overlap | 理由 |
|-----------------|------------|---------------|------|
| 一般的なドキュメント | 500 | 50 | 標準的なバランス |
| 技術文書 | 800 | 100 | 長いコードブロック対応 |
| FAQ | 200 | 0 | 各項目を独立させる |
| ソースコード | 300 | 30 | 関数単位に近い粒度 |
| 長文記事 | 1000 | 150 | 文脈の連続性重視 |

---

## 制限事項

- 推奨最大チャンクサイズ: 2000文字
- 1ドキュメントあたりの推奨最大チャンク数: 1000
- インポート時に埋め込み生成のため、大きなドキュメントは処理に時間がかかる場合があります

---

## エラーレスポンス

```json
{
  "error": true,
  "error_type": "ValidationError",
  "message": "chunk_size must be between 100 and 10000"
}
```

### エラータイプ

- `ValidationError` - 入力バリデーションエラー
