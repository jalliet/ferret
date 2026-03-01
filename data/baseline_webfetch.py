"""
Baseline test: HTTP GET on 50 URLs using httpx.
Approximates what Claude's web_fetch tool does (plain HTTP requests).
Logs status code, response time, content length, and content quality per URL.
"""

import asyncio
import csv
import time
from pathlib import Path

import httpx

INPUT_CSV = Path(__file__).parent / "test-urls.csv"
OUTPUT_CSV = Path(__file__).parent / "results_baseline.csv"

# Mimic a realistic browser User-Agent (Chrome on macOS)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

TIMEOUT = 30.0
MAX_CONCURRENT = 5


def assess_content(text: str, url: str) -> str:
    """Quick heuristic: did we get real content or a block/error page?"""
    if not text or len(text) < 100:
        return "empty"
    lower = text.lower()
    # Common block indicators
    block_signals = [
        "access denied",
        "403 forbidden",
        "please enable javascript",
        "checking your browser",
        "just a moment",
        "attention required",
        "cloudflare",
        "captcha",
        "robot",
        "blocked",
        "rate limit",
        "too many requests",
        "sign in to",
        "log in to continue",
        "create an account",
    ]
    block_count = sum(1 for s in block_signals if s in lower)
    if block_count >= 2:
        return "blocked"
    if len(text) < 500 and block_count >= 1:
        return "likely_blocked"
    if len(text) > 2000:
        return "content_retrieved"
    return "partial"


async def fetch_url(client: httpx.AsyncClient, url_row: dict, semaphore: asyncio.Semaphore) -> dict:
    url = url_row["url"]
    result = {
        "id": url_row["id"],
        "url": url,
        "domain": url_row["domain"],
        "category": url_row["category"],
        "auth_required": url_row["auth_required"],
        "status_code": None,
        "response_time_ms": None,
        "content_length": 0,
        "content_quality": "error",
        "error": None,
    }

    async with semaphore:
        start = time.monotonic()
        try:
            resp = await client.get(url, follow_redirects=True)
            elapsed = (time.monotonic() - start) * 1000
            result["status_code"] = resp.status_code
            result["response_time_ms"] = round(elapsed)
            text = resp.text
            result["content_length"] = len(text)
            result["content_quality"] = assess_content(text, url)
        except httpx.TimeoutException:
            result["response_time_ms"] = round((time.monotonic() - start) * 1000)
            result["error"] = "timeout"
            result["content_quality"] = "timeout"
        except Exception as e:
            result["response_time_ms"] = round((time.monotonic() - start) * 1000)
            result["error"] = str(e)[:200]
            result["content_quality"] = "error"

    return result


async def main():
    # Read test URLs
    with open(INPUT_CSV) as f:
        reader = csv.DictReader(f)
        urls = list(reader)

    print(f"Testing {len(urls)} URLs with plain HTTP GET (httpx)...\n")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT) as client:
        tasks = [fetch_url(client, row, semaphore) for row in urls]
        results = await asyncio.gather(*tasks)

    # Sort by ID
    results.sort(key=lambda r: int(r["id"]))

    # Write results
    fieldnames = [
        "id", "url", "domain", "category", "auth_required",
        "status_code", "response_time_ms", "content_length",
        "content_quality", "error",
    ]
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Print summary
    print(f"{'ID':>3} {'Status':>6} {'Time':>7} {'Length':>8} {'Quality':<20} {'Domain'}")
    print("-" * 80)
    for r in results:
        status = r["status_code"] or "ERR"
        time_ms = f"{r['response_time_ms']}ms" if r["response_time_ms"] else "N/A"
        length = r["content_length"]
        print(f"{r['id']:>3} {status:>6} {time_ms:>7} {length:>8} {r['content_quality']:<20} {r['domain']}")

    # Category summary
    print("\n--- Summary by Category ---")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "success": 0}
        categories[cat]["total"] += 1
        if r["content_quality"] in ("content_retrieved", "partial"):
            categories[cat]["success"] += 1

    for cat, counts in sorted(categories.items()):
        rate = counts["success"] / counts["total"] * 100
        print(f"  {cat:<25} {counts['success']}/{counts['total']} ({rate:.0f}%)")

    total_success = sum(c["success"] for c in categories.values())
    total = sum(c["total"] for c in categories.values())
    print(f"\n  TOTAL: {total_success}/{total} ({total_success/total*100:.0f}%)")
    print(f"\nResults saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    asyncio.run(main())
