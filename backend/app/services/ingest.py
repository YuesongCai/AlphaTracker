"""Ingestion orchestration: sources -> dedup -> signals -> triage -> alerts."""
from __future__ import annotations

import hashlib
import logging
import re
import time
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..ai import triage
from ..models import Narrative, OpsLog, Signal, SignalNarrative, Ticker
from ..sources import (edgar, edgar_stream, google_news, hn, jin10, rss_pool,
                       stocktwits, yahoo)

log = logging.getLogger(__name__)


def _hash(url: str, title: str) -> str:
    """Dedup key. Google News URLs are unique per article; fall back to title."""
    basis = url.strip() if url and len(url) > 30 else _norm_title(title)
    return hashlib.sha256(basis.encode()).hexdigest()[:48]


def _norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9一-鿿]+", "", (title or "").lower())[:120]


def _title_seen_recently(db: Session, ticker_id: int | None, title: str) -> bool:
    """Cross-source near-dup: same normalized title for same ticker within 3 days."""
    norm = _norm_title(title)
    if not norm:
        return False
    since = datetime.utcnow() - timedelta(days=3)
    candidates = (
        db.query(Signal.title)
        .filter(Signal.ticker_id == ticker_id, Signal.fetched_at >= since)
        .order_by(Signal.id.desc())
        .limit(200)
        .all()
    )
    return any(_norm_title(t[0]) == norm for t in candidates)


def _store_items(db: Session, items: list[dict], ticker_id: int | None,
                 narrative_id: int | None = None) -> int:
    added = 0
    for item in items:
        url_hash = _hash(item.get("url", ""), item["title"])
        existing = db.query(Signal).filter_by(url_hash=url_hash).first()
        if existing is not None:
            # keyword feed may re-find a ticker signal: just add the narrative link
            if narrative_id and not any(
                l.narrative_id == narrative_id for l in existing.narrative_links
            ):
                db.add(SignalNarrative(signal_id=existing.id, narrative_id=narrative_id))
            continue
        if _title_seen_recently(db, ticker_id, item["title"]):
            continue
        signal = Signal(
            ticker_id=ticker_id,
            source=item["source"],
            lane=item.get("lane", "company"),
            publisher=item.get("publisher", ""),
            title=item["title"],
            url=item.get("url", ""),
            url_hash=url_hash,
            summary=item.get("summary", ""),
            published_at=item.get("published_at") or datetime.utcnow(),
            entities=item.get("entities") or [],
        )
        db.add(signal)
        db.flush()
        if narrative_id:
            db.add(SignalNarrative(signal_id=signal.id, narrative_id=narrative_id))
        added += 1
    db.commit()
    return added


def _log(db: Session, job: str, status: str, detail: str) -> None:
    db.add(OpsLog(job=job, status=status, detail=detail[:500]))
    # keep the table small
    ids = [r.id for r in db.query(OpsLog.id).order_by(OpsLog.id.desc()).offset(400).all()]
    if ids:
        db.query(OpsLog).filter(OpsLog.id.in_(ids)).delete(synchronize_session=False)
    db.commit()


def ingest_market(db: Session) -> dict:
    """Market-WIDE lanes — the discovery engine's raw material.

    Jin10 CN wire + official RSS pool + HN front page + EDGAR full-market
    stream. Per-source fault tolerance: one dead wire never blocks the rest.
    """
    counts: dict[str, int] = {}
    for name, fetch in (
        ("jin10", lambda: jin10.fetch_flash(30, db)),
        ("rss", lambda: rss_pool.fetch_all(per_feed=12)),
        ("hn", lambda: hn.fetch(20)),
        ("edgar_stream", lambda: edgar_stream.fetch_all(count=40)),
    ):
        try:
            counts[name] = _store_items(db, fetch(), None)
        except Exception as exc:  # noqa: BLE001 - single-source fault tolerance
            log.warning("market lane %s failed: %s", name, exc)
            counts[name] = -1
    return counts


def ingest_news(db: Session) -> dict:
    """Market-wide lanes + per-coverage-ticker news + narrative keywords."""
    market_counts = ingest_market(db)

    added = 0
    tickers = db.query(Ticker).filter_by(active=True).all()
    for ticker in tickers:
        query = ticker.news_query or f"{ticker.name or ticker.symbol} stock"
        items = google_news.fetch(query, limit=20)
        added += _store_items(db, items, ticker.id)

    narratives = db.query(Narrative).filter(Narrative.status != "resolved").all()
    for narrative in narratives:
        for keyword in (narrative.keywords or [])[:3]:
            items = google_news.fetch(keyword, limit=10)
            added += _store_items(db, items, None, narrative_id=narrative.id)

    result = triage.run_triage(db)
    market_str = " ".join(f"{k}:{v}" for k, v in market_counts.items())
    _log(db, "ingest_news", "ok",
         f"市场[{market_str}] 个股+{added},triage {result['triaged']}({result['engine']})")
    return {"added": added, "market": market_counts, **result}


def refresh_quotes(db: Session) -> dict:
    updated = 0
    for ticker in db.query(Ticker).filter_by(active=True).all():
        time.sleep(0.6)  # stay under Yahoo's burst rate limit
        quote = yahoo.get_quote(ticker.symbol)
        if quote and quote["price"] is not None:
            ticker.last_price = quote["price"]
            ticker.change_pct = quote["change_pct"]
            ticker.currency = quote["currency"]
            if quote["name"] and not ticker.name:
                ticker.name = quote["name"]
            ticker.quote_updated_at = datetime.utcnow()
            updated += 1
    db.commit()
    _autoscale_demo_targets(db)
    _log(db, "refresh_quotes", "ok", f"更新 {updated} 个报价")
    return {"updated": updated}


def _autoscale_demo_targets(db: Session) -> None:
    """Demo theses ship with podcast-style illustrative targets; once a live
    price exists, rescale them once so EV math looks sane forever after."""
    import copy

    from ..models import Idea

    for idea in db.query(Idea).filter_by(is_demo=True).all():
        if not (idea.thesis or {}).get("auto_scale") or not idea.ticker.last_price:
            continue
        # deep-copy first: mutating the loaded JSON in place would make the
        # old and new values compare equal at flush time -> no UPDATE emitted
        thesis = copy.deepcopy(idea.thesis)
        price = idea.ticker.last_price
        ref = thesis.get("ref_price") or price
        scenarios = thesis.get("scenarios") or {}
        if abs(price / ref - 1) > 0.2:
            # live price drifted far from the numbers' reference -> rescale
            factor = price / ref
            for leg in scenarios.values():
                if isinstance(leg, dict) and leg.get("target"):
                    leg["target"] = round(leg["target"] * factor, 1)
        thesis["auto_scale"] = False
        thesis["scenarios"] = scenarios
        idea.thesis = thesis
        db.commit()


def ingest_slow(db: Session) -> dict:
    """Hourly: EDGAR filings, StockTwits sentiment, earnings dates."""
    filings_added = 0
    sentiment_updated = 0
    for ticker in db.query(Ticker).filter_by(active=True).all():
        time.sleep(0.6)  # politeness across EDGAR / StockTwits / Yahoo
        if ticker.market == "US":
            if not ticker.cik:
                ticker.cik = edgar.lookup_cik(ticker.symbol)
                db.commit()
            if ticker.cik:
                items = edgar.fetch_filings(ticker.cik, limit=15)
                cutoff = datetime.utcnow() - timedelta(days=14)
                items = [i for i in items if i["published_at"] >= cutoff]
                filings_added += _store_items(db, items, ticker.id)
            snapshot = stocktwits.get_sentiment(ticker.symbol)
            if snapshot:
                ticker.st_bull_ratio = snapshot["bull_ratio"]
                ticker.st_watchers = snapshot["watchers"]
                ticker.st_updated_at = datetime.utcnow()
                sentiment_updated += 1
        earnings = yahoo.get_earnings_date(ticker.symbol)
        if earnings and earnings >= datetime.utcnow().strftime("%Y-%m-%d"):
            ticker.next_earnings = earnings  # Yahoo sometimes returns the past one
        db.commit()

    result = triage.run_triage(db)
    _log(db, "ingest_slow", "ok",
         f"EDGAR 新增 {filings_added},情绪更新 {sentiment_updated},triage {result['triaged']}")
    return {"filings_added": filings_added, "sentiment_updated": sentiment_updated, **result}


def bootstrap_ticker(db: Session, ticker: Ticker) -> None:
    """On ticker add: quote, name, CIK, first news pull (triage happens next cycle)."""
    quote = yahoo.get_quote(ticker.symbol)
    if quote:
        ticker.last_price = quote["price"]
        ticker.change_pct = quote["change_pct"]
        ticker.currency = quote["currency"]
        if quote["name"] and not ticker.name:
            ticker.name = quote["name"]
        ticker.quote_updated_at = datetime.utcnow()
    if ticker.market == "US" and not ticker.cik:
        ticker.cik = edgar.lookup_cik(ticker.symbol)
    if not ticker.news_query:
        ticker.news_query = f"{ticker.name or ticker.symbol} stock"
    db.commit()
    items = google_news.fetch(ticker.news_query, limit=15)
    _store_items(db, items, ticker.id)
