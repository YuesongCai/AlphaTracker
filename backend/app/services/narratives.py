"""Narrative momentum engine.

heat_7d        = materiality-weighted signal count over the last 7 days
momentum_ratio = 7d weighted rate vs the prior-21d weighted rate (per 7d)
momentum_score = 0..100 blend of acceleration and absolute heat
status         = forming / accelerating / cooling (resolved is manual-only)
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models import Narrative, Signal, SignalNarrative


def _weighted(signals: list[Signal]) -> float:
    return sum(max(s.materiality, 1) / 3.0 for s in signals)


def compute_momentum(now: datetime, signals: list[tuple[datetime, int, int]]) -> dict:
    """Pure function for testability.

    signals: list of (published_at, materiality, sentiment)
    """
    d7 = now - timedelta(days=7)
    d28 = now - timedelta(days=28)

    recent = [s for s in signals if s[0] >= d7]
    prior = [s for s in signals if d28 <= s[0] < d7]

    heat_7d = sum(max(m, 1) / 3.0 for _, m, _ in recent)
    prior_weighted = sum(max(m, 1) / 3.0 for _, m, _ in prior)
    if prior_weighted == 0:
        # cold start: no baseline yet — score from absolute heat only
        ratio = 1.0
        score = round(min(100.0, heat_7d * 5))
    else:
        prior_rate = prior_weighted / 3.0  # per-7d
        ratio = heat_7d / max(prior_rate, 0.5)
        # cap the acceleration term so score differentiates by absolute heat
        # instead of saturating at 100 whenever the baseline is thin
        score = round(min(100.0, min(ratio, 3.0) * 15 + heat_7d * 4))

    sentiment_7d = (sum(s for _, _, s in recent) / len(recent)) if recent else 0.0
    sentiment_28d = (sum(s for _, _, s in signals) / len(signals)) if signals else 0.0

    if heat_7d >= 2 and ratio >= 1.6:
        status = "accelerating"
    elif ratio <= 0.5 and heat_7d < 1.5:
        status = "cooling"
    else:
        status = "forming"

    return {
        "heat_7d": round(heat_7d, 2),
        "momentum_ratio": round(ratio, 2),
        "momentum_score": int(score),
        "sentiment_7d": round(sentiment_7d, 2),
        "sentiment_shift": round(sentiment_7d - sentiment_28d, 2),
        "status": status,
    }


def refresh_all(db: Session) -> int:
    """Recompute cached momentum for every non-resolved narrative."""
    now = datetime.utcnow()
    updated = 0
    for narrative in db.query(Narrative).all():
        rows = (
            db.query(Signal.published_at, Signal.materiality, Signal.sentiment)
            .join(SignalNarrative, SignalNarrative.signal_id == Signal.id)
            .filter(
                SignalNarrative.narrative_id == narrative.id,
                Signal.published_at >= now - timedelta(days=28),
                Signal.relevance >= 0.3,
            )
            .all()
        )
        result = compute_momentum(now, [(r[0], r[1], r[2]) for r in rows])
        narrative.heat_7d = result["heat_7d"]
        narrative.momentum_ratio = result["momentum_ratio"]
        narrative.momentum_score = result["momentum_score"]
        narrative.sentiment_7d = result["sentiment_7d"]
        narrative.sentiment_shift = result["sentiment_shift"]
        if narrative.status != "resolved":
            narrative.status = result["status"]
        updated += 1
    db.commit()
    return updated


def timeline(db: Session, narrative_id: int, days: int = 60) -> list[dict]:
    """Daily weighted-heat series for sparklines."""
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(Signal.published_at, Signal.materiality)
        .join(SignalNarrative, SignalNarrative.signal_id == Signal.id)
        .filter(SignalNarrative.narrative_id == narrative_id, Signal.published_at >= since)
        .all()
    )
    buckets: dict[str, float] = {}
    for published, materiality in rows:
        key = published.strftime("%Y-%m-%d")
        buckets[key] = buckets.get(key, 0.0) + max(materiality, 1) / 3.0
    day = since
    series = []
    while day <= datetime.utcnow():
        key = day.strftime("%Y-%m-%d")
        series.append({"date": key, "heat": round(buckets.get(key, 0.0), 2)})
        day += timedelta(days=1)
    return series
