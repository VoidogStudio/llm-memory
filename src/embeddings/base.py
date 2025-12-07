"""Abstract base class for embedding providers."""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed(self, text: str, *, is_query: bool = False) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text
            is_query: True for search queries, False for documents/passages.
                      Some models (like E5) require different prefixes.

        Returns:
            Embedding vector
        """
        pass

    @abstractmethod
    async def embed_batch(
        self, texts: list[str], *, is_query: bool = False
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            is_query: True for search queries, False for documents/passages.
                      Some models (like E5) require different prefixes.

        Returns:
            List of embedding vectors
        """
        pass

    @abstractmethod
    def dimensions(self) -> int:
        """Get embedding vector dimensions.

        Returns:
            Number of dimensions
        """
        pass
