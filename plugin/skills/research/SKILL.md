---
name: research
description: Use when the user asks to research a topic, find information across the web, compare sources, or gather evidence. Triggers on phrases like "research", "look up", "find out about", "what do sources say about", "gather information on".
---

# Web Research Methodology

You have access to a search orchestrator that searches DuckDuckGo, fetches pages in parallel, and returns the most relevant content chunks scored by a cross-encoder model.

## Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| `search_and_scrape` | Search + fetch + score in one call | Starting a new research query |
| `get_more` | Paginate cached results (instant) | Need more depth on same query |
| `stealth_fetch` | Fetch a single URL with stealth browser | A specific URL failed due to bot detection |

## Research Process

### 1. Search broadly first

Call `search_and_scrape` with a clear, specific query. The tool fetches ~10 sources and returns the top 5 most relevant chunks.

- Use natural language queries, not keyword soup
- One focused question per search — don't combine topics
- If the first query misses an angle, search again with a different framing

### 2. Go deeper with get_more

The first `search_and_scrape` caches all scored chunks (typically 50-150). Use `get_more` to paginate through them at zero cost:

```
get_more(query="same query", offset=5, limit=5)   # chunks 6-10
get_more(query="same query", offset=10, limit=5)  # chunks 11-15
```

Do this when the top 5 chunks don't fully answer the question or you need additional perspectives.

### 3. Retry failed URLs with stealth_fetch

If `search_and_scrape` reports failed URLs that look important, retry them individually:

```
stealth_fetch(url="https://blocked-site.com/article")
```

This uses a stealth browser (Camoufox) that bypasses most bot detection. It's slower (3-10s) so only use it for high-value sources.

### 4. Synthesize across sources

After gathering enough chunks:
- Cross-reference claims across multiple sources
- Note conflicting information and which sources disagree
- Cite specific sources with URLs when presenting findings
- Flag when information is from a single source only

## Query Strategy

**Good queries:**
- "how does transformer attention mechanism work in large language models"
- "comparison of web scraping libraries python 2025"
- "CRISPR gene editing recent breakthroughs and ethical concerns"

**Bad queries:**
- "transformers" (too vague)
- "python scraping best 2025 comparison review" (keyword stuffing)
- "tell me everything about AI" (too broad)

## When Sources Disagree

1. Note the disagreement explicitly
2. Check which sources are more authoritative (academic papers > blog posts)
3. Look for the most recent information when facts may have changed
4. Present both sides and let the user decide

## Limitations

- DuckDuckGo's `site:` operator can trigger bot detection — avoid it
- Some paywalled sites return only previews or empty content
- Results are only as current as what DuckDuckGo has indexed
- Cross-encoder scores are relative within a query, not comparable across queries
