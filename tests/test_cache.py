from __future__ import annotations

import pytest

from search_orchestrator.cache import ChunkCache


# ── Basic put / get ────────────────────────────────────────────────────────

def test_put_then_get_returns_correct_chunks(cache, scored_chunks):
    cache.put("python async", scored_chunks)
    result, remaining = cache.get("python async")
    assert result == scored_chunks
    assert remaining == 0


def test_get_unknown_query_returns_empty(cache):
    result, remaining = cache.get("nonexistent query")
    assert result == []
    assert remaining == 0


# ── Offset / limit / remaining ─────────────────────────────────────────────

def test_get_with_offset_returns_correct_slice(cache, scored_chunks):
    cache.put("q", scored_chunks)
    result, remaining = cache.get("q", offset=1, limit=5)
    assert result == scored_chunks[1:]
    assert remaining == 0


def test_get_with_limit_returns_correct_slice_and_remaining(cache, scored_chunks):
    cache.put("q", scored_chunks)
    result, remaining = cache.get("q", offset=0, limit=2)
    assert result == scored_chunks[:2]
    assert remaining == 1


def test_get_with_offset_and_limit(cache, scored_chunks):
    cache.put("q", scored_chunks)
    result, remaining = cache.get("q", offset=1, limit=1)
    assert result == [scored_chunks[1]]
    assert remaining == 1


def test_get_offset_beyond_bounds_returns_empty(cache, scored_chunks):
    cache.put("q", scored_chunks)
    result, remaining = cache.get("q", offset=100, limit=5)
    assert result == []
    assert remaining == 0


# ── LRU eviction ───────────────────────────────────────────────────────────

def test_lru_eviction_oldest_removed(make_scored_chunk):
    small_cache = ChunkCache(max_queries=3)
    for i in range(4):
        small_cache.put(f"query{i}", [make_scored_chunk(text=f"chunk {i}")])

    # query0 should have been evicted
    result, _ = small_cache.get("query0")
    assert result == []

    # query1, query2, query3 should remain
    for i in range(1, 4):
        result, _ = small_cache.get(f"query{i}")
        assert len(result) == 1


def test_lru_access_refreshes_entry(make_scored_chunk):
    small_cache = ChunkCache(max_queries=3)
    for i in range(3):
        small_cache.put(f"query{i}", [make_scored_chunk(text=f"chunk {i}")])

    # Access query0 to refresh it
    small_cache.get("query0")

    # Add a new query — query1 (oldest untouched) should be evicted
    small_cache.put("query3", [make_scored_chunk(text="chunk 3")])

    result, _ = small_cache.get("query1")
    assert result == []

    result, _ = small_cache.get("query0")
    assert len(result) == 1


# ── Key normalization ──────────────────────────────────────────────────────

@pytest.mark.parametrize("variant", [
    "Python Async",
    "PYTHON ASYNC",
    "  python async  ",
    " Python Async ",
])
def test_cache_key_is_case_insensitive_and_whitespace_normalized(cache, scored_chunks, variant):
    cache.put("python async", scored_chunks)
    result, _ = cache.get(variant)
    assert result == scored_chunks


# ── Put updates existing key ───────────────────────────────────────────────

def test_put_existing_key_updates_value(cache, make_scored_chunk):
    old_chunks = [make_scored_chunk(text="old")]
    new_chunks = [make_scored_chunk(text="new")]

    cache.put("query", old_chunks)
    cache.put("query", new_chunks)

    result, _ = cache.get("query")
    assert result == new_chunks
    # Verify no duplicate entries — cache size should be 1
    assert len(cache._cache) == 1


def test_put_existing_key_moves_to_end(make_scored_chunk):
    small_cache = ChunkCache(max_queries=3)
    for i in range(3):
        small_cache.put(f"query{i}", [make_scored_chunk(text=f"chunk {i}")])

    # Re-put query0 to move it to end
    small_cache.put("query0", [make_scored_chunk(text="updated 0")])

    # Add query3 — query1 (now oldest) should be evicted
    small_cache.put("query3", [make_scored_chunk(text="chunk 3")])

    result, _ = small_cache.get("query1")
    assert result == []

    result, _ = small_cache.get("query0")
    assert len(result) == 1
    assert result[0].text == "updated 0"
