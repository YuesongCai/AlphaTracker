"""All REST endpoints. Prefix: /api"""
from __future__ import annotations

import hashlib
import logging
import threading
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .. import config
from ..ai import analysis, provider, triage as triage_mod
from ..db import all_settings, get_db, get_setting, set_setting
from ..models import (Brief, Driver, Evidence, Idea, JournalEntry, Narrative,
                      NarrativeTicker, OpsLog, Signal, SignalNarrative, Ticker)
from ..services import brief as brief_service
from ..services import discovery
from ..services import feishu, ideas as idea_service, ingest, narratives as narrative_service
from . import serializers as ser

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

_ingest_lock = threading.Lock()


# ------------------------------------------------------------------ dashboard

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    since24 = datetime.utcnow() - timedelta(hours=24)
    top_signals = (
        db.query(Signal)
        .filter(Signal.published_at >= since24, Signal.materiality >= 3,
                Signal.relevance >= 0.4)
        .order_by(Signal.materiality.desc(), Signal.published_at.desc())
        .limit(12).all()
    )
    movers = (
        db.query(Narrative).filter(Narrative.status != "resolved")
        .order_by(Narrative.momentum_score.desc()).limit(6).all()
    )
    tickers = db.query(Ticker).filter_by(active=True).order_by(Ticker.symbol).all()
    week = (datetime.utcnow() + timedelta(days=8)).strftime("%Y-%m-%d")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    earnings = [t for t in tickers
                if t.next_earnings and today <= t.next_earnings <= week]
    driver_alerts = (
        db.query(Evidence).join(Evidence.signal)
        .filter(Evidence.created_at >= since24 - timedelta(hours=48))
        .order_by(Evidence.created_at.desc()).limit(8).all()
    )
    latest_brief = db.query(Brief).filter(Brief.kind != "instant").order_by(Brief.id.desc()).first()
    pipeline_counts = dict(
        db.query(Idea.stage, func.count(Idea.id)).group_by(Idea.stage).all()
    )
    backend, detail = provider.resolve_backend(db)
    return {
        "top_signals": [ser.signal_out(s) for s in top_signals],
        "movers": [ser.narrative_out(n) for n in movers],
        "tickers": [ser.ticker_out(t) for t in tickers],
        "earnings_week": [ser.ticker_out(t) for t in earnings],
        "driver_alerts": [{
            "id": e.id, "stance": e.stance,
            "driver": e.driver.name, "idea_id": e.driver.idea_id,
            "symbol": e.driver.idea.ticker.symbol,
            "signal_title": e.signal.title, "signal_url": e.signal.url,
            "created_at": ser.iso(e.created_at),
        } for e in driver_alerts],
        "latest_brief": ser.brief_out(latest_brief) if latest_brief else None,
        "pipeline_counts": pipeline_counts,
        "llm": {"backend": backend, "detail": detail},
    }


# -------------------------------------------------------------------- tickers

class TickerIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    name: str = ""
    market: str = "US"
    sector: str = ""
    news_query: str = ""


@router.get("/tickers")
def list_tickers(db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=7)
    rows = db.query(Ticker).order_by(Ticker.symbol).all()
    counts = dict(
        db.query(Signal.ticker_id, func.count(Signal.id))
        .filter(Signal.published_at >= since).group_by(Signal.ticker_id).all()
    )
    idea_counts = dict(
        db.query(Idea.ticker_id, func.count(Idea.id))
        .filter(Idea.stage != "killed").group_by(Idea.ticker_id).all()
    )
    return [ser.ticker_out(t, {"signals_7d": counts.get(t.id, 0),
                               "idea_count": idea_counts.get(t.id, 0)}) for t in rows]


@router.post("/tickers")
def add_ticker(body: TickerIn, db: Session = Depends(get_db)):
    symbol = body.symbol.strip().upper()
    if db.query(Ticker).filter_by(symbol=symbol).first():
        raise HTTPException(409, f"{symbol} 已在覆盖池中")
    market = "HK" if symbol.endswith(".HK") else body.market.upper()
    ticker = Ticker(symbol=symbol, name=body.name.strip(), market=market,
                    sector=body.sector.strip(), news_query=body.news_query.strip())
    db.add(ticker)
    db.commit()
    try:
        ingest.bootstrap_ticker(db, ticker)
    except Exception as exc:  # noqa: BLE001 - bootstrap is best-effort
        log.warning("bootstrap failed for %s: %s", symbol, exc)
    return ser.ticker_out(ticker)


@router.get("/tickers/{ticker_id}")
def get_ticker(ticker_id: int, db: Session = Depends(get_db)):
    ticker = db.get(Ticker, ticker_id)
    if not ticker:
        raise HTTPException(404)
    signals = (
        db.query(Signal).filter_by(ticker_id=ticker_id)
        .order_by(Signal.published_at.desc()).limit(60).all()
    )
    ideas = db.query(Idea).filter_by(ticker_id=ticker_id).order_by(Idea.updated_at.desc()).all()
    narrative_ids = [
        l.narrative_id for l in db.query(NarrativeTicker).filter_by(ticker_id=ticker_id)
    ]
    narratives = db.query(Narrative).filter(Narrative.id.in_(narrative_ids)).all() if narrative_ids else []
    return {
        **ser.ticker_out(ticker),
        "signals": [ser.signal_out(s) for s in signals],
        "ideas": [ser.idea_out(i) for i in ideas],
        "narratives": [ser.narrative_out(n) for n in narratives],
    }


class TickerPatch(BaseModel):
    name: str | None = None
    sector: str | None = None
    news_query: str | None = None
    active: bool | None = None


@router.patch("/tickers/{ticker_id}")
def patch_ticker(ticker_id: int, body: TickerPatch, db: Session = Depends(get_db)):
    ticker = db.get(Ticker, ticker_id)
    if not ticker:
        raise HTTPException(404)
    for field in ("name", "sector", "news_query", "active"):
        value = getattr(body, field)
        if value is not None:
            setattr(ticker, field, value)
    db.commit()
    return ser.ticker_out(ticker)


@router.delete("/tickers/{ticker_id}")
def delete_ticker(ticker_id: int, db: Session = Depends(get_db)):
    ticker = db.get(Ticker, ticker_id)
    if not ticker:
        raise HTTPException(404)
    if ticker.ideas:
        raise HTTPException(400, "该标的存在 idea,先归档 idea 或将标的设为不活跃")
    db.query(Signal).filter_by(ticker_id=ticker_id).delete()
    db.query(NarrativeTicker).filter_by(ticker_id=ticker_id).delete()
    db.delete(ticker)
    db.commit()
    return {"ok": True}


# -------------------------------------------------------------------- signals

@router.get("/signals")
def list_signals(
    db: Session = Depends(get_db),
    ticker_id: int | None = None,
    narrative_id: int | None = None,
    event_type: str | None = None,
    lane: str | None = None,
    min_materiality: int = 1,
    variant_only: bool = False,
    q: str | None = None,
    days: int = 14,
    limit: int = 100,
    offset: int = 0,
):
    query = db.query(Signal).filter(
        Signal.published_at >= datetime.utcnow() - timedelta(days=min(days, 90))
    )
    if lane:
        query = query.filter(Signal.lane == lane)
    if ticker_id:
        query = query.filter(Signal.ticker_id == ticker_id)
    if narrative_id:
        query = query.join(SignalNarrative).filter(
            SignalNarrative.narrative_id == narrative_id
        )
    if event_type:
        query = query.filter(Signal.event_type == event_type)
    if min_materiality > 1:
        query = query.filter(Signal.materiality >= min_materiality)
    if variant_only:
        query = query.filter(Signal.variant.is_(True))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Signal.title.like(like), Signal.so_what.like(like)))
    total = query.count()
    rows = (query.order_by(Signal.published_at.desc())
            .offset(offset).limit(min(limit, 200)).all())
    return {"total": total, "items": [ser.signal_out(s) for s in rows]}


class ManualSignal(BaseModel):
    title: str
    url: str = ""
    summary: str = ""
    ticker_id: int | None = None


@router.post("/signals")
def add_manual_signal(body: ManualSignal, db: Session = Depends(get_db)):
    basis = body.url or body.title + datetime.utcnow().isoformat()
    signal = Signal(
        ticker_id=body.ticker_id, source="manual", publisher="手动录入",
        title=body.title.strip(), url=body.url.strip(), summary=body.summary.strip(),
        url_hash=hashlib.sha256(basis.encode()).hexdigest()[:48],
    )
    db.add(signal)
    db.commit()
    triage_mod.run_triage(db, limit=5)
    db.refresh(signal)
    return ser.signal_out(signal)


@router.post("/signals/{signal_id}/retriage")
def retriage_signal(signal_id: int, db: Session = Depends(get_db)):
    signal = db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(404)
    signal.triaged = False
    db.commit()
    triage_mod.run_triage(db, limit=5)
    db.refresh(signal)
    return ser.signal_out(signal)


# ----------------------------------------------------------------- narratives

class NarrativeIn(BaseModel):
    title: str
    question: str = ""
    description: str = ""
    stance_bull: str = ""
    stance_bear: str = ""
    kind: str = "company"
    keywords: list[str] = []
    ticker_ids: list[int] = []


@router.get("/narratives")
def list_narratives(db: Session = Depends(get_db), include_resolved: bool = False):
    query = db.query(Narrative)
    if not include_resolved:
        query = query.filter(Narrative.status != "resolved")
    rows = query.order_by(Narrative.momentum_score.desc()).all()
    return [ser.narrative_out(n) for n in rows]


@router.post("/narratives")
def create_narrative(body: NarrativeIn, db: Session = Depends(get_db)):
    narrative = Narrative(
        title=body.title.strip(), question=body.question.strip(),
        description=body.description.strip(), stance_bull=body.stance_bull.strip(),
        stance_bear=body.stance_bear.strip(), kind=body.kind,
        keywords=[k.strip() for k in body.keywords if k.strip()],
    )
    db.add(narrative)
    db.flush()
    for tid in body.ticker_ids:
        if db.get(Ticker, tid):
            db.add(NarrativeTicker(narrative_id=narrative.id, ticker_id=tid))
    db.commit()
    return ser.narrative_out(narrative)


@router.get("/narratives/{narrative_id}")
def get_narrative(narrative_id: int, db: Session = Depends(get_db)):
    narrative = db.get(Narrative, narrative_id)
    if not narrative:
        raise HTTPException(404)
    signals = (
        db.query(Signal).join(SignalNarrative)
        .filter(SignalNarrative.narrative_id == narrative_id)
        .order_by(Signal.published_at.desc()).limit(80).all()
    )
    return {
        **ser.narrative_out(narrative),
        "signals": [ser.signal_out(s) for s in signals],
        "timeline": narrative_service.timeline(db, narrative_id),
    }


class NarrativePatch(BaseModel):
    title: str | None = None
    question: str | None = None
    description: str | None = None
    stance_bull: str | None = None
    stance_bear: str | None = None
    status: str | None = None
    keywords: list[str] | None = None
    ticker_ids: list[int] | None = None


@router.patch("/narratives/{narrative_id}")
def patch_narrative(narrative_id: int, body: NarrativePatch, db: Session = Depends(get_db)):
    narrative = db.get(Narrative, narrative_id)
    if not narrative:
        raise HTTPException(404)
    for field in ("title", "question", "description", "stance_bull", "stance_bear",
                  "status", "keywords"):
        value = getattr(body, field)
        if value is not None:
            setattr(narrative, field, value)
    if body.ticker_ids is not None:
        db.query(NarrativeTicker).filter_by(narrative_id=narrative_id).delete()
        for tid in body.ticker_ids:
            if db.get(Ticker, tid):
                db.add(NarrativeTicker(narrative_id=narrative_id, ticker_id=tid))
    db.commit()
    return ser.narrative_out(narrative)


@router.delete("/narratives/{narrative_id}")
def delete_narrative(narrative_id: int, db: Session = Depends(get_db)):
    narrative = db.get(Narrative, narrative_id)
    if not narrative:
        raise HTTPException(404)
    db.query(SignalNarrative).filter_by(narrative_id=narrative_id).delete()
    db.query(NarrativeTicker).filter_by(narrative_id=narrative_id).delete()
    db.delete(narrative)
    db.commit()
    return {"ok": True}


@router.post("/narratives/suggest")
def suggest_narratives(db: Session = Depends(get_db)):
    try:
        suggestions, engine = analysis.suggest_narratives(db)
        return {"suggestions": suggestions, "engine": engine}
    except provider.LLMUnavailable as exc:
        raise HTTPException(503, f"AI 不可用:{exc}")
    except ValueError as exc:
        raise HTTPException(502, f"AI 输出解析失败:{exc}")


# ---------------------------------------------------------------------- ideas

class SniffIn(BaseModel):
    ticker_id: int | None = None
    symbol: str | None = None
    direction: str = "watch"


@router.get("/ideas")
def list_ideas(db: Session = Depends(get_db), include_killed: bool = True):
    query = db.query(Idea)
    if not include_killed:
        query = query.filter(Idea.stage != "killed")
    rows = query.order_by(Idea.updated_at.desc()).all()
    return [ser.idea_out(i) for i in rows]


@router.post("/ideas/sniff")
def create_via_sniff(body: SniffIn, db: Session = Depends(get_db)):
    """The podcast's filter-or-kill entry point: ticker -> AI sniff -> hunch."""
    ticker = None
    if body.ticker_id:
        ticker = db.get(Ticker, body.ticker_id)
    elif body.symbol:
        symbol = body.symbol.strip().upper()
        ticker = db.query(Ticker).filter_by(symbol=symbol).first()
        if ticker is None:
            ticker = Ticker(symbol=symbol, market="HK" if symbol.endswith(".HK") else "US")
            db.add(ticker)
            db.commit()
            try:
                ingest.bootstrap_ticker(db, ticker)
            except Exception as exc:  # noqa: BLE001
                log.warning("bootstrap during sniff failed: %s", exc)
    if ticker is None:
        raise HTTPException(400, "需要 ticker_id 或 symbol")

    try:
        sniff, engine = analysis.sniff_test(db, ticker)
    except provider.LLMUnavailable as exc:
        raise HTTPException(503, f"AI 不可用,无法生成 Sniff Test:{exc}")
    except ValueError as exc:
        raise HTTPException(502, f"AI 输出解析失败:{exc}")

    verdict = (sniff.get("verdict") or {}).get("action", "advance")
    idea = Idea(
        ticker_id=ticker.id,
        title=f"{ticker.symbol} · {(sniff.get('debates') or [{}])[0].get('question', 'Sniff Test')}"[:190],
        direction=body.direction, stage="hunch", sniff=sniff,
    )
    db.add(idea)
    db.flush()
    idea_service.log_journal(
        db, idea, "ai_flag",
        f"Sniff Test 完成(engine: {engine})。初判:{verdict} —— "
        f"{(sniff.get('verdict') or {}).get('rationale', '')}",
    )
    db.commit()
    return ser.idea_out(idea, full=True)


class IdeaIn(BaseModel):
    ticker_id: int
    title: str
    direction: str = "watch"


@router.post("/ideas")
def create_idea(body: IdeaIn, db: Session = Depends(get_db)):
    if not db.get(Ticker, body.ticker_id):
        raise HTTPException(404, "ticker 不存在")
    idea = Idea(ticker_id=body.ticker_id, title=body.title.strip(),
                direction=body.direction)
    db.add(idea)
    db.flush()
    idea_service.log_journal(db, idea, "stage_change", "手动创建 hunch")
    db.commit()
    return ser.idea_out(idea)


@router.get("/ideas/{idea_id}")
def get_idea(idea_id: int, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(404)
    return ser.idea_out(idea, full=True)


class IdeaPatch(BaseModel):
    title: str | None = None
    direction: str | None = None
    notes: str | None = None
    hypothesis: dict | None = None
    thesis: dict | None = None
    research_plan: dict | None = None


@router.patch("/ideas/{idea_id}")
def patch_idea(idea_id: int, body: IdeaPatch, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(404)
    for field in ("title", "direction", "notes", "hypothesis", "thesis", "research_plan"):
        value = getattr(body, field)
        if value is not None:
            setattr(idea, field, value)
    db.commit()
    return ser.idea_out(idea, full=True)


class StageIn(BaseModel):
    note: str = ""


@router.post("/ideas/{idea_id}/advance")
def advance_idea(idea_id: int, body: StageIn, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(404)
    idea_service.advance(db, idea, body.note)
    db.commit()
    return ser.idea_out(idea, full=True)


@router.post("/ideas/{idea_id}/kill")
def kill_idea(idea_id: int, body: StageIn, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(404)
    idea_service.kill(db, idea, body.note)
    db.commit()
    return ser.idea_out(idea, full=True)


@router.post("/ideas/{idea_id}/research-plan")
def generate_research_plan(idea_id: int, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(404)
    try:
        plan, engine = analysis.research_plan(db, idea)
    except provider.LLMUnavailable as exc:
        raise HTTPException(503, f"AI 不可用:{exc}")
    except ValueError as exc:
        raise HTTPException(502, f"AI 输出解析失败:{exc}")
    idea.research_plan = plan
    idea_service.log_journal(db, idea, "ai_flag", f"研究计划已生成(engine: {engine})")
    db.commit()
    return ser.idea_out(idea, full=True)


class JournalIn(BaseModel):
    content: str
    entry_type: str = "note"


@router.post("/ideas/{idea_id}/journal")
def add_journal(idea_id: int, body: JournalIn, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(404)
    entry_type = body.entry_type if body.entry_type in (
        "note", "belief_update", "stage_change", "ai_flag") else "note"
    idea_service.log_journal(db, idea, entry_type, body.content.strip())
    idea.updated_at = datetime.utcnow()
    db.commit()
    return ser.idea_out(idea, full=True)


# -------------------------------------------------------------------- drivers

class DriverIn(BaseModel):
    name: str
    description: str = ""
    signposts: list[dict] = []


@router.post("/ideas/{idea_id}/drivers")
def add_driver(idea_id: int, body: DriverIn, db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(404)
    driver = Driver(idea_id=idea_id, name=body.name.strip(),
                    description=body.description.strip(),
                    signposts=body.signposts)
    db.add(driver)
    db.commit()
    return ser.idea_out(idea, full=True)


class DriverPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    signposts: list[dict] | None = None


@router.patch("/drivers/{driver_id}")
def patch_driver(driver_id: int, body: DriverPatch, db: Session = Depends(get_db)):
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(404)
    for field in ("name", "description", "signposts"):
        value = getattr(body, field)
        if value is not None:
            setattr(driver, field, value)
    db.commit()
    return ser.driver_out(driver)


@router.delete("/drivers/{driver_id}")
def delete_driver(driver_id: int, db: Session = Depends(get_db)):
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(404)
    db.delete(driver)
    db.commit()
    return {"ok": True}


class EvidenceIn(BaseModel):
    signal_id: int
    stance: str = "neutral"
    note: str = ""


@router.post("/drivers/{driver_id}/evidence")
def add_evidence(driver_id: int, body: EvidenceIn, db: Session = Depends(get_db)):
    driver = db.get(Driver, driver_id)
    if not driver or not db.get(Signal, body.signal_id):
        raise HTTPException(404)
    stance = body.stance if body.stance in ("confirm", "refute", "neutral") else "neutral"
    existing = db.query(Evidence).filter_by(driver_id=driver_id, signal_id=body.signal_id).first()
    if existing:
        existing.stance, existing.note = stance, body.note
    else:
        db.add(Evidence(driver_id=driver_id, signal_id=body.signal_id,
                        stance=stance, note=body.note))
    db.commit()
    return ser.driver_out(driver)


# ------------------------------------------------------------------- discover

@router.get("/discover")
def discover(db: Session = Depends(get_db)):
    from ..models import NarrativeCandidate
    from ..sources import jin10

    candidates = (
        db.query(NarrativeCandidate)
        .filter(NarrativeCandidate.status.in_(["pending", "ai_skip"]))
        .order_by(NarrativeCandidate.score.desc())
        .limit(30).all()
    )
    out = []
    for cand in candidates:
        evidence = (
            db.query(Signal).filter(Signal.id.in_(cand.evidence_ids or []))
            .order_by(Signal.materiality.desc(), Signal.published_at.desc())
            .limit(6).all()
        ) if cand.evidence_ids else []
        out.append(ser.candidate_out(cand, evidence))

    try:
        calendar = jin10.fetch_calendar(min_star=2, db=db)
    except Exception:  # noqa: BLE001 - calendar is garnish, never a blocker
        calendar = []

    lanes = dict(
        db.query(Signal.lane, func.count(Signal.id))
        .filter(Signal.published_at >= datetime.utcnow() - timedelta(hours=24))
        .group_by(Signal.lane).all()
    )
    return {
        "candidates": out,
        "trending": discovery.trending_entities(db),
        "calendar": calendar,
        "lanes_24h": lanes,
    }


@router.post("/discover/scan")
def discover_scan(db: Session = Depends(get_db)):
    result = discovery.scan(db)
    return {"ok": True, **result}


@router.post("/discover/candidates/{cand_id}/promote")
def promote_candidate(cand_id: int, db: Session = Depends(get_db)):
    from ..models import NarrativeCandidate

    cand = db.get(NarrativeCandidate, cand_id)
    if not cand:
        raise HTTPException(404)
    narrative = discovery.promote(db, cand)
    return {"ok": True, "narrative": ser.narrative_out(narrative)}


@router.post("/discover/candidates/{cand_id}/dismiss")
def dismiss_candidate(cand_id: int, db: Session = Depends(get_db)):
    from ..models import NarrativeCandidate

    cand = db.get(NarrativeCandidate, cand_id)
    if not cand:
        raise HTTPException(404)
    discovery.dismiss(db, cand)
    return {"ok": True}


# --------------------------------------------------------------------- briefs

@router.get("/briefs")
def list_briefs(db: Session = Depends(get_db), limit: int = 20):
    rows = (db.query(Brief).filter(Brief.kind != "instant")
            .order_by(Brief.id.desc()).limit(limit).all())
    return [ser.brief_out(b) for b in rows]


class BriefIn(BaseModel):
    kind: str = "manual"
    send: bool = True


@router.post("/briefs/generate")
def generate_brief(body: BriefIn, db: Session = Depends(get_db)):
    kind = body.kind if body.kind in ("morning", "evening", "manual") else "manual"
    brief = brief_service.generate_brief(db, kind=kind, send=body.send)
    return ser.brief_out(brief)


@router.post("/briefs/{brief_id}/send")
def send_brief(brief_id: int, db: Session = Depends(get_db)):
    brief = db.get(Brief, brief_id)
    if not brief:
        raise HTTPException(404)
    ok, err = feishu.send_markdown(db, brief.content_md)
    brief.sent, brief.send_error = ok, err
    db.commit()
    return ser.brief_out(brief)


# ------------------------------------------------------------------- settings

SETTING_KEYS = set(config.DEFAULT_SETTINGS.keys())
MASKED = "••••••••"


@router.get("/settings")
def read_settings(db: Session = Depends(get_db)):
    settings = {k: v for k, v in all_settings(db).items() if k in SETTING_KEYS}
    if settings.get("llm.api_key"):
        settings["llm.api_key"] = MASKED
    backend, detail = provider.resolve_backend(db)
    return {"settings": settings, "llm": {"backend": backend, "detail": detail}}


class SettingsIn(BaseModel):
    settings: dict


@router.put("/settings")
def write_settings(body: SettingsIn, db: Session = Depends(get_db)):
    for key, value in body.settings.items():
        if key not in SETTING_KEYS:
            continue
        if key == "llm.api_key" and value == MASKED:
            continue  # untouched mask round-trip
        set_setting(db, key, value)
    db.commit()
    from ..scheduler import reschedule_briefs
    reschedule_briefs()
    return read_settings(db)


@router.get("/llm/status")
def llm_status(db: Session = Depends(get_db), force: bool = False):
    if force:
        provider.probe_cli(force=True)
    backend, detail = provider.resolve_backend(db)
    cli_ok, cli_detail = provider.probe_cli()
    return {"backend": backend, "detail": detail,
            "cli": {"ok": cli_ok, "detail": cli_detail},
            "api_key_set": bool((get_setting(db, "llm.api_key", "") or "").strip())}


# ------------------------------------------------------------------------ ops

@router.post("/ops/ingest")
def manual_ingest(db: Session = Depends(get_db), what: str = "news"):
    if not _ingest_lock.acquire(blocking=False):
        raise HTTPException(429, "已有摄取任务在运行")
    try:
        if what == "quotes":
            result = ingest.refresh_quotes(db)
        elif what == "slow":
            result = ingest.ingest_slow(db)
        elif what == "all":
            result = {"news": ingest.ingest_news(db),
                      "quotes": ingest.refresh_quotes(db),
                      "slow": ingest.ingest_slow(db)}
        else:
            result = ingest.ingest_news(db)
        narrative_service.refresh_all(db)
        brief_service.instant_alerts(db)
        return {"ok": True, "result": result}
    finally:
        _ingest_lock.release()


@router.get("/ops/status")
def ops_status(db: Session = Depends(get_db)):
    rows = db.query(OpsLog).order_by(OpsLog.id.desc()).limit(30).all()
    signal_count = db.query(func.count(Signal.id)).scalar()
    untriaged = db.query(func.count(Signal.id)).filter_by(triaged=False).scalar()
    from ..scheduler import job_overview
    return {
        "log": [{"job": r.job, "status": r.status, "detail": r.detail,
                 "ran_at": ser.iso(r.ran_at)} for r in rows],
        "signal_count": signal_count,
        "untriaged": untriaged,
        "jobs": job_overview(),
        "version": config.VERSION,
    }
