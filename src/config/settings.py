"""Application settings management using Pydantic Settings."""

from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_db_path() -> str:
    """Get default database path in user's data directory."""
    return str(Path.cwd() / "data" / "llm_memory.db")


class Settings(BaseSettings):
    """Application configuration settings.

    All settings can be configured via environment variables with the
    prefix `LLM_MEMORY_`. For example, `LLM_MEMORY_DATABASE_PATH`.
    """

    # Database
    database_path: str = Field(
        default_factory=_get_default_db_path,
        description="SQLite database file path",
    )

    # Embedding
    embedding_provider: Literal["local", "openai"] = Field(
        default="local", description="Embedding provider to use"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Embedding model name"
    )
    embedding_dimensions: int = Field(
        default=384,
        ge=1,
        le=4096,
        description="Embedding vector dimensions",
    )

    # OpenAI (optional)
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model"
    )

    # Memory
    short_term_ttl_seconds: int = Field(
        default=3600,
        ge=1,
        description="Default TTL for short-term memories (seconds)",
    )
    cleanup_interval_seconds: int = Field(
        default=300,
        ge=60,  # Minimum 60s to prevent excessive disk I/O
        description="TTL cleanup interval in seconds (minimum 60)",
    )

    # Performance
    embedding_batch_size: int = Field(
        default=32,
        ge=1,
        le=1000,
        description="Batch size for embedding generation",
    )
    search_default_top_k: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Default number of search results",
    )

    # Batch operations
    batch_max_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum batch operation size",
    )

    # Rate limiting
    access_log_rate_limit_seconds: int = Field(
        default=60,
        ge=1,
        description="Access log rate limiting interval in seconds",
    )

    # Content limits
    max_content_length: int = Field(
        default=1_000_000,  # 1MB
        ge=1,
        description="Maximum content length in characters",
    )

    # Importance scoring
    importance_max_accesses: int = Field(
        default=100,
        ge=1,
        description="Maximum access count for importance calculation",
    )

    # RRF (Reciprocal Rank Fusion)
    rrf_constant: int = Field(
        default=60,
        ge=1,
        description="Reciprocal Rank Fusion constant (k)",
    )

    # Consolidation
    consolidation_min_memories: int = Field(
        default=2,
        ge=2,
        description="Minimum memories required for consolidation",
    )
    consolidation_max_memories: int = Field(
        default=50,
        ge=2,
        description="Maximum memories per consolidation batch",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Namespace settings
    default_namespace: str | None = Field(
        default=None,
        description="Default namespace for memories (None = auto-detect)",
    )
    namespace_auto_detect: bool = Field(
        default=True,
        description="Enable automatic namespace detection from project context",
    )

    # Semantic Cache settings
    cache_enabled: bool = Field(
        default=True,
        description="Enable semantic cache for query results",
    )
    cache_max_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum number of cache entries",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Cache entry time-to-live in seconds",
    )
    cache_similarity_threshold: float = Field(
        default=0.95,
        ge=0.8,
        le=1.0,
        description="Similarity threshold for cache hit",
    )

    # Token Counter settings
    token_counter_model: str = Field(
        default="gpt-4",
        description="Model name for tiktoken token counting",
    )
    token_buffer_ratio: float = Field(
        default=0.1,
        ge=0.0,
        le=0.3,
        description="Safety buffer ratio for token budget (0.1 = 10%)",
    )

    # Graph Traversal settings
    graph_max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Default maximum depth for graph traversal",
    )
    graph_max_results: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Default maximum results from graph traversal",
    )

    model_config = SettingsConfigDict(
        env_prefix="LLM_MEMORY_", env_file=".env", env_file_encoding="utf-8"
    )

    @model_validator(mode="after")
    def validate_provider_config(self) -> Self:
        """Validate provider-specific configuration."""
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "OpenAI API key is required when embedding_provider='openai'. "
                "Set LLM_MEMORY_OPENAI_API_KEY environment variable."
            )
        if self.consolidation_min_memories > self.consolidation_max_memories:
            raise ValueError(
                f"consolidation_min_memories ({self.consolidation_min_memories}) "
                f"must be <= consolidation_max_memories ({self.consolidation_max_memories})"
            )
        return self
