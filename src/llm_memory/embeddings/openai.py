"""OpenAI embedding provider."""

from typing import Any

from llm_memory.embeddings.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(
        self, api_key: str, model: str = "text-embedding-3-small", dimensions: int = 1536
    ) -> None:
        """Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key
            model: Model name to use
            dimensions: Embedding dimensions
        """
        self.api_key = api_key
        self.model = model
        self._dimensions = dimensions
        self._client: Any | None = None

    def _get_client(self) -> Any:
        """Get OpenAI client lazily.

        Returns:
            OpenAI client
        """
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise ImportError(
                    "openai is not installed. " 'Install with: pip install "llm-memory[openai]"'
                ) from e

            self._client = AsyncOpenAI(api_key=self.api_key)

        return self._client

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        client = self._get_client()

        # Generate embedding
        response = await client.embeddings.create(input=[text], model=self.model)

        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        client = self._get_client()

        # Generate embeddings
        response = await client.embeddings.create(input=texts, model=self.model)

        # Extract embeddings in the same order
        return [item.embedding for item in response.data]

    def dimensions(self) -> int:
        """Get embedding vector dimensions.

        Returns:
            Number of dimensions
        """
        return self._dimensions
