"""Knowledge service for business logic."""

import re

from src.db.repositories.knowledge_repository import KnowledgeRepository
from src.models.knowledge import Chunk, ChunkResult, Document
from src.services.embedding_service import EmbeddingService


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
        chunking_strategy: str = "sentence",
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
            chunking_strategy: Chunking strategy (sentence/paragraph/semantic)

        Returns:
            Tuple of (Document, chunks_created count)
        """
        # Validate chunking_strategy
        if chunking_strategy not in ["sentence", "paragraph", "semantic"]:
            raise ValueError("chunking_strategy must be one of: sentence, paragraph, semantic")

        # Create document
        document = Document(
            title=title,
            source=source,
            category=category,
            metadata=metadata or {},
        )

        await self.repository.create_document(document)

        # Split into chunks based on strategy
        if chunking_strategy == "sentence":
            chunk_data = self.split_by_sentence(content, chunk_size, chunk_overlap)
        elif chunking_strategy == "paragraph":
            chunk_data = self.split_by_paragraph(content, chunk_size, chunk_overlap)
        elif chunking_strategy == "semantic":
            chunk_data = self.split_by_semantic(content, chunk_size, chunk_overlap)

        # Create chunk objects with metadata
        chunks = [
            Chunk(
                document_id=document.id,
                content=data["content"],
                chunk_index=i,
                section_path=data.get("section_path", []),
                has_previous=data.get("has_previous", False),
                has_next=data.get("has_next", False),
                metadata=data.get("metadata", {}),
            )
            for i, data in enumerate(chunk_data)
        ]

        # Generate embeddings
        chunk_texts = [chunk.content for chunk in chunks]
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

    def split_by_sentence(
        self, content: str, chunk_size: int = 500, overlap: int = 50
    ) -> list[dict]:
        """Split content by sentence boundaries.

        Args:
            content: Content to split
            chunk_size: Maximum chunk size
            overlap: Overlap characters

        Returns:
            List of chunk dicts with content and metadata
        """
        if not content or not content.strip():
            return []

        # Split by sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", content)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # If adding sentence exceeds chunk_size and we have content
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + " " + sentence
                else:
                    current_chunk = sentence
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence

        # Add last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Convert to dict format with metadata
        result = []
        for i, chunk_text in enumerate(chunks):
            result.append({
                "content": chunk_text,
                "section_path": [],
                "has_previous": i > 0,
                "has_next": i < len(chunks) - 1,
                "metadata": {},
            })

        return result

    def split_by_paragraph(
        self, content: str, chunk_size: int = 500, overlap: int = 50
    ) -> list[dict]:
        """Split content by paragraph boundaries.

        Args:
            content: Content to split
            chunk_size: Maximum chunk size
            overlap: Overlap characters

        Returns:
            List of chunk dicts with content and metadata
        """
        if not content or not content.strip():
            return []

        # Split by paragraph (double newline)
        paragraphs = content.split("\n\n")

        chunks = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If paragraph fits in chunk_size, use it as-is
            if len(para) <= chunk_size:
                chunks.append(para)
            else:
                # Fallback to sentence strategy for large paragraphs
                sentence_chunks = self.split_by_sentence(para, chunk_size, overlap)
                chunks.extend([c["content"] for c in sentence_chunks])

        # Convert to dict format with metadata
        result = []
        for i, chunk_text in enumerate(chunks):
            result.append({
                "content": chunk_text,
                "section_path": [],
                "has_previous": i > 0,
                "has_next": i < len(chunks) - 1,
                "metadata": {},
            })

        return result

    def split_by_semantic(
        self, content: str, chunk_size: int = 500, overlap: int = 50
    ) -> list[dict]:
        """Split content by semantic boundaries (Markdown-aware).

        Args:
            content: Markdown content to split
            chunk_size: Maximum chunk size
            overlap: Overlap characters

        Returns:
            List of chunk dicts with content, section_path, and metadata
        """
        if not content or not content.strip():
            return []

        # Parse Markdown sections
        sections = self.parse_markdown_sections(content)

        # If no sections found (not Markdown), fallback to paragraph
        if len(sections) <= 1 and not sections[0][0]:
            return self.split_by_paragraph(content, chunk_size, overlap)

        chunks = []
        for section_path, section_content in sections:
            if not section_content.strip():
                continue

            # If section fits in chunk_size, use it as-is
            if len(section_content) <= chunk_size:
                chunks.append({
                    "content": section_content.strip(),
                    "section_path": section_path,
                })
            else:
                # Fallback to paragraph strategy for large sections
                para_chunks = self.split_by_paragraph(section_content, chunk_size, overlap)
                for para_chunk in para_chunks:
                    chunks.append({
                        "content": para_chunk["content"],
                        "section_path": section_path,
                    })

        # Add has_previous and has_next
        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                "content": chunk["content"],
                "section_path": chunk.get("section_path", []),
                "has_previous": i > 0,
                "has_next": i < len(chunks) - 1,
                "metadata": {},
            })

        return result

    def parse_markdown_sections(self, content: str) -> list[tuple[list[str], str]]:
        """Parse Markdown into hierarchical sections.

        Args:
            content: Markdown content

        Returns:
            List of (section_path, section_content) tuples
        """
        lines = content.split("\n")
        sections = []
        current_path: list[str] = []
        current_content: list[str] = []

        for line in lines:
            # Match Markdown headings
            heading_match = re.match(r"^(#+)\s+(.+)", line)

            if heading_match:
                # Save previous section
                if current_content:
                    sections.append((current_path[:], "\n".join(current_content)))

                # Update path
                level = len(heading_match.group(1))
                heading = heading_match.group(2).strip()
                current_path = current_path[:level-1] + [heading]
                current_content = []
            else:
                # Add line to current section
                current_content.append(line)

        # Save last section
        if current_content:
            sections.append((current_path[:], "\n".join(current_content)))

        # If no sections found, return entire content as one section
        if not sections:
            return [([], content)]

        return sections
