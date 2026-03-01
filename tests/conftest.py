from __future__ import annotations

import pytest

from search_orchestrator.cache import ChunkCache
from search_orchestrator.types import ScoredChunk


@pytest.fixture()
def sample_html() -> str:
    """Realistic HTML page with nav, content, and footer boilerplate."""
    return """<!DOCTYPE html>
<html lang="en">
<head><title>Test Article</title></head>
<body>
  <nav><a href="/">Home</a><a href="/about">About</a><a href="/contact">Contact</a></nav>
  <main>
    <h1>Understanding Large Language Models</h1>
    <p>Large language models (LLMs) are neural networks trained on vast amounts of text data.
       They learn statistical patterns in language and can generate coherent text, answer questions,
       and perform a wide range of natural language tasks.</p>
    <p>Recent advances in scaling laws have shown that model performance improves predictably
       with increases in model size, dataset size, and compute budget. This has led to a race
       among AI labs to train ever-larger models.</p>
    <h2>Architecture</h2>
    <p>Most modern LLMs use the Transformer architecture, which relies on self-attention
       mechanisms to process input sequences in parallel rather than sequentially.</p>
  </main>
  <footer><p>&copy; 2025 Test Site. All rights reserved.</p>
    <a href="/privacy">Privacy</a><a href="/terms">Terms</a></footer>
</body>
</html>"""


@pytest.fixture()
def make_scored_chunk():
    """Factory fixture: call with overrides to build a ScoredChunk."""

    def _make(
        text: str = "chunk text",
        source_url: str = "https://example.com",
        chunk_index: int = 0,
        score: float = 0.5,
    ) -> ScoredChunk:
        return ScoredChunk(
            text=text,
            source_url=source_url,
            chunk_index=chunk_index,
            score=score,
        )

    return _make


@pytest.fixture()
def scored_chunks(make_scored_chunk) -> list[ScoredChunk]:
    """Pre-built list of scored chunks sorted by descending score."""
    return [
        make_scored_chunk(text="highly relevant chunk", score=0.95, chunk_index=0),
        make_scored_chunk(text="moderately relevant chunk", score=0.60, chunk_index=1),
        make_scored_chunk(text="low relevance chunk", score=0.20, chunk_index=2),
    ]


@pytest.fixture()
def cache() -> ChunkCache:
    """Fresh ChunkCache instance."""
    return ChunkCache()
