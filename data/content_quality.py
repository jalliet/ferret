"""
Content quality assessment for URL fetching experiments.

Classifies fetched content as one of:
  - success:        Real, substantive content retrieved
  - partial:        Some content but thin (may be a preview, stub, or truncated)
  - blocked:        Block page, login wall, or anti-bot challenge
  - paywall:        Paywall gate (subscription required)
  - empty:          No meaningful text returned
  - error:          Request failed entirely (timeout, connection error, etc.)
"""

import re

# Known block page signatures — matched against lowercased text
# Each tuple is (pattern, min_occurrences_to_trigger)
BLOCK_SIGNATURES = [
    # Cloudflare
    (r"checking your browser", 1),
    (r"just a moment.*cloudflare", 1),
    (r"attention required.*cloudflare", 1),
    (r"ray id:", 1),
    # Generic bot detection
    (r"please enable javascript.*to continue", 1),
    (r"please verify you are (a )?human", 1),
    (r"access denied.*you don.?t have permission", 1),
    (r"403 forbidden", 1),
    (r"automated access.*detected", 1),
    # Login walls
    (r"sign in to (continue|view|access)", 1),
    (r"log in to (continue|view|access)", 1),
    (r"create (a free )?account to (continue|view|access|read)", 1),
    (r"join.*to (unlock|read|view|see)", 1),
]

PAYWALL_SIGNATURES = [
    (r"subscribe to (continue|read|access|unlock)", 1),
    (r"subscription required", 1),
    (r"this (article|content) is for (paid )?subscribers", 1),
    (r"already a subscriber\?", 1),
    (r"start your.*free trial", 1),
]


def assess_content(
    text: str,
    status_code: int | None = None,
    html_length: int | None = None,
) -> str:
    """
    Classify fetched content quality.

    Args:
        text: Extracted text content (boilerplate removed where possible).
        status_code: HTTP status code, if available.
        html_length: Length of raw HTML, for content-to-boilerplate ratio check.
    """
    # --- Hard failures from status code ---
    if status_code is not None:
        if status_code == 401:
            return "blocked"
        if status_code == 403:
            # 403 with substantial text could be a soft block with partial content
            # (e.g., Cloudflare showing cached content), but usually it's a block
            if not text or len(text) < 500:
                return "blocked"
            # Check if it's a block page vs actual content behind a 403
            if _matches_block_page(text):
                return "blocked"
            # Some sites return 403 but still serve content (e.g., rate limit with body)
            return "partial"
        if status_code == 429:
            return "blocked"
        if status_code >= 500:
            return "error"

    # --- No content ---
    if not text or len(text.strip()) < 50:
        return "empty"

    lower = text.lower()

    # --- Block page detection ---
    if _matches_block_page(text):
        return "blocked"

    # --- Paywall detection ---
    if _matches_paywall(text):
        # Paywalled pages often show a preview — check if there's real content too
        sentences = _count_sentences(text)
        if sentences >= 5:
            return "partial"  # Some content visible before the wall
        return "paywall"

    # --- JS shell detection ---
    # If raw HTML is huge but extracted text is tiny, it's likely a JS-rendered shell
    if html_length and html_length > 10000 and len(text) < 200:
        return "empty"

    # --- Content quality by substance ---
    sentences = _count_sentences(text)
    words = len(text.split())

    if words > 500 and sentences >= 5:
        return "success"
    if words > 100 and sentences >= 2:
        return "partial"
    if words > 50:
        return "partial"

    return "empty"


def _matches_block_page(text: str) -> bool:
    """Check if text matches known block page patterns."""
    lower = text.lower()
    for pattern, min_count in BLOCK_SIGNATURES:
        matches = len(re.findall(pattern, lower))
        if matches >= min_count:
            return True
    return False


def _matches_paywall(text: str) -> bool:
    """Check if text matches known paywall patterns."""
    lower = text.lower()
    for pattern, min_count in PAYWALL_SIGNATURES:
        matches = len(re.findall(pattern, lower))
        if matches >= min_count:
            return True
    return False


def _count_sentences(text: str) -> int:
    """Rough sentence count — looks for period/question/exclamation followed by space or end."""
    return len(re.findall(r'[.!?]\s+[A-Z]', text)) + (1 if text.strip() else 0)
