---
description: Research a topic across the web using search, fetch, and relevance scoring
argument-hint: "<topic>"
---

Use the Web Research skill to investigate the following topic:

**$ARGUMENTS**

Follow these steps:

1. Call `search_and_scrape` with a well-formed query based on the topic. If the topic is broad, break it into 2-3 focused queries.
2. Review the top chunks returned. If they don't fully cover the topic, use `get_more` to paginate through additional cached results.
3. If any important-looking URLs failed, retry them with `stealth_fetch`.
4. Synthesize findings into a clear summary with source citations (URLs).
5. Note any conflicting information or gaps in coverage.
