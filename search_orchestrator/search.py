import re
from urllib.parse import urlencode, unquote
from scrapling import Fetcher

from search_orchestrator.types import SearchResult

_fetcher = Fetcher()
_DDG_REDIRECT_RE = re.compile(r"uddg=([^&]+)")


def search_ddg(query: str, num_results: int = 10) -> list[SearchResult]:
    """Search DuckDuckGo and return parsed results."""
    params = urlencode({"q": query})
    url = f"https://html.duckduckgo.com/html/?{params}"
    resp = _fetcher.get(url)

    if resp.status != 200:
        return []

    link_elements = resp.css(".result__a")
    snippet_elements = resp.css(".result__snippet")

    results: list[SearchResult] = []
    for i, link_el in enumerate(link_elements):
        if len(results) >= num_results:
            break
        title = link_el.text.strip() if link_el.text else ""
        href = link_el.attrib.get("href", "")

        match = _DDG_REDIRECT_RE.search(href)
        if match:
            href = unquote(match.group(1))

        snippet = ""
        if i < len(snippet_elements):
            snippet = snippet_elements[i].text.strip() if snippet_elements[i].text else ""

        if title and href:
            results.append(SearchResult(title=title, url=href, snippet=snippet))

    return results
