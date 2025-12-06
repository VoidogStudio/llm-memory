"""Tokenization service for FTS5 support."""

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sudachipy import Tokenizer

logger = logging.getLogger(__name__)


class TokenizationService:
    """Service for text tokenization (Japanese support via SudachiPy)."""

    _instance: "TokenizationService | None" = None
    _tokenizer: "Tokenizer | None" = None
    _has_sudachipy: bool = False
    _initialized: bool = False
    _lock = threading.Lock()

    def __new__(cls) -> "TokenizationService":
        """Singleton pattern for tokenizer reuse with thread safety."""
        # Double-checked locking pattern for thread-safe singleton
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize tokenization service (lazy loading)."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._check_sudachipy()
                    self._initialized = True

    def _check_sudachipy(self) -> None:
        """Check if SudachiPy is available."""
        try:
            from sudachipy import Dictionary

            self._tokenizer = Dictionary(dict_type="core").create()
            self._has_sudachipy = True
            logger.info("SudachiPy initialized successfully")
        except ImportError:
            self._has_sudachipy = False
            logger.info(
                "SudachiPy not available, using basic tokenizer. "
                "Install with: pip install 'llm-memory[japanese]'"
            )

    @property
    def has_japanese_support(self) -> bool:
        """Check if Japanese tokenization is available."""
        return self._has_sudachipy

    def tokenize(self, text: str) -> str:
        """Tokenize text for FTS5 storage/search.

        Args:
            text: Input text

        Returns:
            Tokenized text (space-separated tokens)
        """
        if not text:
            return ""

        if self._has_sudachipy and self._tokenizer:
            from sudachipy import SplitMode

            tokens = self._tokenizer.tokenize(text, SplitMode.C)
            return " ".join([t.surface() for t in tokens])
        else:
            # Fallback: return original text
            # unicode61 tokenizer will handle it
            return text

    def tokenize_query(self, query: str) -> str:
        """Tokenize search query for FTS5 MATCH.

        Args:
            query: Search query

        Returns:
            Tokenized query suitable for FTS5 MATCH
        """
        tokenized = self.tokenize(query)

        # Escape special FTS5 characters to prevent query injection
        # FTS5 special characters: " * : ( ) { } [ ] < > = ^
        # Double quotes are used for phrase matching, so escape them by doubling
        escaped = tokenized.replace('"', '""')

        # Wrap in quotes to treat as phrase search (safer than allowing operators)
        # This prevents injection via AND, OR, NOT, NEAR, * operators
        return f'"{escaped}"'
