"""Discovery engine — the product's reason to exist after the pivot:

cut through the market-wide signal flow and surface emerging narratives,
instead of waiting for the analyst to name a ticker.

Pipeline per scan:
  1. cluster last-48h triaged signals by canonical entity tag
  2. score: heat (materiality-weighted, recency-decayed)
            x publisher breadth x lane breadth x novelty vs 30d baseline
  3. top new clusters -> LLM synthesis into NarrativeCandidate (promote/dismiss)
     (no LLM -> heuristic candidates, still useful)
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..ai import prompts, provider
from ..models import (Narrative, NarrativeCandidate, NarrativeTicker, Signal,
                      SignalNarrative, Ticker)

log = logging.getLogger(__name__)

WINDOW_H = 48
BASELINE_D = 30
HALF_LIFE_H = 24.0
MIN_CLUSTER_SIGNALS = 3
MIN_SCORE = 2.0
SUPPRESS_DAYS = 7          # dismissed cluster keys stay quiet this long
MAX_LLM_PER_SCAN = 3

# Entities too generic to be a narrative hook.
STOPLIST = {
    "STOCK", "STOCKS", "MARKET", "MARKETS", "SHARES", "US", "USA", "ETF",
    "A股", "美股", "港股", "股市", "投资", "经济", "INVESTING", "WALL STREET",
    "WALLSTREET", "TRADING", "AI",  # bare "AI" clusters everything; sub-themes survive
}


def canon(entity: str) -> str:
    entity = (entity or "").strip().strip("#$")
    if not entity:
        return ""
    # tickers & short acronyms uppercase; multiword themes keep their casing
    if len(entity) <= 6 and entity.isascii() and " " not in entity:
        return entity.upper()
    return entity


def _decay(age_hours: float) -> float:
    return math.pow(0.5, max(age_hours, 0.0) / HALF_LIFE_H)


def score_cluster(signals: list[dict], baseline_count: int, now: datetime) -> dict:
    """Pure scoring function (unit-tested).

    signals: [{published_at, materiality, publisher, lane}]
    """
    heat = sum(
        (max(s["materiality"], 1) / 3.0)
        * _decay((now - s["published_at"]).total_seconds() / 3600)
        for s in signals
    )
    publishers = {s["publisher"] or "?" for s in signals}
    lanes = {s["lane"] for s in signals}
    breadth_pub = len(publishers)
    breadth_lane = len(lanes)
    novelty = baseline_count < 3

    score = heat
    score *= 1 + 0.25 * min(breadth_pub - 1, 4)   # corroboration across outlets
    if breadth_lane >= 2:
        score *= 1.5                               # crossed lanes = structural
    if novelty:
        score *= 1.8                               # newly hot > chronically hot
    return {
        "heat": round(heat, 2),
        "breadth_pub": breadth_pub,
        "breadth_lane": breadth_lane,
        "novelty": novelty,
        "score": round(score, 2),
    }


def _window_signals(db: Session, now: datetime) -> list[Signal]:
    return (
        db.query(Signal)
        .filter(Signal.triaged.is_(True),
                Signal.published_at >= now - timedelta(hours=WINDOW_H),
                Signal.relevance >= 0.35,
                Signal.materiality >= 2)
        .all()
    )


def _baseline_counts(db: Session, now: datetime, keys: set[str]) -> dict[str, int]:
    """How often each entity appeared in the 30d BEFORE the window."""
    rows = (
        db.query(Signal.entities)
        .filter(Signal.published_at < now - timedelta(hours=WINDOW_H),
                Signal.published_at >= now - timedelta(days=BASELINE_D))
        .all()
    )
    counts: dict[str, int] = {}
    for (entities,) in rows:
        for entity in entities or []:
            key = canon(entity)
            if key in keys:
                counts[key] = counts.get(key, 0) + 1
    return counts


def _tracked_keys(db: Session) -> set[str]:
    """Entities already represented by narratives or fresh candidates."""
    covered: set[str] = set()
    for narrative in db.query(Narrative).all():
        covered.add(canon(narrative.title.split("×")[0].split(":")[0]))
        for keyword in narrative.keywords or []:
            covered.add(canon(keyword))
        for link in narrative.ticker_links:
            covered.add(canon(link.ticker.symbol))
    active = db.query(NarrativeCandidate).filter(
        NarrativeCandidate.status.in_(["pending", "promoted"])
    ).all()
    for cand in active:
        covered.add(canon(cand.cluster_key))
    cutoff = datetime.utcnow() - timedelta(days=SUPPRESS_DAYS)
    for cand in db.query(NarrativeCandidate).filter(
        NarrativeCandidate.status.in_(["dismissed", "ai_skip"]),
        NarrativeCandidate.updated_at >= cutoff,
    ).all():
        covered.add(canon(cand.cluster_key))
    return covered


def scan(db: Session, llm_budget: int = MAX_LLM_PER_SCAN) -> dict:
    """One discovery pass. Returns counters for ops logging."""
    now = datetime.utcnow()
    signals = _window_signals(db, now)

    clusters: dict[str, list[Signal]] = {}
    for signal in signals:
        for entity in signal.entities or []:
            key = canon(entity)
            if key and key not in STOPLIST:
                clusters.setdefault(key, []).append(signal)

    if not clusters:
        return {"clusters": 0, "candidates_new": 0, "candidates_updated": 0}

    baseline = _baseline_counts(db, now, set(clusters))
    tracked = _tracked_keys(db)
    coverage_symbols = {t.symbol for t in db.query(Ticker.symbol).all()}

    scored: list[tuple[str, list[Signal], dict]] = []
    for key, cluster_signals in clusters.items():
        uniq = {s.id: s for s in cluster_signals}.values()
        cluster_signals = list(uniq)
        if len(cluster_signals) < MIN_CLUSTER_SIGNALS:
            continue
        metrics = score_cluster(
            [{"published_at": s.published_at, "materiality": s.materiality,
              "publisher": s.publisher, "lane": s.lane} for s in cluster_signals],
            baseline.get(key, 0), now,
        )
        if metrics["score"] >= MIN_SCORE:
            scored.append((key, cluster_signals, metrics))
    scored.sort(key=lambda x: x[2]["score"], reverse=True)

    new_count = updated = 0
    llm_used = 0
    for key, cluster_signals, metrics in scored[:20]:
        evidence_ids = [s.id for s in sorted(
            cluster_signals, key=lambda s: (s.materiality, s.published_at), reverse=True
        )][:12]
        existing = (
            db.query(NarrativeCandidate)
            .filter_by(cluster_key=key)
            .filter(NarrativeCandidate.status == "pending")
            .first()
        )
        if existing is not None:
            existing.score = metrics["score"]
            existing.heat = metrics["heat"]
            existing.breadth_pub = metrics["breadth_pub"]
            existing.breadth_lane = metrics["breadth_lane"]
            existing.evidence_ids = evidence_ids
            updated += 1
            continue
        if key in tracked:
            continue
        candidate = NarrativeCandidate(
            cluster_key=key, score=metrics["score"], heat=metrics["heat"],
            breadth_pub=metrics["breadth_pub"], breadth_lane=metrics["breadth_lane"],
            novelty=metrics["novelty"], evidence_ids=evidence_ids,
            title=f"{key}:热度升温", question="", engine="heuristic",
        )
        synthesized = None
        if llm_used < llm_budget:
            synthesized = _synthesize(db, key, cluster_signals)
        if key in coverage_symbols and synthesized is None:
            # A hot coverage name with no AI-framed debate adds nothing the
            # trending strip doesn't already show — candidates must add framing.
            continue
        if synthesized is not None:
            llm_used += 1
            for field in ("title", "question", "why_now", "driver_question",
                          "stance_bull", "stance_bear"):
                setattr(candidate, field, str(synthesized.get(field, ""))[:500])
            candidate.ticker_symbols = [
                str(s).upper() for s in synthesized.get("ticker_symbols") or []][:6]
            candidate.keywords = [str(k) for k in synthesized.get("keywords") or []][:4]
            candidate.engine = synthesized.get("_engine", "llm")
            candidate.ai_rationale = str(synthesized.get("rationale", ""))[:300]
            if not synthesized.get("worth_tracking", True):
                candidate.status = "ai_skip"
        db.add(candidate)
        new_count += 1
    db.commit()
    return {"clusters": len(scored), "candidates_new": new_count,
            "candidates_updated": updated, "llm_used": llm_used}


def _synthesize(db: Session, key: str, signals: list[Signal]) -> dict | None:
    top = sorted(signals, key=lambda s: (s.materiality, s.published_at), reverse=True)[:10]
    evidence = "\n".join(
        f"- {s.published_at:%m-%d %H:%M} | {s.publisher} | {s.title}"
        + (f" | {s.so_what}" if s.so_what else "")
        for s in top
    )
    existing = "\n".join(f"- {n.title}" for n in db.query(Narrative).all()) or "(无)"
    try:
        result, engine = provider.complete_json(
            db,
            prompts.CANDIDATE_PROMPT.format(entity=key, evidence=evidence, existing=existing),
            prompts.CANDIDATE_SYSTEM,
            max_tokens=1500,
        )
        if isinstance(result, dict):
            result["_engine"] = engine
            return result
    except (provider.LLMUnavailable, ValueError) as exc:
        log.info("candidate synthesis unavailable for %s: %s", key, exc)
    return None


# ------------------------------------------------------------------ actions --

def promote(db: Session, candidate: NarrativeCandidate) -> Narrative:
    """Candidate -> tracked Narrative; discovered tickers join coverage."""
    narrative = Narrative(
        title=candidate.title or f"{candidate.cluster_key} 叙事",
        question=candidate.question,
        description=candidate.why_now,
        stance_bull=candidate.stance_bull,
        stance_bear=candidate.stance_bear,
        kind="theme" if not candidate.ticker_symbols else "company",
        keywords=candidate.keywords or [candidate.cluster_key],
    )
    db.add(narrative)
    db.flush()

    for symbol in candidate.ticker_symbols or []:
        symbol = symbol.strip().upper()
        if not symbol or len(symbol) > 12:
            continue
        ticker = db.query(Ticker).filter_by(symbol=symbol).first()
        if ticker is None:
            ticker = Ticker(symbol=symbol,
                            market="HK" if symbol.endswith(".HK") else "US")
            db.add(ticker)
            db.flush()
        db.add(NarrativeTicker(narrative_id=narrative.id, ticker_id=ticker.id))

    for signal_id in candidate.evidence_ids or []:
        if db.get(Signal, signal_id):
            db.add(SignalNarrative(signal_id=signal_id, narrative_id=narrative.id))

    candidate.status = "promoted"
    db.commit()
    return narrative


def dismiss(db: Session, candidate: NarrativeCandidate) -> None:
    candidate.status = "dismissed"
    db.commit()


def trending_entities(db: Session, limit: int = 12) -> list[dict]:
    """Entity heat strip for the Radar page."""
    now = datetime.utcnow()
    signals = _window_signals(db, now)
    clusters: dict[str, list[Signal]] = {}
    for signal in signals:
        for entity in signal.entities or []:
            key = canon(entity)
            if key and key not in STOPLIST:
                clusters.setdefault(key, []).append(signal)
    baseline = _baseline_counts(db, now, set(clusters))
    out = []
    for key, cluster_signals in clusters.items():
        uniq = list({s.id: s for s in cluster_signals}.values())
        if len(uniq) < 2:
            continue
        metrics = score_cluster(
            [{"published_at": s.published_at, "materiality": s.materiality,
              "publisher": s.publisher, "lane": s.lane} for s in uniq],
            baseline.get(key, 0), now,
        )
        sample = max(uniq, key=lambda s: s.materiality)
        out.append({"entity": key, **metrics, "count": len(uniq),
                    "sample_title": sample.title[:120]})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:limit]
