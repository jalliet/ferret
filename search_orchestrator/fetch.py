import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

from scrapling import Fetcher, StealthyFetcher
from bs4 import BeautifulSoup

_fetcher = Fetcher()
_stealth_fetcher = StealthyFetcher()
_ALLOWED_SCHEMES = frozenset({"http", "https"})
_BLOCKED_HOSTS = frozenset({"169.254.169.254", "metadata.google.internal", "localhost"})
_MIN_TEXT_LEN = 50


def _validate_url(url: str) -> None:
    """Reject non-HTTP schemes, private IPs, and cloud metadata endpoints."""
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"Blocked scheme: {parsed.scheme}")
    hostname = parsed.hostname or ""
    if hostname in _BLOCKED_HOSTS:
        raise ValueError(f"Blocked metadata host: {hostname}")
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError(f"Blocked private/internal IP: {hostname}")
    except ValueError as e:
        if "Blocked" in str(e):
            raise


def _extract_text(html: str) -> str:
    """Extract clean text from HTML, stripping boilerplate tags."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _do_fetch(url: str, fetcher) -> dict:
    """Validate URL, fetch with given fetcher, extract text."""
    try:
        _validate_url(url)
        resp = fetcher.get(url)
        if resp.status >= 400:
            return {"url": url, "status": resp.status, "text": "", "error": f"HTTP {resp.status}"}
        text = _extract_text(resp.html_content)
        if len(text) < _MIN_TEXT_LEN:
            return {"url": url, "status": resp.status, "text": "", "error": "empty_content"}
        return {"url": url, "status": resp.status, "text": text, "error": None}
    except Exception as e:
        return {"url": url, "status": 0, "text": "", "error": str(e)}


def fetch_parallel(urls: list[str], max_workers: int = 5) -> list[dict]:
    """Fetch multiple URLs in parallel. Returns list of result dicts."""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_do_fetch, url, _fetcher): url for url in urls}
        for future in as_completed(futures):
            results.append(future.result())
    url_order = {url: i for i, url in enumerate(urls)}
    results.sort(key=lambda r: url_order.get(r["url"], 999))
    return results


def stealth_fetch_one(url: str) -> dict:
    """Fetch a single URL with StealthyFetcher (Camoufox)."""
    return _do_fetch(url, _stealth_fetcher)
