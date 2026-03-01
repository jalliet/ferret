import re
from urllib.parse import urlencode, unquote
from scrapling import Fetcher

_fetcher = Fetcher()

def search_ddg(query: str, num_results: int = 10) -> list[dict]:
    """Search DuckDuckGo and return parsed results.
    Returns list of {"title": str, "url": str, "snippet": str}.
    """
    params = urlencode({"q": query})
    url = f"https://html.duckduckgo.com/html/?{params}"
    resp = _fetcher.get(url)

    if resp.status != 200:
        return []

    link_elements = resp.css(".result__a")
    snippet_elements = resp.css(".result__snippet")

    results = []
    for i, link_el in enumerate(link_elements):
        if len(results) >= num_results:
            break
        title = link_el.text.strip() if link_el.text else ""
        href = link_el.attrib.get("href", "")

        if "uddg=" in href:
            match = re.search(r"uddg=([^&]+)", href)
            if match:
                href = unquote(match.group(1))

        snippet = ""
        if i < len(snippet_elements):
            snippet = snippet_elements[i].text.strip() if snippet_elements[i].text else ""

        if title and href:
            results.append({"title": title, "url": href, "snippet": snippet})

    return results
