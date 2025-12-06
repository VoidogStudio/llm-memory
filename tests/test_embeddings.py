"""Tests for embedding providers."""

import pytest

from src.embeddings.base import EmbeddingProvider


class TestEmbeddingProvider:
    """Test EmbeddingProvider base class."""

    @pytest.mark.asyncio
    async def test_mock_embedding_provider(self, mock_embedding_provider: EmbeddingProvider):
        """Test mock embedding provider."""
        # Test single embedding
        embedding = await mock_embedding_provider.embed("Test text")

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(v, float) for v in embedding)

    @pytest.mark.asyncio
    async def test_mock_batch_embedding(self, mock_embedding_provider: EmbeddingProvider):
        """Test mock batch embedding generation."""
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = await mock_embedding_provider.embed_batch(texts)

        assert len(embeddings) == len(texts)  # Mock returns same number as input
        assert all(len(emb) == 384 for emb in embeddings)

    @pytest.mark.asyncio
    async def test_embedding_dimensions(self, mock_embedding_provider: EmbeddingProvider):
        """Test getting embedding dimensions."""
        dims = mock_embedding_provider.dimensions()

        assert dims == 384
