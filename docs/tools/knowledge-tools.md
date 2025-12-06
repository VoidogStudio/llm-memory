# Knowledge Tools

Knowledge Tools are a set of tools for importing documents with chunking and querying them with semantic search.

## Overview

| Tool | Description |
|------|-------------|
| `knowledge_import` | Import document with chunking |
| `knowledge_query` | Query with semantic search |

---

## knowledge_import

Imports a document into the knowledge base. Content is automatically chunked and embedding vectors are generated for each chunk.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | string | Yes | - | Document title |
| `content` | string | Yes | - | Full document content |
| `source` | string | No | `null` | Source URL or file path |
| `category` | string | No | `null` | Classification category |
| `chunk_size` | integer | No | `500` | Characters per chunk |
| `chunk_overlap` | integer | No | `50` | Overlap characters between chunks |
| `metadata` | object | No | `{}` | Additional metadata |

### Response

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "API Documentation",
  "chunks_created": 15,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Example

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

### Validation

- `title` cannot be empty
- `content` cannot be empty
- `chunk_size` must be in range 100-10000
- `chunk_overlap` must be 0 or greater and less than `chunk_size`

### How Chunking Works

1. Document is split every `chunk_size` characters
2. Each chunk overlaps with the previous chunk by `chunk_overlap` characters
3. Overlap maintains context continuity

```
Document: [AAAAAABBBBBBCCCCCC]

chunk_size=6, chunk_overlap=2:
  Chunk 1: [AAAAAA]
  Chunk 2:   [AABBBB]  (2 character overlap)
  Chunk 3:       [BBCCCC]
```

---

## knowledge_query

Query the knowledge base with semantic search.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `top_k` | integer | No | `5` | Number of chunks to return |
| `category` | string | No | `null` | Filter by category |
| `document_id` | string | No | `null` | Filter by document ID |
| `include_document_info` | boolean | No | `true` | Include document metadata |

### Response

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

### Examples

```python
# Basic query
knowledge_query(query="authentication methods")

# Filter by category
knowledge_query(
    query="error handling",
    category="documentation",
    top_k=10
)

# Search within specific document
knowledge_query(
    query="rate limiting",
    document_id="550e8400-e29b-41d4-a716-446655440000",
    include_document_info=False
)
```

---

## Use Cases

### Document Search System

```python
# Import multiple documents
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

# Search based on user question
results = knowledge_query(
    query="How do I authenticate API requests?",
    top_k=3
)
```

### Codebase Documentation

```python
knowledge_import(
    title="auth_module.py",
    content=source_code,
    source="/src/auth/auth_module.py",
    category="source_code",
    chunk_size=300,  # Smaller chunks work better for code
    chunk_overlap=30
)
```

### FAQ System

```python
# Import entire FAQ
knowledge_import(
    title="FAQ",
    content=faq_content,
    category="faq",
    chunk_size=200,  # Each FAQ entry becomes one chunk
    chunk_overlap=0
)

# Search for relevant FAQ
knowledge_query(query="how to reset password", category="faq")
```

---

## Recommended Settings

### Chunk Size Guidelines

| Content Type | chunk_size | chunk_overlap | Reason |
|--------------|------------|---------------|--------|
| General documents | 500 | 50 | Standard balance |
| Technical docs | 800 | 100 | Long code blocks support |
| FAQ | 200 | 0 | Keep each item independent |
| Source code | 300 | 30 | Near function-level granularity |
| Long articles | 1000 | 150 | Context continuity priority |

---

## Limitations

- Recommended max chunk size: 2000 characters
- Recommended max chunks per document: 1000
- Large documents may take time to process due to embedding generation

---

## Error Response

```json
{
  "error": true,
  "error_type": "ValidationError",
  "message": "chunk_size must be between 100 and 10000"
}
```

### Error Types

- `ValidationError` - Input validation error
