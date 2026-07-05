"""Yahoo Finance — quotes, company names, earnings dates.

Yahoo blocks Python HTTP clients via TLS fingerprinting; we go through the
system curl (see curlhttp.py). quoteSummary needs a cookie+crumb dance which
we do lazily; earnings date is optional context and degrades gracefully.
"""
from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import curlhttp

log = logging.getLogger(__name__)

_crumb: str | None = None
_cookie_jar = str(Path(tempfile.gettempdir()) / "mosaic-yahoo-cookies.txt")


def get_quote(symbol: str) -> dict | None:
    """Return {price, prev_close, change_pct, currency, name, exchange} or None.

    Rotates query1/query2 hosts; Yahoo rate-limits bursts per host.
    """
    data = None
    for host in ("query1", "query2"):
        data = curlhttp.get_json(
            f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": "1d", "range": "10d"},
        )
        if isinstance(data, dict):
            break
    try:
        result = data["chart"]["result"][0]
        meta = result["meta"]
    except (TypeError, KeyError, IndexError):
        log.warning("yahoo quote failed for %s", symbol)
        return None

    price = meta.get("regularMarketPrice")
    # True previous close = the close before the latest bar (chartPreviousClose
    # is the close before the *range window*, which is days old).
    prev = meta.get("regularMarketPreviousClose")
    if not prev:
        try:
            closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
            if price is not None and closes and abs(closes[-1] - price) < 1e-6:
                closes = closes[:-1]  # last bar is the live/current session
            prev = closes[-1] if closes else None
        except (KeyError, IndexError, TypeError):
            prev = None
    change_pct = None
    if price is not None and prev:
        change_pct = (price / prev - 1) * 100
    return {
        "price": price,
        "prev_close": prev,
        "change_pct": change_pct,
        "currency": meta.get("currency") or "USD",
        "name": meta.get("longName") or meta.get("shortName") or "",
        "exchange": meta.get("fullExchangeName") or "",
    }


def _ensure_crumb() -> str | None:
    global _crumb
    if _crumb:
        return _crumb
    curlhttp.get("https://fc.yahoo.com", timeout=10, cookie_jar=_cookie_jar)
    body = curlhttp.get("https://query1.finance.yahoo.com/v1/test/getcrumb",
                        timeout=10, cookie_jar=_cookie_jar)
    if body and "<" not in body and len(body.strip()) < 30:
        _crumb = body.strip()
    return _crumb


def get_earnings_date(symbol: str) -> str | None:
    """Next earnings date as YYYY-MM-DD, or None."""
    params: dict = {"modules": "calendarEvents"}
    crumb = _ensure_crumb()
    if crumb:
        params["crumb"] = crumb
    data = curlhttp.get_json(
        f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}",
        params=params, cookie_jar=_cookie_jar,
    )
    try:
        earnings = data["quoteSummary"]["result"][0]["calendarEvents"]["earnings"]
        dates = earnings.get("earningsDate") or []
        if dates:
            ts = dates[0].get("raw")
            if ts:
                return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, KeyError, IndexError):
        log.info("yahoo earnings date unavailable for %s", symbol)
    return None
