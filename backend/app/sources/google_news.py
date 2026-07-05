"""Google News RSS — per-ticker and per-narrative keyword feeds.

Free, no auth, covers US/HK/global equities and Chinese-language queries.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from urllib.parse import quote_plus

import feedparser
import httpx

from .. import config

log = logging.getLogger(__name__)

_FEED_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_time(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            return datetime.utcfromtimestamp(time.mktime(parsed))
    return datetime.utcnow()


def fetch(query: str, limit: int = 25) -> list[dict]:
    """Fetch news items for a query string like 'NVIDIA stock'."""
    url = _FEED_URL.format(query=quote_plus(query))
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": config.HTTP_USER_AGENT},
            timeout=20,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("google_news fetch failed for %r: %s", query, exc)
        return []

    feed = feedparser.parse(resp.text)
    items: list[dict] = []
    for entry in feed.entries[:limit]:
        title = _strip_html(getattr(entry, "title", ""))
        if not title:
            continue
        # Google News titles end with " - Publisher"
        publisher = ""
        if " - " in title:
            title, publisher = title.rsplit(" - ", 1)
        source_obj = getattr(entry, "source", None)
        if source_obj is not None and getattr(source_obj, "title", ""):
            publisher = source_obj.title
        items.append(
            {
                "source": "google_news",
                "title": title.strip(),
                "url": getattr(entry, "link", ""),
                "publisher": publisher.strip(),
                "summary": _strip_html(getattr(entry, "summary", ""))[:500],
                "published_at": _parse_time(entry),
            }
        )
    return items
