"""Integration tests for parallel fetch functionality.

These tests hit the network and require internet access.
Run with: .venv/bin/python -m pytest tests/test_fetch_integration.py -v -m network
"""

from __future__ import annotations

import pytest

from search_orchestrator.fetch import fetch_parallel


pytestmark = pytest.mark.network


def test_fetch_parallel_success():
    results = fetch_parallel(["https://httpbin.org/html"], max_workers=1)
    assert len(results) == 1
    r = results[0]
    assert r.ok is True, f"httpbin.org/html should succeed, got error: {r.error}"
    assert len(r.text) > 0, "Successful fetch should return non-empty text"


def test_fetch_parallel_http_error():
    results = fetch_parallel(["https://httpbin.org/status/403"], max_workers=1)
    assert len(results) == 1
    r = results[0]
    assert r.ok is False, "403 response should result in ok=False"


def test_fetch_parallel_dns_failure():
    results = fetch_parallel(["https://nonexistent.invalid/page"], max_workers=1)
    assert len(results) == 1
    r = results[0]
    assert r.ok is False, "DNS failure should result in ok=False"


def test_fetch_parallel_preserves_url_order():
    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/status/403",
        "https://nonexistent.invalid/page",
    ]
    results = fetch_parallel(urls, max_workers=3)
    assert len(results) == len(urls), "Should return one result per input URL"
    for i, (result, url) in enumerate(zip(results, urls)):
        assert result.url == url, (
            f"Result at index {i} should have url={url}, got {result.url}"
        )


def test_fetch_parallel_mixed_results():
    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/status/403",
        "https://nonexistent.invalid/page",
    ]
    results = fetch_parallel(urls, max_workers=3)
    assert len(results) == 3

    # First: success
    assert results[0].ok is True, "httpbin.org/html should succeed"
    assert len(results[0].text) > 0, "Successful fetch should have text"

    # Second: HTTP error
    assert results[1].ok is False, "403 should fail"

    # Third: DNS failure
    assert results[2].ok is False, "DNS failure should fail"
