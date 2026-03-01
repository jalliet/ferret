"""Context efficiency benchmark tests.

Measures token reduction when using cross-encoder filtering vs dumping
raw fetched page text.  Requires network access and model loading.
"""

from __future__ import annotations

import pytest

from search_orchestrator.search import search_ddg
from search_orchestrator.fetch import fetch_parallel
from search_orchestrator.chunker import chunk_text
from search_orchestrator.scorer import score_chunks
from search_orchestrator.types import ScoredChunk


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

TOP_K = 5


def _estimate_tokens(text: str) -> float:
    """Rough token estimate: word count * 0.75."""
    return len(text.split()) * 0.75


def _run_pipeline(query: str, num_results: int = 10) -> dict:
    """Execute search -> fetch -> chunk -> score and return metrics.

    Returns a dict with keys:
        raw_tokens      – estimated tokens across all fetched text
        filtered_tokens – estimated tokens across top-k scored chunks
        scored_chunks   – list[ScoredChunk] sorted by score descending
        fetched_count   – number of URLs that returned usable text
    """
    # 1. Search
    results = search_ddg(query, num_results=num_results)
    urls = [r.url for r in results]

    # 2. Fetch
    fetched = fetch_parallel(urls)
    successful = [f for f in fetched if f.ok and f.text.strip()]

    # 3. Chunk + build ScoredChunk objects
    all_chunks: list[ScoredChunk] = []
    raw_text_parts: list[str] = []
    for fr in successful:
        raw_text_parts.append(fr.text)
        for idx, chunk_str in enumerate(chunk_text(fr.text)):
            all_chunks.append(
                ScoredChunk(
                    text=chunk_str,
                    source_url=fr.url,
                    chunk_index=idx,
                )
            )

    # 4. Score
    scored = score_chunks(query, all_chunks) if all_chunks else []

    # 5. Metrics
    raw_tokens = _estimate_tokens(" ".join(raw_text_parts))
    top_chunks = scored[:TOP_K]
    filtered_tokens = _estimate_tokens(" ".join(c.text for c in top_chunks))

    return {
        "raw_tokens": raw_tokens,
        "filtered_tokens": filtered_tokens,
        "scored_chunks": scored,
        "fetched_count": len(successful),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

QUERIES = [
    "how do large language models handle long context windows",
    "best practices for PostgreSQL indexing performance",
    "climate change effects on coral reef ecosystems",
]


@pytest.mark.network
@pytest.mark.slow
@pytest.mark.parametrize("query", QUERIES)
def test_token_reduction_ratio(query: str) -> None:
    """Filtered top-k chunks should be at least 3x smaller than raw text."""
    result = _run_pipeline(query)

    assert result["fetched_count"] > 0, "No pages were successfully fetched"
    assert result["raw_tokens"] > 0, "Raw token count should be positive"
    assert result["filtered_tokens"] > 0, "Filtered token count should be positive"

    ratio = result["raw_tokens"] / result["filtered_tokens"]
    assert ratio >= 3, (
        f"Token reduction ratio {ratio:.1f}x is below the 3x threshold "
        f"(raw={result['raw_tokens']:.0f}, filtered={result['filtered_tokens']:.0f})"
    )


@pytest.mark.network
@pytest.mark.slow
def test_scoring_produces_meaningful_separation() -> None:
    """Top chunk score should be significantly higher than bottom chunk score."""
    query = "how do large language models handle long context windows"
    result = _run_pipeline(query)
    scored = result["scored_chunks"]

    assert len(scored) >= 2, "Need at least 2 chunks to measure separation"

    top_score = scored[0].score
    bottom_score = scored[-1].score
    separation = top_score - bottom_score

    assert separation > 1.0, (
        f"Score separation {separation:.2f} is too small "
        f"(top={top_score:.4f}, bottom={bottom_score:.4f})"
    )


@pytest.mark.network
@pytest.mark.slow
def test_filtered_chunks_contain_relevant_content() -> None:
    """Top-5 chunks for a specific query should mention query-related terms."""
    query = "best practices for PostgreSQL indexing performance"
    result = _run_pipeline(query)
    scored = result["scored_chunks"]

    top_chunks = scored[:TOP_K]
    assert len(top_chunks) > 0, "No scored chunks returned"

    combined_text = " ".join(c.text for c in top_chunks).lower()

    # At least one of the core query concepts should appear in the top chunks.
    keywords = ["postgres", "index", "performance", "query", "database"]
    matches = [kw for kw in keywords if kw in combined_text]

    assert len(matches) >= 2, (
        f"Top-{TOP_K} chunks only matched {matches} out of {keywords}; "
        f"expected at least 2 query-related keywords"
    )
