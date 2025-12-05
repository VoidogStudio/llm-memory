"""Knowledge service for business logic."""

import re

from llm_memory.db.repositories.knowledge_repository import KnowledgeRepository
from llm_memory.models.knowledge import Chunk, ChunkResult, Document
from llm_memory.services.embedding_service import EmbeddingService


class KnowledgeService:
    """Service for knowledge base operations."""

    def __init__(
        self, repository: KnowledgeRepository, embedding_service: EmbeddingService
    ) -> None:
        """Initialize knowledge service.

        Args:
            repository: Knowledge repository
            embedding_service: Embedding service
        """
        self.repository = repository
        self.embedding_service = embedding_service

    async def import_document(
        self,
        title: str,
        content: str,
        source: str | None = None,
        category: str | None = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        metadata: dict | None = None,
    ) -> tuple[Document, int]:
        """Import a document into the knowledge base.

        Args:
            title: Document title
            content: Document content
            source: Source URL/path
            category: Category
            chunk_size: Characters per chunk
            chunk_overlap: Overlap between chunks
            metadata: Additional metadata

        Returns:
            Tuple of (Document, chunks_created count)
        """
        # Create document
        document = Document(
            title=title,
            source=source,
            category=category,
            metadata=metadata or {},
        )

        await self.repository.create_document(document)

        # Split into chunks
        chunk_texts = self.split_into_chunks(content, chunk_size, chunk_overlap)

        # Create chunk objects
        chunks = [
            Chunk(document_id=document.id, content=chunk_text, chunk_index=i)
            for i, chunk_text in enumerate(chunk_texts)
        ]

        # Generate embeddings
        embeddings = await self.embedding_service.generate_batch(chunk_texts)

        # Store chunks with embeddings
        await self.repository.create_chunks(chunks, embeddings)

        return (document, len(chunks))

    async def query(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
        document_id: str | None = None,
    ) -> list[ChunkResult]:
        """Query the knowledge base.

        Args:
            query: Search query
            top_k: Number of results
            category: Filter by category
            document_id: Filter by document

        Returns:
            List of chunk results
        """
        # Generate query embedding
        embedding = await self.embedding_service.generate(query)

        # Perform vector search
        return await self.repository.vector_search_chunks(
            embedding=embedding, top_k=top_k, category=category, document_id=document_id
        )

    async def get_document(self, document_id: str) -> Document | None:
        """Get document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document or None if not found
        """
        return await self.repository.find_document(document_id)

    async def delete_document(self, document_id: str) -> bool:
        """Delete document and its chunks.

        Args:
            document_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete_document(document_id)

    def split_into_chunks(
        self, content: str, chunk_size: int = 500, overlap: int = 50
    ) -> list[str]:
        """Split content into overlapping chunks.

        Args:
            content: Content to split
            chunk_size: Characters per chunk
            overlap: Overlap between chunks

        Returns:
            List of chunk strings
        """
        if chunk_size <= overlap:
            raise ValueError("chunk_size must be greater than overlap")

        # Handle empty content
        if not content or not content.strip():
            return []

        # Split by sentences first (better for semantic meaning)
        sentences = re.split(r"(?<=[.!?])\s+", content)

        chunks = []
        current_chunk = ""
        current_size = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # If adding this sentence would exceed chunk_size
            if current_size + sentence_len > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                # Take last 'overlap' characters from current chunk
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + " " + sentence
                    current_size = len(current_chunk)
                else:
                    current_chunk = sentence
                    current_size = sentence_len
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_size = len(current_chunk)

        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks
