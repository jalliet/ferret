from __future__ import annotations

import pytest

from search_orchestrator.fetch import extract_text


# ── Boilerplate tag stripping ──────────────────────────────────────────────

@pytest.mark.parametrize("tag", ["script", "style", "nav", "footer", "header"])
def test_extract_text_strips_boilerplate_tag(tag):
    html = f"<{tag}>unwanted content</{tag}><p>keep this</p>"
    result = extract_text(html)
    assert "unwanted content" not in result
    assert "keep this" in result


# ── Content preservation ───────────────────────────────────────────────────

def test_extract_text_preserves_main_article_content(sample_html):
    result = extract_text(sample_html)
    assert "Understanding Large Language Models" in result
    assert "neural networks trained on vast amounts of text data" in result
    assert "Transformer architecture" in result


def test_extract_text_strips_nav_from_sample(sample_html):
    result = extract_text(sample_html)
    assert "Home" not in result
    assert "About" not in result
    assert "Contact" not in result


def test_extract_text_strips_footer_from_sample(sample_html):
    result = extract_text(sample_html)
    assert "All rights reserved" not in result
    assert "Privacy" not in result
    assert "Terms" not in result


# ── Edge cases ─────────────────────────────────────────────────────────────

def test_extract_text_empty_html_returns_empty_string():
    assert extract_text("") == ""


def test_extract_text_minimal_paragraph():
    result = extract_text("<p>hello world</p>")
    assert result == "hello world"


def test_extract_text_only_boilerplate_returns_empty():
    html = "<script>var x=1;</script><style>body{}</style><nav>menu</nav>"
    result = extract_text(html)
    assert result == ""


def test_extract_text_nested_tags_stripped():
    html = "<nav><ul><li><a href='/'>Deep nested nav</a></li></ul></nav><p>content</p>"
    result = extract_text(html)
    assert "Deep nested nav" not in result
    assert "content" in result


def test_extract_text_multiple_paragraphs_joined_with_newlines():
    html = "<p>first paragraph</p><p>second paragraph</p>"
    result = extract_text(html)
    assert "first paragraph" in result
    assert "second paragraph" in result
    lines = result.split("\n")
    assert len(lines) == 2


def test_extract_text_malformed_html_does_not_raise():
    html = "<p>unclosed paragraph<div>mixed <b>nesting"
    result = extract_text(html)
    assert isinstance(result, str)
