"""Plain-dict serializers (kept out of routes for reuse)."""
from __future__ import annotations

from datetime import datetime

from ..models import Brief, Driver, Idea, JournalEntry, Narrative, Signal, Ticker
from ..services.ideas import scenario_ev


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def ticker_out(t: Ticker, counts: dict | None = None) -> dict:
    out = {
        "id": t.id, "symbol": t.symbol, "name": t.name, "market": t.market,
        "sector": t.sector, "news_query": t.news_query, "active": t.active,
        "last_price": t.last_price, "change_pct": t.change_pct,
        "currency": t.currency, "next_earnings": t.next_earnings,
        "st_bull_ratio": t.st_bull_ratio, "st_watchers": t.st_watchers,
        "quote_updated_at": iso(t.quote_updated_at),
    }
    if counts:
        out.update(counts)
    return out


def signal_out(s: Signal) -> dict:
    return {
        "id": s.id,
        "ticker": {"id": s.ticker.id, "symbol": s.ticker.symbol} if s.ticker else None,
        "source": s.source, "publisher": s.publisher, "title": s.title,
        "url": s.url, "summary": s.summary,
        "published_at": iso(s.published_at),
        "triaged": s.triaged, "triage_engine": s.triage_engine,
        "relevance": s.relevance, "materiality": s.materiality,
        "sentiment": s.sentiment, "event_type": s.event_type,
        "so_what": s.so_what, "variant": s.variant,
        "narratives": [
            {"id": l.narrative.id, "title": l.narrative.title} for l in s.narrative_links
        ],
    }


def narrative_out(n: Narrative, tickers: bool = True) -> dict:
    return {
        "id": n.id, "title": n.title, "question": n.question,
        "description": n.description, "stance_bull": n.stance_bull,
        "stance_bear": n.stance_bear, "kind": n.kind, "status": n.status,
        "keywords": n.keywords or [],
        "heat_7d": n.heat_7d, "momentum_ratio": n.momentum_ratio,
        "momentum_score": n.momentum_score, "sentiment_7d": n.sentiment_7d,
        "sentiment_shift": n.sentiment_shift,
        "created_at": iso(n.created_at),
        "tickers": [
            {"id": l.ticker.id, "symbol": l.ticker.symbol} for l in n.ticker_links
        ] if tickers else [],
    }


def driver_out(d: Driver) -> dict:
    ev = [
        {
            "id": e.id, "stance": e.stance, "note": e.note,
            "created_at": iso(e.created_at),
            "signal": {"id": e.signal.id, "title": e.signal.title, "url": e.signal.url,
                       "published_at": iso(e.signal.published_at),
                       "materiality": e.signal.materiality},
        }
        for e in sorted(d.evidence, key=lambda x: x.created_at, reverse=True)
    ]
    confirm = sum(1 for e in d.evidence if e.stance == "confirm")
    refute = sum(1 for e in d.evidence if e.stance == "refute")
    return {
        "id": d.id, "name": d.name, "description": d.description,
        "signposts": d.signposts or [], "evidence": ev,
        "confirm_count": confirm, "refute_count": refute,
    }


def journal_out(j: JournalEntry) -> dict:
    return {"id": j.id, "entry_type": j.entry_type, "content": j.content,
            "created_at": iso(j.created_at)}


def idea_out(i: Idea, full: bool = False) -> dict:
    thesis = i.thesis or {}
    ev = scenario_ev(thesis.get("scenarios") or {}, i.ticker.last_price)
    out = {
        "id": i.id, "title": i.title, "direction": i.direction, "stage": i.stage,
        "is_demo": i.is_demo,
        "ticker": {"id": i.ticker.id, "symbol": i.ticker.symbol, "name": i.ticker.name,
                   "last_price": i.ticker.last_price, "change_pct": i.ticker.change_pct,
                   "currency": i.ticker.currency},
        "created_at": iso(i.created_at), "updated_at": iso(i.updated_at),
        "ev": ev,
        "driver_count": len(i.drivers),
        "has_sniff": bool(i.sniff),
        "has_plan": bool(i.research_plan),
    }
    if full:
        out.update({
            "sniff": i.sniff or {}, "hypothesis": i.hypothesis or {},
            "research_plan": i.research_plan or {}, "thesis": thesis,
            "notes": i.notes,
            "drivers": [driver_out(d) for d in i.drivers],
            "journal": [journal_out(j) for j in sorted(i.journal, key=lambda x: x.created_at, reverse=True)],
        })
    return out


def brief_out(b: Brief) -> dict:
    return {"id": b.id, "kind": b.kind, "title": b.title, "content_md": b.content_md,
            "created_at": iso(b.created_at), "sent": b.sent, "send_error": b.send_error}
