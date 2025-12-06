"""Local embedding provider using sentence-transformers."""

from typing import Any

from llm_memory.embeddings.base import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize local embedding provider.

        Args:
            model_name: Model name to use
        """
        self.model_name = model_name
        self._model: Any | None = None
        self._dimensions: int | None = None

    def _load_model(self) -> Any:
        """Load the sentence transformer model lazily.

        Returns:
            Loaded model
        """
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise ImportError(
                    "sentence-transformers is not installed. "
                    'Install with: pip install "llm-memory[local]"'
                ) from e

            self._model = SentenceTransformer(self.model_name)
            self._dimensions = self._model.get_sentence_embedding_dimension()

        return self._model

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        model = self._load_model()

        # Generate embedding (synchronous operation)
        embedding = model.encode(text, convert_to_numpy=True)

        # Convert to list
        return embedding.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        model = self._load_model()

        # Generate embeddings (synchronous operation)
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

        # Convert to list
        return [emb.tolist() for emb in embeddings]

    def dimensions(self) -> int:
        """Get embedding vector dimensions.

        Returns:
            Number of dimensions

        Raises:
            RuntimeError: If model fails to load properly
        """
        if self._dimensions is None:
            self._load_model()

        if self._dimensions is None:
            raise RuntimeError(
                f"Failed to determine embedding dimensions for model: {self.model_name}"
            )

        return self._dimensions
