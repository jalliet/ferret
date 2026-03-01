"""Integration tests for the full search-and-scrape pipeline.

These tests hit the network and are slow (each pipeline call fetches multiple URLs).
Run with: .venv/bin/python -m pytest tests/test_pipeline_integration.py -v -m network
"""

from __future__ import annotations

import time

import pytest

from search_orchestrator.server import search_and_scrape, get_more


pytestmark = [pytest.mark.network, pytest.mark.slow]


# ── Basic pipeline tests ─────────────────────────────────────────────


@pytest.fixture(scope="module")
def pipeline_result():
    """Run search_and_scrape once and share the result across tests in this module."""
    return search_and_scrape("python web scraping best practices")


def test_search_and_scrape_returns_scored_chunks(pipeline_result):
    result = pipeline_result
    assert len(result["chunks"]) > 0, "Pipeline should return at least one chunk"
    assert result["sources_fetched"] > 0, "Pipeline should fetch at least one source"
    for chunk in result["chunks"]:
        assert "score" in chunk, "Each chunk must have a score"
        assert "text" in chunk, "Each chunk must have text"
        assert "source_url" in chunk, "Each chunk must have a source_url"


def test_search_and_scrape_scores_sorted_descending(pipeline_result):
    scores = [c["score"] for c in pipeline_result["chunks"]]
    assert scores == sorted(scores, reverse=True), (
        "Chunks should be sorted by score in descending order"
    )


def test_search_and_scrape_caches_results(pipeline_result):
    result = pipeline_result
    assert result["total_cached"] > len(result["chunks"]), (
        f"total_cached ({result['total_cached']}) should exceed returned chunks "
        f"({len(result['chunks'])}), indicating more results are cached for pagination"
    )


# ── get_more tests ───────────────────────────────────────────────────


def test_get_more_returns_cached_chunks(pipeline_result):
    """After search_and_scrape, get_more should return cached chunks instantly."""
    t0 = time.time()
    more = get_more("python web scraping best practices", offset=0, limit=5)
    dt = time.time() - t0

    assert len(more["chunks"]) > 0, "get_more should return cached chunks"
    assert more["remaining"] >= 0, "remaining should be non-negative"
    assert dt < 1.0, f"get_more should be near-instant (cached), took {dt:.2f}s"


def test_get_more_unknown_query_returns_error():
    result = get_more("completely_unknown_query_that_was_never_searched")
    assert "error" in result, "get_more for unknown query should return an error key"
    assert len(result["chunks"]) == 0, "Unknown query should return no chunks"


# ── Research breadth parametrized test ───────────────────────────────


RESEARCH_QUERIES = [
    "how does transformer attention mechanism work in large language models",
    "best practices for building MCP servers with Python",
    "comparison of web scraping libraries python 2025",
    "what causes hallucination in AI models and how to mitigate",
    "rust vs go for backend systems performance comparison",
]


@pytest.mark.parametrize("query", RESEARCH_QUERIES)
def test_research_breadth(query):
    result = search_and_scrape(query, num_results=10, top_k=5)
    assert result["sources_fetched"] >= 3, (
        f"Expected >=3 sources fetched for '{query}', got {result['sources_fetched']}"
    )
    assert len(result["chunks"]) >= 1, (
        f"Expected >=1 chunk returned for '{query}', got {len(result['chunks'])}"
    )
