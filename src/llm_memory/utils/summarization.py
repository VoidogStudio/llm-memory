"""Extractive summarization utilities."""

import re
from collections import Counter


def extractive_summary(
    text: str,
    max_length: int = 4000,
) -> str:
    """Generate extractive summary by selecting key sentences.

    Args:
        text: Input text to summarize
        max_length: Maximum output length in characters

    Returns:
        Summarized text
    """
    if len(text) <= max_length:
        return text

    sentences = split_sentences(text)
    if not sentences:
        return text[:max_length]

    # Calculate word frequency
    word_freq = calculate_word_frequency(text)

    # Score sentences
    sentence_scores = [(sent, score_sentence(sent, word_freq)) for sent in sentences]

    # Sort by score descending
    sentence_scores.sort(key=lambda x: x[1], reverse=True)

    # Select sentences until max_length
    selected = []
    current_length = 0

    for sentence, _ in sentence_scores:
        sentence_len = len(sentence) + 2  # +2 for separator
        if current_length + sentence_len <= max_length:
            selected.append(sentence)
            current_length += sentence_len
        else:
            break

    # Return in original order (use set for O(1) lookup)
    selected_set = set(selected)
    original_order = [sent for sent in sentences if sent in selected_set]

    return " ".join(original_order)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences.

    Args:
        text: Input text

    Returns:
        List of sentences
    """
    # Handle Japanese and English sentence boundaries
    pattern = r"(?<=[。！？.!?])\s*"
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def calculate_word_frequency(text: str) -> dict[str, float]:
    """Calculate normalized word frequency.

    Args:
        text: Input text

    Returns:
        Dictionary of word -> frequency score
    """
    # Simple word splitting (handles both Japanese and English)
    words = re.findall(r"\w+", text.lower())

    # Stop words (basic list)
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "の",
        "は",
        "が",
        "を",
        "に",
        "で",
        "と",
        "も",
        "や",
        "から",
    }

    filtered = [w for w in words if w not in stop_words and len(w) > 1]
    counter = Counter(filtered)

    # Normalize
    max_freq = max(counter.values()) if counter else 1
    return {word: count / max_freq for word, count in counter.items()}


def score_sentence(
    sentence: str,
    word_freq: dict[str, float],
) -> float:
    """Score a sentence based on word frequency.

    Args:
        sentence: Sentence to score
        word_freq: Word frequency dictionary

    Returns:
        Sentence score
    """
    words = re.findall(r"\w+", sentence.lower())
    if not words:
        return 0.0

    score = sum(word_freq.get(w, 0) for w in words)
    # Normalize by sentence length to avoid bias toward long sentences
    return score / len(words)
