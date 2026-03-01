from concurrent.futures import ThreadPoolExecutor, as_completed
from scrapling import Fetcher, StealthyFetcher
from bs4 import BeautifulSoup

_fetcher = Fetcher()

def _extract_text(html: str) -> str:
    """Extract clean text from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _fetch_one(url: str) -> dict:
    """Fetch a single URL with Scrapling Fetcher (HTTP-only)."""
    try:
        resp = _fetcher.get(url)
        if resp.status >= 400:
            return {"url": url, "status": resp.status, "text": "", "error": f"HTTP {resp.status}"}
        text = _extract_text(resp.html_content)
        if len(text) < 50:
            return {"url": url, "status": resp.status, "text": "", "error": "empty_content"}
        return {"url": url, "status": resp.status, "text": text, "error": None}
    except Exception as e:
        return {"url": url, "status": 0, "text": "", "error": str(e)}


def fetch_parallel(urls: list[str], max_workers: int = 5) -> list[dict]:
    """Fetch multiple URLs in parallel. Returns list of result dicts."""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_one, url): url for url in urls}
        for future in as_completed(futures):
            results.append(future.result())
    url_order = {url: i for i, url in enumerate(urls)}
    results.sort(key=lambda r: url_order.get(r["url"], 999))
    return results


def stealth_fetch_one(url: str) -> dict:
    """Fetch a single URL with StealthyFetcher (Camoufox)."""
    try:
        fetcher = StealthyFetcher()
        resp = fetcher.get(url)
        text = _extract_text(resp.html_content)
        if len(text) < 50:
            return {"url": url, "status": resp.status, "text": "", "error": "empty_content"}
        return {"url": url, "status": resp.status, "text": text, "error": None}
    except Exception as e:
        return {"url": url, "status": 0, "text": "", "error": str(e)}
