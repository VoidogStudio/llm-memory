"""Token counting utilities with tiktoken support and fallback."""

from typing import Literal

# Optional tiktoken import
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None  # type: ignore
    TIKTOKEN_AVAILABLE = False


ModelName = Literal["gpt-4", "gpt-4o", "gpt-3.5-turbo", "text-embedding-3-small"]


def is_tiktoken_available() -> bool:
    """Check if tiktoken library is available.

    Returns:
        True if tiktoken is available, False otherwise
    """
    return TIKTOKEN_AVAILABLE


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens using tiktoken (accurate method).

    Args:
        text: Text to count tokens for
        model: Model name for tokenizer

    Returns:
        Exact token count

    Raises:
        RuntimeError: If tiktoken is not available
    """
    if not TIKTOKEN_AVAILABLE:
        raise RuntimeError(
            "tiktoken is not installed. Install with: pip install tiktoken"
        )

    if not text:
        return 0

    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base for unknown models
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens = encoding.encode(text)
    return len(tokens)


def estimate_tokens(text: str) -> int:
    """Estimate token count without tiktoken (fallback method).

    Uses character-based estimation with different ratios for
    Japanese/CJK characters vs English words.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Count CJK characters (Japanese, Chinese, Korean)
    cjk_count = sum(
        1
        for char in text
        if "\u4e00" <= char <= "\u9fff"  # CJK Unified Ideographs
        or "\u3040" <= char <= "\u309f"  # Hiragana
        or "\u30a0" <= char <= "\u30ff"  # Katakana
        or "\uac00" <= char <= "\ud7af"  # Hangul
    )

    # Estimate tokens
    # CJK: approximately 0.7 tokens per character
    # English: approximately len/4 (rough average)
    cjk_tokens = int(cjk_count * 0.7)
    remaining_chars = len(text) - cjk_count
    english_tokens = max(0, remaining_chars // 4)

    return cjk_tokens + english_tokens


def get_token_count(text: str, model: str = "gpt-4") -> int:
    """Get token count (uses tiktoken if available, otherwise estimates).

    Args:
        text: Text to count tokens for
        model: Model name for tokenizer (only used if tiktoken available)

    Returns:
        Token count (exact if tiktoken available, estimated otherwise)
    """
    if TIKTOKEN_AVAILABLE:
        return count_tokens(text, model)
    return estimate_tokens(text)
