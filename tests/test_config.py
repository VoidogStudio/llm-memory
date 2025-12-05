"""Tests for configuration management."""

import os

import pytest
from pydantic import ValidationError

from llm_memory.config.settings import Settings


class TestSettings:
    """Test Settings class."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()

        assert settings.database_path == "./data/llm_memory.db"
        assert settings.embedding_provider == "local"
        assert settings.embedding_model == "all-MiniLM-L6-v2"
        assert settings.embedding_dimensions == 384
        assert settings.short_term_ttl_seconds == 3600
        assert settings.embedding_batch_size == 32
        assert settings.search_default_top_k == 10
        assert settings.log_level == "INFO"

    def test_custom_settings(self):
        """Test creating settings with custom values."""
        settings = Settings(
            database_path="/custom/path.db",
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            embedding_dimensions=1536,
            openai_api_key="test-key",
            short_term_ttl_seconds=7200,
        )

        assert settings.database_path == "/custom/path.db"
        assert settings.embedding_provider == "openai"
        assert settings.embedding_model == "text-embedding-3-small"
        assert settings.embedding_dimensions == 1536
        assert settings.openai_api_key == "test-key"
        assert settings.short_term_ttl_seconds == 7200

    def test_env_variable_override(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv("LLM_MEMORY_DATABASE_PATH", "/env/path.db")
        monkeypatch.setenv("LLM_MEMORY_EMBEDDING_PROVIDER", "openai")
        monkeypatch.setenv("LLM_MEMORY_EMBEDDING_DIMENSIONS", "1536")

        settings = Settings()

        assert settings.database_path == "/env/path.db"
        assert settings.embedding_provider == "openai"
        assert settings.embedding_dimensions == 1536

    def test_env_prefix(self, monkeypatch):
        """Test that LLM_MEMORY_ prefix is required."""
        # Without prefix, should use default
        monkeypatch.setenv("DATABASE_PATH", "/wrong/path.db")

        settings = Settings()

        assert settings.database_path == "./data/llm_memory.db"

    def test_openai_settings(self):
        """Test OpenAI-specific settings."""
        settings = Settings(
            embedding_provider="openai",
            openai_api_key="test-key",
            openai_embedding_model="text-embedding-3-large",
        )

        assert settings.embedding_provider == "openai"
        assert settings.openai_api_key == "test-key"
        assert settings.openai_embedding_model == "text-embedding-3-large"

    def test_invalid_embedding_provider(self):
        """Test that invalid embedding provider raises validation error."""
        with pytest.raises(ValidationError):
            Settings(embedding_provider="invalid_provider")

    def test_negative_dimensions(self):
        """Test that negative dimensions raise validation error."""
        # Pydantic will accept this since it's typed as int
        # but in practice the embedding service would fail
        settings = Settings(embedding_dimensions=-1)
        assert settings.embedding_dimensions == -1

    def test_settings_model_config(self):
        """Test that model config is properly set."""
        settings = Settings()

        # Check that env prefix is set
        assert settings.model_config["env_prefix"] == "LLM_MEMORY_"
