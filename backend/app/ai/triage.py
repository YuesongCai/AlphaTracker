"""Batch triage of untriaged signals: LLM first, heuristics as safety net."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..models import Driver, Idea, Narrative, Signal, SignalNarrative, Evidence, Ticker
from . import heuristics, prompts, provider

log = logging.getLogger(__name__)

BATCH_SIZE = 12


def _context_blocks(db: Session) -> tuple[str, str, str, set[int], set[int]]:
    coverage = "\n".join(
        f"{t.id}|{t.symbol}|{t.name}" for t in db.query(Ticker).filter_by(active=True)
    ) or "(空)"
    narratives = db.query(Narrative).filter(Narrative.status != "resolved").all()
    narr_block = "\n".join(f"{n.id}|{n.title}|{n.question}" for n in narratives) or "(空)"
    drivers = (
        db.query(Driver)
        .join(Idea)
        .filter(Idea.stage.in_(["hypothesis", "thesis"]))
        .all()
    )
    driver_block = "\n".join(
        f"{d.id}|{d.idea.ticker.symbol}|{d.name}" for d in drivers
    ) or "(空)"
    return (
        coverage,
        narr_block,
        driver_block,
        {n.id for n in narratives},
        {d.id for d in drivers},
    )


def _apply_heuristic(signal: Signal, db: Session | None = None) -> None:
    form = signal.title.split("]")[0].lstrip("[") if signal.source == "edgar" else None
    result = heuristics.triage_one(signal.title, signal.source, form)
    _apply_result(signal, result, engine="heuristic")
    if db is not None:
        _keyword_link_narratives(db, signal)


def _keyword_link_narratives(db: Session, signal: Signal) -> None:
    """No-LLM narrative mapping: shared ticker + keyword token in the title."""
    if not signal.ticker_id:
        return
    title = (signal.title or "").lower()
    narratives = (
        db.query(Narrative)
        .join(Narrative.ticker_links)
        .filter(Narrative.status != "resolved")
        .all()
    )
    for narrative in narratives:
        if signal.ticker_id not in {l.ticker_id for l in narrative.ticker_links}:
            continue
        tokens = {
            word.lower()
            for keyword in (narrative.keywords or [])
            for word in keyword.split()
            if len(word) > 3
        }
        if tokens and any(token in title for token in tokens):
            exists = (
                db.query(SignalNarrative)
                .filter_by(signal_id=signal.id, narrative_id=narrative.id)
                .first()
            )
            if not exists:
                db.add(SignalNarrative(signal_id=signal.id, narrative_id=narrative.id))


def _apply_result(signal: Signal, result: dict, engine: str) -> None:
    signal.relevance = max(0.0, min(1.0, float(result.get("relevance", 0.5))))
    signal.materiality = max(1, min(5, int(result.get("materiality", 2))))
    signal.sentiment = max(-2, min(2, int(result.get("sentiment", 0))))
    signal.event_type = str(result.get("event_type", "other"))[:20]
    signal.so_what = str(result.get("so_what", ""))[:300]
    signal.variant = bool(result.get("variant", False))
    signal.triaged = True
    signal.triage_engine = engine


def _link_narratives(db: Session, signal: Signal, ids, valid: set[int]) -> None:
    for nid in ids or []:
        try:
            nid = int(nid)
        except (TypeError, ValueError):
            continue
        if nid in valid:
            exists = (
                db.query(SignalNarrative)
                .filter_by(signal_id=signal.id, narrative_id=nid)
                .first()
            )
            if not exists:
                db.add(SignalNarrative(signal_id=signal.id, narrative_id=nid))


def _link_drivers(db: Session, signal: Signal, result: dict, valid: set[int]) -> None:
    stance = result.get("driver_stance") or "neutral"
    if stance not in ("confirm", "refute", "neutral"):
        stance = "neutral"
    for did in result.get("driver_ids") or []:
        try:
            did = int(did)
        except (TypeError, ValueError):
            continue
        if did in valid:
            exists = db.query(Evidence).filter_by(driver_id=did, signal_id=signal.id).first()
            if not exists:
                db.add(Evidence(driver_id=did, signal_id=signal.id, stance=stance,
                                note=signal.so_what or "自动映射"))


def run_triage(db: Session, limit: int = 120) -> dict:
    """Triage untriaged signals. LLM path is rate-limited by `limit` per run;
    the heuristic path is cheap and always clears the whole backlog."""
    backend, _ = provider.resolve_backend(db)

    query = db.query(Signal).filter_by(triaged=False).order_by(Signal.published_at.desc())
    pending = query.all() if backend == "off" else query.limit(limit).all()
    if not pending:
        return {"triaged": 0, "engine": "none"}

    if backend == "off":
        for signal in pending:
            _apply_heuristic(signal, db)
        db.commit()
        return {"triaged": len(pending), "engine": "heuristic"}

    coverage, narr_block, driver_block, valid_narr, valid_drv = _context_blocks(db)
    done = 0
    engine_used = "heuristic"
    for i in range(0, len(pending), BATCH_SIZE):
        batch = pending[i : i + BATCH_SIZE]
        items = "\n".join(
            f"- id={s.id} [{s.ticker.symbol if s.ticker else 'MACRO'}|{s.source}"
            f"|{s.publisher}] {s.title}"
            for s in batch
        )
        prompt = prompts.TRIAGE_PROMPT.format(
            coverage=coverage, narratives=narr_block, drivers=driver_block, items=items
        )
        by_id = {s.id: s for s in batch}
        try:
            results, engine = provider.complete_json(
                db, prompt, prompts.TRIAGE_SYSTEM, max_tokens=4000
            )
            engine_used = engine
            if not isinstance(results, list):
                raise ValueError("triage result is not a list")
            seen = set()
            for row in results:
                sid = row.get("id")
                signal = by_id.get(int(sid)) if sid is not None else None
                if signal is None:
                    continue
                _apply_result(signal, row, engine)
                _link_narratives(db, signal, row.get("narrative_ids"), valid_narr)
                _link_drivers(db, signal, row, valid_drv)
                seen.add(signal.id)
            for signal in batch:  # anything the model skipped
                if signal.id not in seen:
                    _apply_heuristic(signal, db)
        except (provider.LLMUnavailable, ValueError, TypeError) as exc:
            log.warning("LLM triage batch failed (%s); falling back to heuristics", exc)
            for signal in batch:
                _apply_heuristic(signal, db)
        done += len(batch)
        db.commit()
    return {"triaged": done, "engine": engine_used}
