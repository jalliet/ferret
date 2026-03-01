"""Unit tests for search_orchestrator.scorer — cross-encoder relevance scoring."""

from __future__ import annotations

import pytest

from search_orchestrator.scorer import score_chunks


pytestmark = pytest.mark.slow


def test_score_chunks_empty_input_returns_empty_list(make_scored_chunk):
    """score_chunks with an empty list returns [] without loading the model."""
    result = score_chunks("any query", [])
    assert result == []


def test_score_chunks_relevant_text_ranks_above_irrelevant(make_scored_chunk):
    """A chunk semantically relevant to the query ranks above an irrelevant one."""
    query = "What is the capital of France?"
    relevant = make_scored_chunk(
        text="Paris is the capital and most populous city of France.",
        chunk_index=0,
        score=0.0,
    )
    moderate = make_scored_chunk(
        text="France is a country in Western Europe known for its culture.",
        chunk_index=1,
        score=0.0,
    )
    irrelevant = make_scored_chunk(
        text="The mitochondria is the powerhouse of the cell.",
        chunk_index=2,
        score=0.0,
    )

    result = score_chunks(query, [irrelevant, moderate, relevant])

    assert result[-1] is irrelevant, "Irrelevant chunk should rank last"


def test_score_chunks_scores_are_set(make_scored_chunk):
    """Every chunk has a non-zero float score after scoring."""
    chunks = [
        make_scored_chunk(text="Python is a programming language.", chunk_index=0, score=0.0),
        make_scored_chunk(text="JavaScript runs in the browser.", chunk_index=1, score=0.0),
    ]

    result = score_chunks("What programming languages exist?", chunks)

    for chunk in result:
        assert isinstance(chunk.score, float)
        assert chunk.score != 0.0


def test_score_chunks_sorted_descending(make_scored_chunk):
    """Returned list is sorted by score in descending order."""
    chunks = [
        make_scored_chunk(text="Unrelated: baking sourdough bread.", chunk_index=0, score=0.0),
        make_scored_chunk(text="Machine learning uses neural networks.", chunk_index=1, score=0.0),
        make_scored_chunk(text="Deep learning is a subset of machine learning.", chunk_index=2, score=0.0),
    ]

    result = score_chunks("Explain deep learning and neural networks", chunks)

    scores = [c.score for c in result]
    assert scores == sorted(scores, reverse=True)


def test_score_chunks_single_chunk(make_scored_chunk):
    """Works correctly with a single-element list."""
    chunk = make_scored_chunk(text="Rust is a systems programming language.", chunk_index=0, score=0.0)

    result = score_chunks("Tell me about Rust programming", [chunk])

    assert len(result) == 1
    assert result[0] is chunk
    assert isinstance(result[0].score, float)
    assert result[0].score != 0.0


def test_score_chunks_mutates_original_objects(make_scored_chunk):
    """score_chunks mutates the original ScoredChunk objects, not copies."""
    original_chunks = [
        make_scored_chunk(text="Original chunk about databases.", chunk_index=0, score=0.0),
        make_scored_chunk(text="Another chunk about SQL queries.", chunk_index=1, score=0.0),
    ]

    score_chunks("database management", original_chunks)

    for chunk in original_chunks:
        assert chunk.score != 0.0, "Original object's score should be mutated"
