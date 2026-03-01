from collections import OrderedDict


class ChunkCache:
    """LRU cache for scored chunks keyed by query string."""

    def __init__(self, max_queries: int = 50):
        self._cache: OrderedDict[str, list[dict]] = OrderedDict()
        self._max = max_queries

    def put(self, query: str, chunks: list[dict]) -> None:
        key = query.lower().strip()
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = chunks
        while len(self._cache) > self._max:
            self._cache.popitem(last=False)

    def get(self, query: str, offset: int = 0, limit: int = 5) -> tuple[list[dict], int]:
        """Return (chunks_slice, total_remaining)."""
        key = query.lower().strip()
        if key not in self._cache:
            return [], 0
        self._cache.move_to_end(key)
        all_chunks = self._cache[key]
        sliced = all_chunks[offset:offset + limit]
        remaining = max(0, len(all_chunks) - offset - limit)
        return sliced, remaining

    def has(self, query: str) -> bool:
        return query.lower().strip() in self._cache
