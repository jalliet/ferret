"""Phase 3 spike: validate DDG search result parsing with Scrapling."""

import asyncio
import csv
import re
from urllib.parse import urlencode, unquote
from scrapling import Fetcher

fetcher = Fetcher()

async def fetch_ddg(query: str) -> dict:
    """Fetch DuckDuckGo search results page and extract result links/titles/snippets."""
    params = urlencode({"q": query})
    url = f"https://html.duckduckgo.com/html/?{params}"

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"URL: {url}")

    resp = fetcher.get(url)
    status = resp.status
    html = resp.html_content
    print(f"Status: {status}, HTML length: {len(html)} chars")

    # Parse results using Scrapling's CSS selectors
    results = []

    # DDG HTML interface uses .result class for each result
    result_elements = resp.css(".result")
    print(f"Found {len(result_elements)} .result elements")

    if not result_elements:
        # Try alternative selectors
        result_elements = resp.css(".web-result")
        print(f"Found {len(result_elements)} .web-result elements")

    if not result_elements:
        # Dump a sample of the HTML for debugging
        print(f"\nFirst 3000 chars of HTML:\n{html[:3000]}")
        return {"query": query, "status": status, "results": [], "raw_len": len(html)}

    # Use response-level CSS selectors for links and snippets
    link_elements = resp.css(".result__a")
    snippet_elements = resp.css(".result__snippet")
    print(f"Found {len(link_elements)} .result__a links, {len(snippet_elements)} .result__snippet snippets")

    for i, link_el in enumerate(link_elements):
        title = link_el.text.strip() if link_el.text else ""
        href = link_el.attrib.get("href", "")

        # DDG wraps URLs in a redirect — extract the actual URL
        if "uddg=" in href:
            match = re.search(r"uddg=([^&]+)", href)
            if match:
                href = unquote(match.group(1))

        # Match snippet by index
        snippet = ""
        if i < len(snippet_elements):
            snippet = snippet_elements[i].text.strip() if snippet_elements[i].text else ""

        if title and href:
            results.append({"title": title, "url": href, "snippet": snippet})

    print(f"Parsed {len(results)} results with links")
    for i, r in enumerate(results[:5]):
        print(f"  [{i+1}] {r['title'][:60]}")
        print(f"      {r['url'][:80]}")
        print(f"      {r['snippet'][:80]}...")

    return {"query": query, "status": status, "results": results, "raw_len": len(html)}


async def main():
    queries = [
        "python web scraping best practices 2025",
        "how to use scrapling library",
        "claude code MCP server tutorial",
        "site:github.com scrapling",
        "ferret research orchestration",
    ]

    all_results = []
    for q in queries:
        result = await fetch_ddg(q)
        all_results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in all_results:
        n = len(r["results"])
        status = "PASS" if n >= 5 else "MARGINAL" if n >= 1 else "FAIL"
        print(f"[{status}] \"{r['query']}\" — {n} results, {r['raw_len']} chars HTML")

    total = sum(len(r["results"]) for r in all_results)
    passing = sum(1 for r in all_results if len(r["results"]) >= 5)
    print(f"\nTotal results extracted: {total}")
    print(f"Queries with 5+ results: {passing}/{len(queries)}")
    print(f"GO/NO-GO: {'GO' if passing >= 4 else 'NO-GO'} (need 4/5 queries with 5+ results)")

    # Write results to CSV
    csv_path = "data/results_ddg.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["query", "http_status", "html_chars", "result_rank", "title", "url", "snippet", "verdict"])
        for r in all_results:
            n = len(r["results"])
            verdict = "PASS" if n >= 5 else "MARGINAL" if n >= 1 else "FAIL"
            if r["results"]:
                for i, res in enumerate(r["results"], 1):
                    writer.writerow([r["query"], r["status"], r["raw_len"], i, res["title"], res["url"], res["snippet"], verdict])
            else:
                writer.writerow([r["query"], r["status"], r["raw_len"], 0, "", "", "", verdict])
    print(f"\nResults written to {csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
