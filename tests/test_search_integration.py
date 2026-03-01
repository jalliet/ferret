"""Integration tests for DDG search functionality.

These tests hit the network and require internet access.
Run with: .venv/bin/python -m pytest tests/test_search_integration.py -v -m network
"""

from __future__ import annotations

import pytest

from search_orchestrator.search import search_ddg


pytestmark = pytest.mark.network


class TestSearchDDGReturnsResults:
    def test_results_have_required_attributes(self):
        results = search_ddg("python web scraping")
        assert len(results) > 0, "DDG search should return at least one result"
        for r in results:
            assert hasattr(r, "title"), "Each result should have a title attribute"
            assert hasattr(r, "url"), "Each result should have a url attribute"
            assert hasattr(r, "snippet"), "Each result should have a snippet attribute"

    def test_urls_are_absolute(self):
        results = search_ddg("python web scraping")
        for r in results:
            assert r.url.startswith("http"), (
                f"URL should be absolute (start with http), got: {r.url}"
            )

    def test_titles_are_non_empty(self):
        results = search_ddg("python web scraping")
        for r in results:
            assert len(r.title) > 0, "Each result should have a non-empty title"


def test_search_ddg_respects_num_results_limit():
    results = search_ddg("python web scraping", num_results=5)
    assert len(results) <= 5, (
        f"Requested num_results=5 but got {len(results)} results"
    )


def test_search_ddg_unusual_query_handles_gracefully():
    """An unusual/niche query should either return results or an empty list, not crash."""
    results = search_ddg("xyzzy_nonexistent_gibberish_query_12345")
    assert isinstance(results, list), "Should return a list even for unusual queries"
