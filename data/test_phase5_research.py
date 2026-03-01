"""Phase 5: test search_and_scrape on 10 diverse research questions.

Measures: sources fetched, chunks cached, failures, top chunk relevance, latency.
Run from project root: PYTHONPATH=. .venv/bin/python data/test_phase5_research.py
"""

import csv
import time

from search_orchestrator.server import search_and_scrape

QUERIES = [
    "how does transformer attention mechanism work in large language models",
    "best practices for building MCP servers with Python",
    "comparison of web scraping libraries python 2025",
    "what causes hallucination in AI models and how to mitigate",
    "rust vs go for backend systems performance comparison",
    "how to implement RAG retrieval augmented generation",
    "climate change impact on global food supply 2024 2025",
    "CRISPR gene editing recent breakthroughs and ethical concerns",
    "zero knowledge proofs practical applications blockchain",
    "microplastics health effects latest research findings",
]

all_results = []

for i, query in enumerate(QUERIES, 1):
    print(f"\n{'='*60}")
    print(f"[{i}/{len(QUERIES)}] {query}")
    print(f"{'='*60}")

    t0 = time.time()
    result = search_and_scrape(query, num_results=10, top_k=5)
    dt = time.time() - t0

    n_chunks = len(result.get("chunks", []))
    n_cached = result.get("total_cached", 0)
    n_sources = result.get("sources_fetched", 0)
    n_failed = len(result.get("failed_urls", []))
    error = result.get("error", None)
    top_score = result["chunks"][0]["score"] if result.get("chunks") else 0
    top_url = result["chunks"][0]["source_url"][:80] if result.get("chunks") else ""

    verdict = "PASS" if n_chunks >= 3 and n_sources >= 5 else "MARGINAL" if n_chunks >= 1 else "FAIL"

    print(f"  {verdict} — {n_sources} sources, {n_cached} chunks cached, {n_failed} failed, top score={top_score:.4f} ({dt:.1f}s)")
    if error:
        print(f"  ERROR: {error}")
    if result.get("failed_urls"):
        for f in result["failed_urls"][:3]:
            print(f"    FAILED: {f['url'][:60]} — {f['error'][:40]}")

    all_results.append({
        "query": query,
        "sources_fetched": n_sources,
        "chunks_cached": n_cached,
        "chunks_returned": n_chunks,
        "failed_urls": n_failed,
        "top_score": top_score,
        "top_url": top_url,
        "latency_s": round(dt, 1),
        "verdict": verdict,
        "error": error or "",
    })

# Summary
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")

pass_count = sum(1 for r in all_results if r["verdict"] == "PASS")
marginal_count = sum(1 for r in all_results if r["verdict"] == "MARGINAL")
fail_count = sum(1 for r in all_results if r["verdict"] == "FAIL")
avg_sources = sum(r["sources_fetched"] for r in all_results) / len(all_results)
avg_cached = sum(r["chunks_cached"] for r in all_results) / len(all_results)
avg_latency = sum(r["latency_s"] for r in all_results) / len(all_results)
avg_top_score = sum(r["top_score"] for r in all_results) / len(all_results)

print(f"  PASS: {pass_count}/{len(QUERIES)}, MARGINAL: {marginal_count}, FAIL: {fail_count}")
print(f"  Avg sources/query: {avg_sources:.1f}")
print(f"  Avg chunks cached/query: {avg_cached:.1f}")
print(f"  Avg latency: {avg_latency:.1f}s")
print(f"  Avg top chunk score: {avg_top_score:.4f}")

# CSV
csv_path = "data/results_phase5_research.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(all_results[0].keys()))
    w.writeheader()
    w.writerows(all_results)
print(f"\nResults written to {csv_path}")
