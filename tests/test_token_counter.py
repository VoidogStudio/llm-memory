"""Tests for token counting utilities."""

import pytest

from src.utils.token_counter import (
    count_tokens,
    estimate_tokens,
    get_token_count,
    is_tiktoken_available,
)


class TestTiktokenAvailability:
    """Test tiktoken availability check."""

    def test_is_tiktoken_available(self):
        """Test tiktoken availability check returns bool."""
        result = is_tiktoken_available()
        assert isinstance(result, bool)


class TestCountTokens:
    """Test exact token counting with tiktoken."""

    def test_count_tokens_with_tiktoken(self):
        """Test accurate token counting if tiktoken available."""
        if not is_tiktoken_available():
            pytest.skip("tiktoken not available")

        count = count_tokens("Hello, world!")
        assert count > 0
        assert isinstance(count, int)

    def test_count_tokens_empty_string(self):
        """Test empty string returns 0 tokens."""
        if not is_tiktoken_available():
            pytest.skip("tiktoken not available")

        count = count_tokens("")
        assert count == 0

    def test_count_tokens_japanese(self):
        """Test Japanese text token counting."""
        if not is_tiktoken_available():
            pytest.skip("tiktoken not available")

        count = count_tokens("これはテストです。")
        assert count > 0

    def test_count_tokens_without_tiktoken_raises_error(self, monkeypatch):
        """Test count_tokens raises error if tiktoken unavailable."""
        import src.utils.token_counter as tc

        monkeypatch.setattr(tc, "TIKTOKEN_AVAILABLE", False)

        with pytest.raises(RuntimeError, match="tiktoken is not installed"):
            count_tokens("test")

    def test_count_tokens_with_different_models(self):
        """Test token counting with different model encodings."""
        if not is_tiktoken_available():
            pytest.skip("tiktoken not available")

        text = "This is a test sentence."

        # GPT-4 model
        count_gpt4 = count_tokens(text, model="gpt-4")
        assert count_gpt4 > 0

        # GPT-3.5 model
        count_gpt35 = count_tokens(text, model="gpt-3.5-turbo")
        assert count_gpt35 > 0

    def test_count_tokens_unknown_model_fallback(self):
        """Test unknown model falls back to cl100k_base encoding."""
        if not is_tiktoken_available():
            pytest.skip("tiktoken not available")

        count = count_tokens("Hello", model="unknown-model-xyz")
        assert count > 0


class TestEstimateTokens:
    """Test fallback token estimation."""

    def test_estimate_tokens_english(self):
        """Test English text token estimation."""
        text = "This is a test sentence with multiple words."
        count = estimate_tokens(text)
        assert count > 0
        # Rough check: English text ~1 token per 4 chars
        assert count > len(text) // 8

    def test_estimate_tokens_japanese(self):
        """Test Japanese text token estimation."""
        text = "これは日本語のテストメモリです。機械学習について説明しています。"
        count = estimate_tokens(text)
        assert count > 0
        # Japanese characters should count as ~0.7 tokens each
        assert count > 10

    def test_estimate_tokens_mixed(self):
        """Test mixed Japanese and English text."""
        text = "Pythonプログラミングの基礎を学びましょう。Variables, functions, classes."
        count = estimate_tokens(text)
        assert count > 0

    def test_estimate_tokens_empty_string(self):
        """Test empty string returns 0."""
        count = estimate_tokens("")
        assert count == 0

    def test_estimate_tokens_korean(self):
        """Test Korean text token estimation."""
        text = "한글 텍스트 테스트입니다."
        count = estimate_tokens(text)
        assert count > 0

    def test_estimate_tokens_chinese(self):
        """Test Chinese text token estimation."""
        text = "这是中文文本测试。"
        count = estimate_tokens(text)
        assert count > 0


class TestGetTokenCount:
    """Test unified token counting function."""

    def test_get_token_count_uses_tiktoken_if_available(self):
        """Test get_token_count uses tiktoken when available."""
        if not is_tiktoken_available():
            pytest.skip("tiktoken not available")

        text = "Hello, world!"
        count = get_token_count(text)
        assert count > 0
        # Should match count_tokens result
        assert count == count_tokens(text)

    def test_get_token_count_uses_estimate_without_tiktoken(self, monkeypatch):
        """Test get_token_count falls back to estimate without tiktoken."""
        import src.utils.token_counter as tc

        monkeypatch.setattr(tc, "TIKTOKEN_AVAILABLE", False)

        text = "This is a test."
        count = get_token_count(text)
        assert count > 0
        # Should match estimate_tokens result
        assert count == estimate_tokens(text)

    def test_get_token_count_empty_string(self):
        """Test empty string returns 0."""
        count = get_token_count("")
        assert count == 0

    def test_get_token_count_with_model_parameter(self):
        """Test get_token_count accepts model parameter."""
        if not is_tiktoken_available():
            pytest.skip("tiktoken not available")

        text = "Test with model parameter"
        count = get_token_count(text, model="gpt-3.5-turbo")
        assert count > 0


class TestEdgeCases:
    """Test edge cases and special inputs."""

    def test_very_long_text(self):
        """Test token counting for very long text."""
        long_text = "This is a test sentence. " * 1000
        count = get_token_count(long_text)
        assert count > 1000

    def test_special_characters(self):
        """Test token counting with special characters."""
        text = "Test with special chars: @#$%^&*()[]{}|\\;:'\",<.>/?`~"
        count = get_token_count(text)
        assert count > 0

    def test_unicode_emojis(self):
        """Test token counting with emojis."""
        text = "Hello 👋 world 🌍 with emojis 😊"
        count = get_token_count(text)
        assert count > 0

    def test_newlines_and_whitespace(self):
        """Test token counting with various whitespace."""
        text = "Line 1\n\nLine 2\t\tLine 3    Line 4"
        count = get_token_count(text)
        assert count > 0

    def test_numbers_and_symbols(self):
        """Test token counting with numbers."""
        text = "Numbers: 123456789 and symbols: $100.50"
        count = get_token_count(text)
        assert count > 0
