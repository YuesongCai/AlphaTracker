"""Idea pipeline logic: stage transitions with journaling, scenario EV math."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Idea, JournalEntry

STAGES = ["hunch", "hypothesis", "thesis"]


def scenario_ev(scenarios: dict, current_price: float | None) -> dict | None:
    """Expected value & skew from {bull|base|bear: {target, prob}}.

    Probabilities are normalized if they don't sum to 1.
    """
    if not scenarios or not current_price or current_price <= 0:
        return None
    legs = []
    for name in ("bull", "base", "bear"):
        leg = scenarios.get(name) or {}
        try:
            target = float(leg.get("target"))
            prob = float(leg.get("prob"))
        except (TypeError, ValueError):
            return None
        if target <= 0 or prob < 0:
            return None
        legs.append((name, target, prob))
    total_prob = sum(p for _, _, p in legs)
    if total_prob <= 0:
        return None
    legs = [(n, t, p / total_prob) for n, t, p in legs]

    ev_return = sum(p * (t / current_price - 1) for _, t, p in legs)
    bull = next(t for n, t, _ in legs if n == "bull")
    bear = next(t for n, t, _ in legs if n == "bear")
    upside = bull / current_price - 1
    downside = 1 - bear / current_price
    skew = (upside / downside) if downside > 0 else None
    return {
        "ev_return": round(ev_return, 4),
        "upside": round(upside, 4),
        "downside": round(-downside, 4),
        "skew": round(skew, 2) if skew is not None else None,
        "legs": [{"name": n, "target": t, "prob": round(p, 3)} for n, t, p in legs],
    }


def log_journal(db: Session, idea: Idea, entry_type: str, content: str) -> None:
    db.add(JournalEntry(idea_id=idea.id, entry_type=entry_type, content=content))


def advance(db: Session, idea: Idea, note: str = "") -> str:
    """Move one stage up; journaling is mandatory (process leaves a trail)."""
    if idea.stage == "killed":
        idea.stage = "hunch"
        log_journal(db, idea, "stage_change", f"复活想法 → hunch。{note}")
        return idea.stage
    idx = STAGES.index(idea.stage) if idea.stage in STAGES else 0
    if idx >= len(STAGES) - 1:
        return idea.stage
    idea.stage = STAGES[idx + 1]
    label = {"hypothesis": "升级为 Hypothesis:形成可检验命题",
             "thesis": "升级为 Thesis:完成研究,进入监控"}[idea.stage]
    log_journal(db, idea, "stage_change", f"{label}。{note}".strip())
    return idea.stage


def kill(db: Session, idea: Idea, reason: str) -> None:
    idea.stage = "killed"
    log_journal(db, idea, "stage_change", f"否决(filter-or-kill):{reason or '未说明理由'}")
