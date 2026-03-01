from __future__ import annotations
from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from search_orchestrator.types import ScoredChunk


class ChunkCache:
    """LRU cache for scored chunks keyed by query string."""

    def __init__(self, max_queries: int = 50):
        self._cache: OrderedDict[str, list[ScoredChunk]] = OrderedDict()
        self._max = max_queries

    def _key(self, query: str) -> str:
        return query.lower().strip()

    def put(self, query: str, chunks: list[ScoredChunk]) -> None:
        key = self._key(query)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = chunks
        while len(self._cache) > self._max:
            self._cache.popitem(last=False)

    def get(self, query: str, offset: int = 0, limit: int = 5) -> tuple[list[ScoredChunk], int]:
        """Return (chunks_slice, total_remaining). Returns ([], 0) if not cached."""
        key = self._key(query)
        if key not in self._cache:
            return [], 0
        self._cache.move_to_end(key)
        all_chunks = self._cache[key]
        sliced = all_chunks[offset:offset + limit]
        remaining = max(0, len(all_chunks) - offset - limit)
        return sliced, remaining
