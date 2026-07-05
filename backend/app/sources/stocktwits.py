"""StockTwits — retail sentiment snapshot per US symbol (via curl, see curlhttp).

Kept as a per-ticker gauge (bull ratio + watchers), not individual signals:
retail chatter is context, not news.
"""
from __future__ import annotations

import logging

from . import curlhttp

log = logging.getLogger(__name__)


def get_sentiment(symbol: str) -> dict | None:
    """Return {bull_ratio: 0..1|None, watchers: int, messages: int} or None."""
    data = curlhttp.get_json(
        f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
    )
    if not isinstance(data, dict) or "messages" not in data:
        return None

    messages = data.get("messages", [])
    bull = bear = 0
    for msg in messages:
        sentiment = ((msg.get("entities") or {}).get("sentiment") or {}).get("basic")
        if sentiment == "Bullish":
            bull += 1
        elif sentiment == "Bearish":
            bear += 1
    tagged = bull + bear
    return {
        "bull_ratio": (bull / tagged) if tagged else None,
        "watchers": (data.get("symbol") or {}).get("watchlist_count") or 0,
        "messages": len(messages),
    }
