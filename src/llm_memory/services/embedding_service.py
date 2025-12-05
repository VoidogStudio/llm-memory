"""Embedding service for vector generation."""

from llm_memory.embeddings.base import EmbeddingProvider


class EmbeddingService:
    """Service for generating embeddings."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        """Initialize embedding service.

        Args:
            provider: Embedding provider instance
        """
        self.provider = provider

    async def generate(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector

        Raises:
            ValueError: If text is empty
        """
        return await self.provider.embed(text)

    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If texts list is empty
        """
        return await self.provider.embed_batch(texts)

    def dimensions(self) -> int:
        """Get embedding vector dimensions.

        Returns:
            Number of dimensions
        """
        return self.provider.dimensions()
