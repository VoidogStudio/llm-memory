"""Local embedding provider using sentence-transformers."""

from typing import Any

from src.embeddings.base import EmbeddingProvider

# E5 model patterns that require prefixes
E5_MODEL_PATTERNS = ("e5-small", "e5-base", "e5-large", "e5-mistral")


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small") -> None:
        """Initialize local embedding provider.

        Args:
            model_name: Model name to use
        """
        self.model_name = model_name
        self._model: Any | None = None
        self._dimensions: int | None = None
        self._is_e5_model = self._check_is_e5_model(model_name)

    def _check_is_e5_model(self, model_name: str) -> bool:
        """Check if the model is an E5 model that requires prefixes.

        Args:
            model_name: Model name to check

        Returns:
            True if E5 model, False otherwise
        """
        model_lower = model_name.lower()
        return any(pattern in model_lower for pattern in E5_MODEL_PATTERNS)

    def _add_prefix(self, text: str, is_query: bool) -> str:
        """Add appropriate prefix for E5 models.

        Args:
            text: Input text
            is_query: True for search queries, False for documents/passages

        Returns:
            Text with prefix if E5 model, original text otherwise
        """
        if not self._is_e5_model:
            return text

        prefix = "query: " if is_query else "passage: "
        return prefix + text

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

    async def embed(self, text: str, *, is_query: bool = False) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text
            is_query: True for search queries, False for documents/passages

        Returns:
            Embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        model = self._load_model()

        # Add E5 prefix if needed
        processed_text = self._add_prefix(text, is_query)

        # Generate embedding (synchronous operation)
        embedding = model.encode(processed_text, convert_to_numpy=True)

        # Convert to list
        return embedding.tolist()

    async def embed_batch(
        self, texts: list[str], *, is_query: bool = False
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            is_query: True for search queries, False for documents/passages

        Returns:
            List of embedding vectors
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        model = self._load_model()

        # Add E5 prefix if needed
        processed_texts = [self._add_prefix(t, is_query) for t in texts]

        # Generate embeddings (synchronous operation)
        embeddings = model.encode(
            processed_texts, convert_to_numpy=True, show_progress_bar=False
        )

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
