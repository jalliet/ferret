"""Phase 4 validation: smoke tests for all search_orchestrator modules.

Run from project root: PYTHONPATH=. .venv/bin/python data/test_orchestrator.py
"""

import csv
import time

results = []  # (module, test, detail) — all PASS or script dies on assert


def ok(module, test, detail=""):
    results.append((module, test, detail))
    print(f"  PASS — {test}: {detail}" if detail else f"  PASS — {test}")


# ── DDG search ────────────────────────────────────────────────────────
print("\nTEST: search")
from search_orchestrator.search import search_ddg

r = search_ddg("python web scraping")
assert len(r) > 0 and all(k in r[0] for k in ("title", "url", "snippet"))
assert all(r_item["url"].startswith("http") for r_item in r), "All URLs should be absolute"
assert all(len(r_item["title"]) > 0 for r_item in r), "All results should have titles"
ok("search", "ddg_search", f"{len(r)} results, first: {r[0]['title'][:50]}")

# Verify num_results limit
r5 = search_ddg("python web scraping", num_results=5)
assert len(r5) <= 5, f"num_results=5 should return <=5, got {len(r5)}"
ok("search", "num_results_limit", f"requested 5, got {len(r5)}")

# ── Parallel fetch ────────────────────────────────────────────────────
print("\nTEST: fetch")
from search_orchestrator.fetch import fetch_parallel, _extract_text

# Test text extraction on realistic HTML with boilerplate
realistic_html = """
<html><head><title>Test Page</title>
<style>.nav{color:red}</style>
<script>var x = 1; console.log("tracking");</script>
</head><body>
<nav><ul><li>Home</li><li>About</li><li>Contact</li></ul></nav>
<header><h1>Site Header</h1><div class="logo">Brand</div></header>
<main>
<article>
<h2>Web Scraping Best Practices</h2>
<p>When scraping websites, always respect robots.txt and rate limits.
Use appropriate headers and identify your bot with a User-Agent string.</p>
<p>Consider using libraries like BeautifulSoup or Scrapling for parsing HTML.
These tools handle malformed markup gracefully and provide CSS selector support.</p>
</article>
</main>
<footer><p>Copyright 2025. All rights reserved.</p><nav>Footer nav links</nav></footer>
</body></html>
"""
text = _extract_text(realistic_html)
# Content should survive
assert "Web Scraping Best Practices" in text, "Article heading should survive"
assert "respect robots.txt" in text, "Article content should survive"
assert "BeautifulSoup or Scrapling" in text, "Article content should survive"
# Boilerplate should be stripped
assert "tracking" not in text, "Scripts should be stripped"
assert "color:red" not in text, "Styles should be stripped"
assert "Copyright 2025" not in text, "Footer should be stripped"
assert "Site Header" not in text, "Header should be stripped"
ok("fetch", "extract_text_realistic", "content preserved, boilerplate stripped")

# Test parallel fetch on multiple URLs including a mix of success/failure
test_urls = [
    "https://httpbin.org/html",          # known good
    "https://httpbin.org/status/403",     # will return 403
    "https://nonexistent.invalid/page",   # DNS failure
]
fetched = fetch_parallel(test_urls, max_workers=3)
assert len(fetched) == 3, "Should return result for every URL"
assert fetched[0]["url"] == test_urls[0], "Results should preserve URL order"
assert fetched[1]["url"] == test_urls[1], "Results should preserve URL order"
assert fetched[2]["url"] == test_urls[2], "Results should preserve URL order"
# First should succeed
assert fetched[0]["error"] is None and len(fetched[0]["text"]) > 0
# Second should fail (403)
assert fetched[1]["error"] is not None
# Third should fail (DNS)
assert fetched[2]["error"] is not None
ok("fetch", "fetch_parallel_mixed", f"1 success, 2 failures handled gracefully")

# ── Chunker ───────────────────────────────────────────────────────────
print("\nTEST: chunker")
from search_orchestrator.chunker import chunk_text

assert chunk_text("") == [] and chunk_text("   ") == []
ok("chunker", "empty_input", "returns []")

# Single short paragraph stays as one chunk
short = "Web scraping is the process of extracting data from websites. It involves fetching pages and parsing their content."
assert len(chunk_text(short)) == 1
ok("chunker", "short_text", "1 chunk")

# Realistic multi-paragraph text
long_text = (
    "Web scraping is a technique for extracting information from websites. "
    "It involves making HTTP requests to web servers and parsing the HTML responses. "
    "Python has several libraries that make web scraping straightforward. "
    "BeautifulSoup is one of the most popular HTML parsing libraries. "
    "It provides methods for navigating and searching the parse tree. "
    "Scrapling is a newer library that adds anti-bot detection capabilities. "
) * 50  # ~300 sentences, ~1800 words
chunks = chunk_text(long_text, chunk_size=500, overlap=50)
assert len(chunks) >= 3, f"Expected >=3 chunks from ~1800 words, got {len(chunks)}"
word_counts = [len(c.split()) for c in chunks]
# All chunks except last should be close to target size
for i, wc in enumerate(word_counts[:-1]):
    assert 400 <= wc <= 600, f"Chunk {i} has {wc} words, expected ~500"
ok("chunker", "long_text", f"{len(chunks)} chunks, word counts: {word_counts}")

# Overlap: end of chunk N should appear at start of chunk N+1
last_words = set(chunks[0].split()[-30:])
first_words = set(chunks[1].split()[:60])
overlap_count = len(last_words & first_words)
assert overlap_count >= 10, f"Expected >=10 overlapping words, got {overlap_count}"
ok("chunker", "overlap", f"{overlap_count} words shared between chunks 0 and 1")

# ── Cross-encoder scorer ──────────────────────────────────────────────
print("\nTEST: scorer")
from search_orchestrator.scorer import score_chunks

scored = score_chunks("python web scraping", [
    {"text": "python web scraping tutorial with beautifulsoup requests library", "source_url": "relevant.com", "chunk_index": 0},
    {"text": "cooking recipes for dinner tonight with fresh vegetables", "source_url": "irrelevant.com", "chunk_index": 0},
    {"text": "web scraping python requests library http parsing html", "source_url": "also-relevant.com", "chunk_index": 0},
])
assert len(scored) == 3 and all("score" in c for c in scored)
assert scored[0]["score"] >= scored[1]["score"] >= scored[2]["score"]
assert scored[-1]["source_url"] == "irrelevant.com", "Irrelevant content should rank last"
assert scored[-1]["score"] < scored[0]["score"], "Irrelevant should score lower than relevant"
ok("scorer", "relevance_ranking", f"{[(c['source_url'].split('.')[0], c['score']) for c in scored]}")

assert score_chunks("query", []) == []
ok("scorer", "empty_input", "returns []")

# ── LRU cache ─────────────────────────────────────────────────────────
print("\nTEST: cache")
from search_orchestrator.cache import ChunkCache

cache = ChunkCache(max_queries=2)
cache.put("query1", [{"a": 1}, {"b": 2}, {"c": 3}])
chunks_out, remaining = cache.get("query1", offset=0, limit=2)
assert len(chunks_out) == 2 and remaining == 1
ok("cache", "put_get", "2 returned, 1 remaining")

# Offset beyond bounds
chunks_out, remaining = cache.get("query1", offset=10, limit=5)
assert len(chunks_out) == 0 and remaining == 0
ok("cache", "offset_beyond_bounds", "returns empty, 0 remaining")

cache.put("query2", [{"d": 4}])
cache.put("query3", [{"e": 5}])
q1_chunks, _ = cache.get("query1")
q2_chunks, _ = cache.get("query2")
q3_chunks, _ = cache.get("query3")
assert len(q1_chunks) == 0 and len(q2_chunks) > 0 and len(q3_chunks) > 0
ok("cache", "lru_eviction", "oldest evicted at max_queries=2")

cache2 = ChunkCache()
cache2.put("Python Scraping", [{"f": 6}])
lower_chunks, _ = cache2.get("python scraping")
padded_chunks, _ = cache2.get("  Python Scraping  ")
assert len(lower_chunks) > 0 and len(padded_chunks) > 0
ok("cache", "case_insensitive", "normalized keys")

# Unknown query
chunks_out, remaining = cache2.get("never searched")
assert len(chunks_out) == 0 and remaining == 0
ok("cache", "unknown_query", "returns empty gracefully")

# ── Full pipeline ─────────────────────────────────────────────────────
print("\nTEST: pipeline")
from search_orchestrator.server import search_and_scrape, get_more

t0 = time.time()
result = search_and_scrape("python web scraping best practices")
dt = time.time() - t0
assert len(result["chunks"]) > 0 and result["total_cached"] > len(result["chunks"])
assert result["sources_fetched"] > 0, "Should have fetched some sources"
assert all("score" in c and "text" in c and "source_url" in c for c in result["chunks"]), "Chunks should have score, text, source_url"
# Scores should be in descending order
scores = [c["score"] for c in result["chunks"]]
assert scores == sorted(scores, reverse=True), "Chunks should be sorted by score descending"
ok("pipeline", "search_and_scrape", f"{result['total_cached']} cached from {result['sources_fetched']} sources, {len(result['failed_urls'])} failed ({dt:.1f}s)")

t0 = time.time()
more = get_more("python web scraping best practices", offset=5, limit=5)
dt = time.time() - t0
assert len(more["chunks"]) > 0 and more["remaining"] >= 0 and dt < 1.0
ok("pipeline", "get_more", f"{more['remaining']} remaining ({dt:.3f}s — cached)")

assert "error" in get_more("nonexistent query")
ok("pipeline", "get_more_unknown", "returns error")

# ── Summary + CSV ─────────────────────────────────────────────────────
print(f"\n{'=' * 40}")
print(f"ALL {len(results)} TESTS PASSED")
print(f"{'=' * 40}")

csv_path = "data/results_orchestrator_smoke.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["module", "test", "result", "detail"])
    for module, test, detail in results:
        w.writerow([module, test, "PASS", detail])
print(f"Results written to {csv_path}")
