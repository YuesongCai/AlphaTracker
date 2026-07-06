"""Hacker News front page — the earliest weathervane for tech narratives.

Keyless Algolia API; only high-score front-page stories make it in.
LLM triage downgrades the non-investment-relevant ones.
"""
from __future__ import annotations

import logging
from datetime import datetime

from . import curlhttp

log = logging.getLogger(__name__)

MIN_POINTS = 80


def fetch(limit: int = 20) -> list[dict]:
    data = curlhttp.get_json(
        "https://hn.algolia.com/api/v1/search",
        params={"tags": "front_page", "hitsPerPage": limit},
        timeout=15,
    )
    if not data:
        return []
    out = []
    for hit in data.get("hits", []):
        points = hit.get("points") or 0
        title = (hit.get("title") or "").strip()
        if points < MIN_POINTS or not title:
            continue
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        try:
            published = datetime.utcfromtimestamp(hit.get("created_at_i") or 0)
        except (ValueError, OSError):
            published = datetime.utcnow()
        out.append({
            "source": "hn",
            "lane": "tech",
            "title": f"{title}(HN {points}分)",
            "url": url,
            "publisher": "Hacker News",
            "summary": "",
            "published_at": published,
        })
    return out
