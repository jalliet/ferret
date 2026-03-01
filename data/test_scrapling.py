"""
Phase 2: Test Scrapling's fetchers on the same 50 URLs.
Uses tiered escalation: Fetcher (HTTP) first, then StealthyFetcher for failures.
Logs status, fetcher tier used, response time, content length, and quality per URL.
"""

import csv
import logging
import time
from pathlib import Path

from scrapling import Fetcher, StealthyFetcher

from content_quality import assess_content

# Suppress Scrapling's verbose INFO logging
logging.getLogger().setLevel(logging.WARNING)

INPUT_CSV = Path(__file__).parent / "test-urls.csv"
OUTPUT_CSV = Path(__file__).parent / "results_scrapling.csv"

TIMEOUT = 30


def try_fetcher(url: str) -> dict:
    """Try Scrapling's HTTP Fetcher (fast tier)."""
    start = time.monotonic()
    try:
        resp = Fetcher.get(url, timeout=TIMEOUT)
        elapsed = (time.monotonic() - start) * 1000
        text = resp.get_all_text()
        html = resp.html_content or ""
        return {
            "status_code": resp.status,
            "response_time_ms": round(elapsed),
            "content_length": len(text),
            "content_quality": assess_content(text, status_code=resp.status, html_length=len(html)),
            "fetcher_tier": "http",
            "error": None,
        }
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return {
            "status_code": None,
            "response_time_ms": round(elapsed),
            "content_length": 0,
            "content_quality": "error",
            "fetcher_tier": "http",
            "error": str(e)[:200],
        }


def try_stealthy(url: str) -> dict:
    """Try Scrapling's StealthyFetcher (Camoufox, full anti-bot bypass)."""
    start = time.monotonic()
    try:
        resp = StealthyFetcher.fetch(url, headless=True, timeout=TIMEOUT * 1000)
        elapsed = (time.monotonic() - start) * 1000
        text = resp.get_all_text()
        html = resp.html_content or ""
        return {
            "status_code": resp.status,
            "response_time_ms": round(elapsed),
            "content_length": len(text),
            "content_quality": assess_content(text, status_code=resp.status, html_length=len(html)),
            "fetcher_tier": "stealth",
            "error": None,
        }
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return {
            "status_code": None,
            "response_time_ms": round(elapsed),
            "content_length": 0,
            "content_quality": "error",
            "fetcher_tier": "stealth",
            "error": str(e)[:200],
        }


def is_failure(quality: str) -> bool:
    """Check if a content quality classification counts as a failure."""
    return quality in ("empty", "blocked", "paywall", "error")


def test_url(url_row: dict) -> dict:
    """Test a URL with tiered escalation: HTTP first, stealth if HTTP fails."""
    url = url_row["url"]
    url_id = url_row["id"]
    domain = url_row["domain"]

    print(f"  [{url_id:>2}/50] {domain:<25}", end="", flush=True)

    # Tier 1: HTTP Fetcher
    result = try_fetcher(url)

    # Escalate to stealth if HTTP tier failed
    if is_failure(result["content_quality"]):
        http_result = result.copy()
        print(f" HTTP={result['content_quality']:<16}", end="", flush=True)

        # Tier 3: StealthyFetcher
        result = try_stealthy(url)
        result["http_status"] = http_result["status_code"]
        result["http_quality"] = http_result["content_quality"]
        result["http_time_ms"] = http_result["response_time_ms"]
        print(f" -> Stealth={result['content_quality']:<16} ({result['response_time_ms']}ms)")
    else:
        result["http_status"] = result["status_code"]
        result["http_quality"] = result["content_quality"]
        result["http_time_ms"] = result["response_time_ms"]
        print(f" HTTP={result['content_quality']:<16} ({result['response_time_ms']}ms)")

    # Merge URL metadata
    result["id"] = url_id
    result["url"] = url
    result["domain"] = domain
    result["category"] = url_row["category"]
    result["auth_required"] = url_row["auth_required"]

    return result


def main():
    with open(INPUT_CSV) as f:
        reader = csv.DictReader(f)
        urls = list(reader)

    print(f"Testing {len(urls)} URLs with Scrapling (HTTP -> Stealth escalation)...\n")

    results = []
    for row in urls:
        result = test_url(row)
        results.append(result)

    # Sort by ID
    results.sort(key=lambda r: int(r["id"]))

    # Write CSV
    fieldnames = [
        "id", "url", "domain", "category", "auth_required",
        "fetcher_tier", "status_code", "response_time_ms", "content_length",
        "content_quality", "http_status", "http_quality", "http_time_ms", "error",
    ]
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    # Print summary
    print(f"\n{'ID':>3} {'Tier':<8} {'Status':>6} {'Time':>7} {'Length':>8} {'Quality':<20} {'Domain'}")
    print("-" * 90)
    for r in results:
        status = r["status_code"] or "ERR"
        time_ms = f"{r['response_time_ms']}ms" if r["response_time_ms"] else "N/A"
        print(f"{r['id']:>3} {r['fetcher_tier']:<8} {status:>6} {time_ms:>7} {r['content_length']:>8} {r['content_quality']:<20} {r['domain']}")

    # Category summary
    print("\n--- Summary by Category ---")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "success": 0}
        categories[cat]["total"] += 1
        if not is_failure(r["content_quality"]):
            categories[cat]["success"] += 1

    for cat, counts in sorted(categories.items()):
        rate = counts["success"] / counts["total"] * 100
        print(f"  {cat:<25} {counts['success']}/{counts['total']} ({rate:.0f}%)")

    total_success = sum(c["success"] for c in categories.values())
    total = sum(c["total"] for c in categories.values())
    print(f"\n  TOTAL: {total_success}/{total} ({total_success/total*100:.0f}%)")

    # Comparison with baseline
    baseline_file = Path(__file__).parent / "results_baseline.csv"
    if baseline_file.exists():
        print("\n--- Comparison vs Baseline (httpx) ---")
        with open(baseline_file) as f:
            baseline = {row["id"]: row for row in csv.DictReader(f)}
        improved = []
        regressed = []
        same = 0
        for r in results:
            b = baseline.get(r["id"], {})
            b_ok = not is_failure(b.get("content_quality", "error"))
            s_ok = not is_failure(r["content_quality"])
            if s_ok and not b_ok:
                improved.append(r)
            elif not s_ok and b_ok:
                regressed.append(r)
            else:
                same += 1
        print(f"  Improved:  {len(improved)} URLs now accessible")
        for r in improved:
            b = baseline[r["id"]]
            print(f"    [{r['id']:>2}] {r['domain']:<25} {b['content_quality']} -> {r['content_quality']} (tier: {r['fetcher_tier']})")
        print(f"  Regressed: {len(regressed)} URLs now worse")
        for r in regressed:
            b = baseline[r["id"]]
            print(f"    [{r['id']:>2}] {r['domain']:<25} {b['content_quality']} -> {r['content_quality']} (tier: {r['fetcher_tier']})")
        print(f"  Same:      {same} URLs unchanged")

        # Go/no-go gate
        print("\n--- GO/NO-GO GATE ---")
        baseline_failed_noauth = []
        for id in sorted(baseline, key=int):
            b = baseline[id]
            if is_failure(b["content_quality"]) and b["auth_required"] != "yes":
                baseline_failed_noauth.append(id)

        scrapling_fixed = 0
        for id in baseline_failed_noauth:
            s_row = next((r for r in results if r["id"] == id), None)
            if s_row and not is_failure(s_row["content_quality"]):
                scrapling_fixed += 1

        total_bf = len(baseline_failed_noauth)
        rate = scrapling_fixed / total_bf * 100 if total_bf else 0
        print(f"  Baseline failures (non-auth): {total_bf}")
        print(f"  Scrapling recovered:          {scrapling_fixed}/{total_bf} ({rate:.0f}%)")
        print(f"  Target: >85%")
        if rate >= 85:
            print("  VERDICT: GO")
        else:
            print(f"  VERDICT: BELOW TARGET (need {round(total_bf * 0.85)} recoveries, got {scrapling_fixed})")

    print(f"\nResults saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()