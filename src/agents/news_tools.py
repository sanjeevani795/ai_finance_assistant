"""Lightweight RSS headline fetch for the News Synthesizer agent (stdlib only)."""

from __future__ import annotations

import logging
import urllib.request
import xml.etree.ElementTree as ET
from urllib.error import URLError

logger = logging.getLogger(__name__)

_DEFAULT_FEEDS = (
    "https://feeds.reuters.com/reuters/businessNews",
)


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def fetch_rss_headlines(
    url: str,
    *,
    timeout: float = 12.0,
    max_items: int = 6,
) -> list[str]:
    """Return up to `max_items` titles from an RSS or Atom-ish XML feed."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ai-finance-assistant/1.0 (educational RSS reader)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — intentional URL fetch
            raw = resp.read()
    except (URLError, OSError) as exc:
        logger.warning("RSS fetch failed for %s: %s", url, exc)
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        logger.warning("RSS parse failed for %s", url)
        return []

    titles: list[str] = []
    for el in root.iter():
        if _strip_ns(el.tag).lower() == "title" and el.text:
            t = el.text.strip()
            if t and t not in titles and not t.lower().startswith("http"):
                titles.append(t)
            if len(titles) >= max_items + 2:
                break
    # First title is often channel title
    out = [t for t in titles if len(t) > 12][:max_items]
    return out


def news_context_block(
    *,
    rss_urls: list[str] | None = None,
    timeout: float = 12.0,
    max_items_per_feed: int = 4,
) -> str:
    """Fetch headlines from configured feeds; never raises."""
    urls = list(rss_urls or _DEFAULT_FEEDS)
    blocks: list[str] = []
    for url in urls[:4]:
        titles = fetch_rss_headlines(url, timeout=timeout, max_items=max_items_per_feed)
        if titles:
            blocks.append(f"Feed: {url}\n" + "\n".join(f"- {t}" for t in titles))
    if not blocks:
        return ""
    return "Recent headlines (RSS; may be delayed; verify at source):\n\n" + "\n\n".join(blocks)
