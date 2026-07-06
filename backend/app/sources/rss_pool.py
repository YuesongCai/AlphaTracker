"""Curated official RSS pool — the MacroRadar lesson applied to equities:

read the wire directly (WSJ/CNBC/MarketWatch/SA/NYT/FT/Fed/TechCrunch/Verge),
don't search-query an aggregator. Every feed verified live before inclusion.
Lanes: markets | macro | tech. Per-feed fault tolerance; one dead feed never
blocks the pool.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime

import feedparser

from . import curlhttp

log = logging.getLogger(__name__)

# name, url, lane  — keep names short; they show as publisher in the UI.
FEEDS: list[dict] = [
    {"name": "WSJ Markets", "lane": "markets",
     "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"},
    {"name": "WSJ Business", "lane": "markets",
     "url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"},
    {"name": "CNBC Top", "lane": "markets",
     "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"},
    {"name": "CNBC Markets", "lane": "markets",
     "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839069"},
    {"name": "MarketWatch", "lane": "markets",
     "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"name": "SeekingAlpha 快讯", "lane": "markets",
     "url": "https://seekingalpha.com/market_currents.xml"},
    {"name": "NYT Business", "lane": "markets",
     "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"},
    {"name": "NYT Economy", "lane": "macro",
     "url": "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml"},
    {"name": "FT", "lane": "macro",
     "url": "https://www.ft.com/rss/home"},
    {"name": "美联储", "lane": "macro",
     "url": "https://www.federalreserve.gov/feeds/press_all.xml"},
    {"name": "CNBC Tech", "lane": "tech",
     "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910"},
    {"name": "TechCrunch", "lane": "tech",
     "url": "https://techcrunch.com/feed/"},
    {"name": "The Verge", "lane": "tech",
     "url": "https://www.theverge.com/rss/index.xml"},
]

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_time(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            return datetime.utcfromtimestamp(time.mktime(parsed))
    return datetime.utcnow()


def fetch_feed(feed: dict, limit: int = 15) -> list[dict]:
    body = curlhttp.get(feed["url"], timeout=20, ua=_UA)
    if not body:
        return []
    parsed = feedparser.parse(body)
    out = []
    for entry in parsed.entries[:limit]:
        title = _strip_html(getattr(entry, "title", ""))
        link = getattr(entry, "link", "")
        if not title or not link:
            continue
        out.append({
            "source": "rss",
            "lane": feed["lane"],
            "title": title[:300],
            "url": link,
            "publisher": feed["name"],
            "summary": _strip_html(getattr(entry, "summary", ""))[:500],
            "published_at": _parse_time(entry),
        })
    return out


def fetch_all(per_feed: int = 15) -> list[dict]:
    """Fetch the whole pool with per-feed fault tolerance."""
    items: list[dict] = []
    for feed in FEEDS:
        try:
            got = fetch_feed(feed, per_feed)
            items.extend(got)
        except Exception as exc:  # noqa: BLE001
            log.warning("rss feed %s failed: %s", feed["name"], exc)
        time.sleep(0.3)  # be polite across hosts
    return items
