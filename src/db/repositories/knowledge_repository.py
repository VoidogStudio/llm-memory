"""Knowledge repository for database operations."""

import json
from datetime import datetime
from typing import Any

from src.db.database import Database
from src.models.knowledge import Chunk, ChunkResult, Document


class KnowledgeRepository:
    """Repository for knowledge base operations."""

    def __init__(self, db: Database) -> None:
        """Initialize repository.

        Args:
            db: Database instance
        """
        self.db = db

    async def create_document(self, document: Document) -> Document:
        """Create a new knowledge document.

        Args:
            document: Document object to create

        Returns:
            Created document object
        """
        await self.db.execute(
            """
            INSERT INTO knowledge_documents (
                id, title, source, category, version, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.id,
                document.title,
                document.source,
                document.category,
                document.version,
                json.dumps(document.metadata),
                document.created_at.isoformat(),
                document.updated_at.isoformat(),
            ),
        )
        await self.db.commit()
        return document

    async def create_chunks(
        self, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> list[Chunk]:
        """Create document chunks with embeddings.

        Args:
            chunks: List of chunk objects
            embeddings: List of embedding vectors

        Returns:
            Created chunk objects
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        async with self.db.transaction():
            # Insert chunks
            chunk_params = [
                (
                    chunk.id,
                    chunk.document_id,
                    chunk.content,
                    chunk.chunk_index,
                    json.dumps(chunk.metadata),
                    json.dumps(chunk.section_path),
                    1 if chunk.has_previous else 0,
                    1 if chunk.has_next else 0,
                )
                for chunk in chunks
            ]

            await self.db.executemany(
                """
                INSERT INTO knowledge_chunks (
                    id, document_id, content, chunk_index, metadata,
                    section_path, has_previous, has_next
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                chunk_params,
            )

            # Insert embeddings
            embedding_params = [
                (chunk.id, json.dumps(embedding))
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ]

            await self.db.executemany(
                "INSERT INTO chunk_embeddings (chunk_id, embedding) VALUES (?, ?)",
                embedding_params,
            )

        return chunks

    async def find_document(self, document_id: str) -> Document | None:
        """Find document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document object or None if not found
        """
        cursor = await self.db.execute(
            "SELECT * FROM knowledge_documents WHERE id = ?", (document_id,)
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_document(row)

    async def delete_document(self, document_id: str) -> bool:
        """Delete document and all its chunks.

        Args:
            document_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        async with self.db.transaction():
            # Get chunk IDs
            cursor = await self.db.execute(
                "SELECT id FROM knowledge_chunks WHERE document_id = ?", (document_id,)
            )
            rows = await cursor.fetchall()
            chunk_ids = [row[0] for row in rows]

            # Delete chunk embeddings
            if chunk_ids:
                # Validate IDs to prevent injection
                if not all(isinstance(id, str) for id in chunk_ids):
                    raise ValueError("All IDs must be strings")

                placeholders = ",".join("?" * len(chunk_ids))
                await self.db.execute(
                    f"DELETE FROM chunk_embeddings WHERE chunk_id IN ({placeholders})",
                    tuple(chunk_ids),
                )

            # Delete chunks (CASCADE will handle this, but explicit is better)
            await self.db.execute(
                "DELETE FROM knowledge_chunks WHERE document_id = ?", (document_id,)
            )

            # Delete document
            cursor = await self.db.execute(
                "DELETE FROM knowledge_documents WHERE id = ?", (document_id,)
            )

        return cursor.rowcount > 0

    async def vector_search_chunks(
        self,
        embedding: list[float],
        top_k: int,
        category: str | None = None,
        document_id: str | None = None,
    ) -> list[ChunkResult]:
        """Perform vector similarity search on chunks.

        Args:
            embedding: Query embedding vector
            top_k: Number of results to return
            category: Filter by document category
            document_id: Filter by specific document

        Returns:
            List of chunk results with similarity scores
        """
        # Build WHERE clause for filters
        where_clauses = ["e.chunk_id = c.id", "c.document_id = d.id"]
        params: list[Any] = [json.dumps(embedding)]

        if category:
            where_clauses.append("d.category = ?")
            params.append(category)

        if document_id:
            where_clauses.append("d.id = ?")
            params.append(document_id)

        where_clause = " AND ".join(where_clauses)

        # Perform vector search
        # The WHERE clause is built from validated parameters (category and document_id are user input but parameterized)
        # sqlite-vec requires LIMIT in the subquery for knn searches
        cursor = await self.db.execute(
            f"""
            SELECT
                c.*,
                d.id as doc_id,
                d.title as doc_title,
                d.source as doc_source,
                d.category as doc_category,
                d.version as doc_version,
                d.metadata as doc_metadata,
                d.created_at as doc_created_at,
                d.updated_at as doc_updated_at,
                MAX(0, 1 - distance) as similarity
            FROM (
                SELECT embedding, chunk_id, distance
                FROM chunk_embeddings
                WHERE embedding MATCH ?
                ORDER BY distance
                LIMIT ?
            ) e
            JOIN knowledge_chunks c ON {where_clause}
            JOIN knowledge_documents d ON c.document_id = d.id
            ORDER BY distance
            """,
            tuple([params[0], top_k] + params[1:]),
        )

        rows = await cursor.fetchall()

        results = []
        for row in rows:
            # Convert Row to dict to use .get() method
            row_dict = dict(row)
            chunk = Chunk(
                id=row_dict["id"],
                document_id=row_dict["document_id"],
                content=row_dict["content"],
                chunk_index=row_dict["chunk_index"],
                metadata=json.loads(row_dict["metadata"]) if row_dict["metadata"] else {},
                section_path=json.loads(row_dict["section_path"]) if row_dict.get("section_path") else [],
                has_previous=bool(row_dict.get("has_previous", 0)),
                has_next=bool(row_dict.get("has_next", 0)),
            )

            document = Document(
                id=row_dict["doc_id"],
                title=row_dict["doc_title"],
                source=row_dict["doc_source"],
                category=row_dict["doc_category"],
                version=row_dict["doc_version"],
                metadata=json.loads(row_dict["doc_metadata"]) if row_dict["doc_metadata"] else {},
                created_at=datetime.fromisoformat(row_dict["doc_created_at"]),
                updated_at=datetime.fromisoformat(row_dict["doc_updated_at"]),
            )

            similarity = float(row_dict["similarity"])

            results.append(ChunkResult(chunk=chunk, document=document, similarity=similarity))

        return results

    def _row_to_document(self, row: Any) -> Document:
        """Convert database row to Document object.

        Args:
            row: Database row

        Returns:
            Document object
        """
        row_dict = dict(row)
        return Document(
            id=row_dict["id"],
            title=row_dict["title"],
            source=row_dict["source"],
            category=row_dict["category"],
            version=row_dict["version"],
            metadata=json.loads(row_dict["metadata"]) if row_dict["metadata"] else {},
            created_at=datetime.fromisoformat(row_dict["created_at"]),
            updated_at=datetime.fromisoformat(row_dict["updated_at"]),
        )
