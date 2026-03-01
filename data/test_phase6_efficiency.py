"""Phase 6: context efficiency test — raw text vs cross-encoder filtered.

Measures token reduction ratio when returning only top-k scored chunks
vs dumping all fetched content. Target: 5x+ reduction.

Run from project root: PYTHONPATH=. .venv/bin/python data/test_phase6_efficiency.py
"""

import csv
import time

from search_orchestrator.search import search_ddg
from search_orchestrator.fetch import fetch_parallel
from search_orchestrator.chunker import chunk_text
from search_orchestrator.scorer import score_chunks

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

TOP_K = 5  # what Claude would see


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~0.75 tokens per word."""
    return int(len(text.split()) * 0.75)


all_results = []

for i, query in enumerate(QUERIES, 1):
    print(f"\n[{i}/{len(QUERIES)}] {query}")

    # Search + fetch
    search_results = search_ddg(query, num_results=10)
    urls = [r["url"] for r in search_results]
    fetch_results = fetch_parallel(urls)
    successful = [r for r in fetch_results if r["error"] is None]

    # Raw text: everything fetched (what you'd get dumping pages into context)
    raw_texts = [r["text"] for r in successful]
    raw_tokens = sum(estimate_tokens(t) for t in raw_texts)

    # Chunk all text
    all_chunks = []
    for result in successful:
        chunks = chunk_text(result["text"])
        for j, text in enumerate(chunks):
            all_chunks.append({"text": text, "source_url": result["url"], "chunk_index": j})

    chunked_tokens = sum(estimate_tokens(c["text"]) for c in all_chunks)

    # Score and take top-k
    t0 = time.time()
    scored = score_chunks(query, all_chunks)
    score_time = time.time() - t0

    top_k_chunks = scored[:TOP_K]
    filtered_tokens = sum(estimate_tokens(c["text"]) for c in top_k_chunks)

    # Metrics
    reduction = raw_tokens / filtered_tokens if filtered_tokens > 0 else 0
    top_score = top_k_chunks[0]["score"] if top_k_chunks else 0
    bottom_score = top_k_chunks[-1]["score"] if top_k_chunks else 0

    verdict = "PASS" if reduction >= 5 else "MARGINAL" if reduction >= 3 else "FAIL"

    print(f"  {verdict} — raw={raw_tokens:,} tok, filtered={filtered_tokens:,} tok, reduction={reduction:.1f}x")
    print(f"  {len(successful)} sources, {len(all_chunks)} chunks, score range=[{bottom_score:.2f}, {top_score:.2f}], scoring={score_time:.1f}s")

    all_results.append({
        "query": query,
        "sources": len(successful),
        "total_chunks": len(all_chunks),
        "raw_tokens": raw_tokens,
        "chunked_tokens": chunked_tokens,
        "filtered_tokens": filtered_tokens,
        "reduction_ratio": round(reduction, 1),
        "top_score": round(top_score, 4),
        "bottom_score": round(bottom_score, 4),
        "score_time_s": round(score_time, 1),
        "verdict": verdict,
    })

# Summary
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")

avg_raw = sum(r["raw_tokens"] for r in all_results) / len(all_results)
avg_filtered = sum(r["filtered_tokens"] for r in all_results) / len(all_results)
avg_reduction = sum(r["reduction_ratio"] for r in all_results) / len(all_results)
avg_score_time = sum(r["score_time_s"] for r in all_results) / len(all_results)
pass_count = sum(1 for r in all_results if r["verdict"] == "PASS")

print(f"  Avg raw tokens/query: {avg_raw:,.0f}")
print(f"  Avg filtered tokens/query (top {TOP_K}): {avg_filtered:,.0f}")
print(f"  Avg reduction: {avg_reduction:.1f}x")
print(f"  Avg scoring time: {avg_score_time:.1f}s")
print(f"  PASS (>=5x reduction): {pass_count}/{len(QUERIES)}")

csv_path = "data/results_phase6_efficiency.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(all_results[0].keys()))
    w.writeheader()
    w.writerows(all_results)
print(f"\nResults written to {csv_path}")
