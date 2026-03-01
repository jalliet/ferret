from __future__ import annotations

import pytest

from search_orchestrator.chunker import chunk_text


# ── Empty / whitespace inputs ──────────────────────────────────────────────

@pytest.mark.parametrize("text", ["", "   ", "\n\n", "\t  \n"])
def test_chunk_text_empty_or_whitespace_returns_empty_list(text: str):
    assert chunk_text(text) == []


# ── Single chunk (short text) ──────────────────────────────────────────────

def test_chunk_text_short_text_returns_single_chunk():
    text = "This is a short sentence."
    result = chunk_text(text, chunk_size=500)
    assert len(result) == 1
    assert result[0] == text


# ── Multiple chunks ────────────────────────────────────────────────────────

def _make_long_text(word_count: int) -> str:
    """Build text with sentence boundaries, roughly *word_count* words."""
    sentence = "The quick brown fox jumps over the lazy dog."  # 9 words
    repeats = (word_count // 9) + 1
    return " ".join([sentence] * repeats)


def test_chunk_text_long_text_splits_into_multiple_chunks():
    text = _make_long_text(1200)
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 2
    for chunk in chunks:
        word_count = len(chunk.split())
        # Each chunk should be within ±20% of target (except last)
        assert word_count <= 500 * 1.2 + 50  # allow overlap carry-over


def test_chunk_text_all_words_preserved():
    """Reassembling chunks (accounting for overlap) should cover all input words."""
    text = _make_long_text(600)
    chunks = chunk_text(text, chunk_size=200, overlap=30)
    # Every word in the original should appear in at least one chunk
    original_words = set(text.split())
    chunk_words = set()
    for c in chunks:
        chunk_words.update(c.split())
    assert original_words == chunk_words


# ── Overlap ────────────────────────────────────────────────────────────────

def test_chunk_text_overlap_words_appear_in_consecutive_chunks():
    """Exact overlap invariant: current impl slices word lists directly."""
    text = _make_long_text(800)
    overlap = 40
    chunks = chunk_text(text, chunk_size=200, overlap=overlap)
    assert len(chunks) >= 2
    for i in range(len(chunks) - 1):
        tail_words = chunks[i].split()[-overlap:]
        head_words = chunks[i + 1].split()[:overlap]
        assert tail_words == head_words


def test_chunk_text_zero_overlap_preserves_total_word_count():
    text = _make_long_text(800)
    original_words = len(text.split())
    chunks = chunk_text(text, chunk_size=200, overlap=0)
    assert len(chunks) >= 2
    # With overlap=0, total words across all chunks should equal the original
    total_chunk_words = sum(len(c.split()) for c in chunks)
    assert total_chunk_words == original_words, (
        f"With overlap=0, total chunk words ({total_chunk_words}) should equal "
        f"original word count ({original_words})"
    )


# ── Custom parameters ──────────────────────────────────────────────────────

def test_chunk_text_custom_chunk_size():
    text = _make_long_text(300)
    chunks = chunk_text(text, chunk_size=100, overlap=0)
    assert len(chunks) >= 3
    for chunk in chunks[:-1]:  # last chunk may be shorter
        word_count = len(chunk.split())
        assert word_count <= 120  # some tolerance for sentence alignment


def test_chunk_text_custom_overlap():
    text = _make_long_text(400)
    overlap = 20
    chunks = chunk_text(text, chunk_size=100, overlap=overlap)
    assert len(chunks) >= 2
    tail = chunks[0].split()[-overlap:]
    head = chunks[1].split()[:overlap:]
    assert tail == head


# ── No sentence boundaries ────────────────────────────────────────────────

def test_chunk_text_no_sentence_boundaries_still_chunks():
    """Text without .!? should still be returned (as a single 'sentence')."""
    words = ["word"] * 800
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=300, overlap=0)
    # Without sentence breaks the regex won't split, so entire text is one sentence.
    # Since that one sentence exceeds chunk_size, but there's nothing already accumulated
    # at the start, it gets added as-is (the split condition requires current_count > 0).
    assert len(chunks) >= 1
    total_words = sum(len(c.split()) for c in chunks)
    assert total_words == 800


def test_chunk_text_single_sentence_no_split():
    text = "Hello world this is a single sentence without ending punctuation"
    chunks = chunk_text(text, chunk_size=5, overlap=0)
    # No sentence boundary → one "sentence" → never triggers split (current_count starts 0)
    assert len(chunks) == 1
    assert chunks[0] == text
