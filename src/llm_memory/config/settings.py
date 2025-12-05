"""Application settings management using Pydantic Settings."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    # Database
    database_path: str = Field(
        default="./data/llm_memory.db", description="SQLite database file path"
    )

    # Embedding
    embedding_provider: Literal["local", "openai"] = Field(
        default="local", description="Embedding provider to use"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Embedding model name"
    )
    embedding_dimensions: int = Field(default=384, description="Embedding vector dimensions")

    # OpenAI (optional)
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model"
    )

    # Memory
    short_term_ttl_seconds: int = Field(
        default=3600, description="Default TTL for short-term memories (seconds)"
    )

    # Performance
    embedding_batch_size: int = Field(
        default=32, description="Batch size for embedding generation"
    )
    search_default_top_k: int = Field(default=10, description="Default number of search results")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = SettingsConfigDict(
        env_prefix="LLM_MEMORY_", env_file=".env", env_file_encoding="utf-8"
    )
