from mcp.server.fastmcp import FastMCP
from search_orchestrator.search import search_ddg
from search_orchestrator.fetch import fetch_parallel, stealth_fetch_one
from search_orchestrator.chunker import chunk_text
from search_orchestrator.scorer import score_chunks
from search_orchestrator.cache import ChunkCache
from search_orchestrator.types import ScoredChunk

mcp = FastMCP(name="ferret-search-orchestrator")
_cache = ChunkCache()


@mcp.tool()
def search_and_scrape(query: str, num_results: int = 10, top_k: int = 5) -> dict:
    """Search the web and return top relevant content chunks.

    Searches DuckDuckGo, fetches top URLs in parallel, extracts text,
    chunks and scores by relevance. Results are cached for pagination via get_more.

    Args:
        query: Search query string.
        num_results: Number of search results to fetch (default 10).
        top_k: Number of top-scoring chunks to return (default 5).
    """
    search_results = search_ddg(query, num_results=num_results)
    if not search_results:
        return {"error": "No search results found", "chunks": [], "failed_urls": []}

    urls = [r.url for r in search_results]

    fetch_results = fetch_parallel(urls)
    successful = [r for r in fetch_results if r.ok]
    failed = [{"url": r.url, "error": r.error} for r in fetch_results if not r.ok]

    all_chunks: list[ScoredChunk] = []
    for result in successful:
        chunks = chunk_text(result.text)
        for i, text in enumerate(chunks):
            all_chunks.append(ScoredChunk(text=text, source_url=result.url, chunk_index=i))

    if not all_chunks:
        return {"error": "No content extracted", "chunks": [], "failed_urls": failed}

    scored = score_chunks(query, all_chunks)
    _cache.put(query, scored)

    return {
        "chunks": [c.to_dict() for c in scored[:top_k]],
        "total_cached": len(scored),
        "sources_fetched": len(successful),
        "failed_urls": failed,
    }


@mcp.tool()
def get_more(query: str, offset: int = 0, limit: int = 5) -> dict:
    """Paginate through cached scored chunks from a previous search.

    Zero network cost — returns chunks from the in-memory cache.

    Args:
        query: The same query string used in search_and_scrape.
        offset: Starting index into the cached chunk list.
        limit: Number of chunks to return.
    """
    chunks, remaining = _cache.get(query, offset=offset, limit=limit)
    if not chunks and remaining == 0:
        return {"error": f"No cached results for query: '{query}'", "chunks": [], "remaining": 0}
    return {"chunks": [c.to_dict() for c in chunks], "remaining": remaining, "offset": offset}


@mcp.tool()
def stealth_fetch(url: str) -> dict:
    """Fetch a single URL using stealth browser (Camoufox).

    Use this for URLs that failed in search_and_scrape due to bot detection.
    Slower (3-10s) but bypasses most anti-bot protections.

    Args:
        url: The URL to fetch with stealth browser.
    """
    result = stealth_fetch_one(url)
    if not result.ok:
        return {"error": result.error, "url": url, "text": ""}
    return {"url": url, "text": result.text, "char_count": len(result.text)}
