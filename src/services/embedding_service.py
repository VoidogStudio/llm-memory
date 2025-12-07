"""Embedding service for vector generation."""

from src.embeddings.base import EmbeddingProvider


class EmbeddingService:
    """Service for generating embeddings."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        """Initialize embedding service.

        Args:
            provider: Embedding provider instance
        """
        self.provider = provider

    async def generate(self, text: str, *, is_query: bool = False) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text
            is_query: True for search queries, False for documents/passages.
                      Some models (like E5) require different prefixes.

        Returns:
            Embedding vector

        Raises:
            ValueError: If text is empty
        """
        return await self.provider.embed(text, is_query=is_query)

    async def generate_batch(
        self, texts: list[str], *, is_query: bool = False
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            is_query: True for search queries, False for documents/passages.
                      Some models (like E5) require different prefixes.

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If texts list is empty
        """
        return await self.provider.embed_batch(texts, is_query=is_query)

    def dimensions(self) -> int:
        """Get embedding vector dimensions.

        Returns:
            Number of dimensions
        """
        return self.provider.dimensions()
