"""Configuration module for LLM Memory."""

from src.config.settings import Settings

# Global settings instance (lazy-loaded singleton)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance.

    Returns a cached singleton instance of Settings. The settings are
    loaded from environment variables on first access.

    Returns:
        The global Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def set_settings(settings: Settings) -> None:
    """Set the global settings instance.

    This is primarily useful for testing or when you need to
    override settings programmatically.

    Args:
        settings: Settings instance to use globally
    """
    global _settings
    _settings = settings


def reset_settings() -> None:
    """Reset the global settings instance.

    This forces settings to be reloaded on next access.
    Primarily useful for testing.
    """
    global _settings
    _settings = None


__all__ = ["Settings", "get_settings", "set_settings", "reset_settings"]
