"""Generative analysis: sniff tests, research plans, narrative discovery.

All outputs are hypothesis-layer material — the UI labels them as such.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models import Narrative, Signal, Ticker
from . import prompts, provider

log = logging.getLogger(__name__)


def sniff_test(db: Session, ticker: Ticker) -> tuple[dict, str]:
    """Generate a sniff test for a ticker. Raises LLMUnavailable."""
    headlines = (
        db.query(Signal)
        .filter(Signal.ticker_id == ticker.id)
        .order_by(Signal.published_at.desc())
        .limit(15)
        .all()
    )
    headline_block = "\n".join(
        f"- [{s.published_at:%m-%d}] {s.title}" for s in headlines
    ) or "(暂无,凭你的知识作答并注明截止时间)"

    prompt = prompts.SNIFF_PROMPT.format(
        symbol=ticker.symbol,
        name=ticker.name or ticker.symbol,
        price=f"{ticker.last_price:.2f}" if ticker.last_price else "未知",
        currency=ticker.currency,
        change_pct=f"{ticker.change_pct:+.2f}%" if ticker.change_pct is not None else "未知",
        headlines=headline_block,
    )
    result, engine = provider.complete_json(db, prompt, prompts.SNIFF_SYSTEM, max_tokens=4000)
    if not isinstance(result, dict) or "focus5" not in result:
        raise ValueError("sniff test result malformed")
    result["_meta"] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "engine": engine,
        "price_at_generation": ticker.last_price,
        "disclaimer": "AI 预研素材(hypothesis 层),需人工验证,不构成投资建议",
    }
    return result, engine


def research_plan(db: Session, idea) -> tuple[dict, str]:
    """Generate a research plan for an idea. Raises LLMUnavailable."""
    context_parts = []
    if idea.sniff:
        debates = idea.sniff.get("debates") or []
        context_parts.append("关键辩论: " + "; ".join(d.get("question", "") for d in debates))
        verdict = idea.sniff.get("verdict") or {}
        context_parts.append(f"sniff 结论: {verdict.get('rationale', '')}")
    if idea.hypothesis:
        props = idea.hypothesis.get("propositions") or []
        context_parts.append("待验证命题: " + "; ".join(p.get("text", str(p)) if isinstance(p, dict) else str(p) for p in props))
    if idea.notes:
        context_parts.append(f"分析师笔记: {idea.notes[:500]}")

    prompt = prompts.RESEARCH_PLAN_PROMPT.format(
        symbol=idea.ticker.symbol,
        name=idea.ticker.name,
        title=idea.title,
        direction=idea.direction,
        context="\n".join(context_parts) or "(无,基于常识制定)",
    )
    result, engine = provider.complete_json(
        db, prompt, prompts.RESEARCH_PLAN_SYSTEM, max_tokens=4000
    )
    if not isinstance(result, dict) or "analyses" not in result:
        raise ValueError("research plan malformed")
    # normalize into checkable items
    for section in ("analyses", "people"):
        for item in result.get(section) or []:
            if isinstance(item, dict):
                item.setdefault("done", False)
    result["_meta"] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "engine": engine,
        "disclaimer": "AI 生成的研究编排建议,访谈与判断由人完成",
    }
    return result, engine


def suggest_narratives(db: Session) -> tuple[list, str]:
    """Discover new narratives from recent high-materiality signals."""
    existing = db.query(Narrative).all()
    existing_block = "\n".join(f"- {n.title}" for n in existing) or "(无)"
    since = datetime.utcnow() - timedelta(hours=72)
    signals = (
        db.query(Signal)
        .filter(Signal.published_at >= since, Signal.materiality >= 3)
        .order_by(Signal.materiality.desc(), Signal.published_at.desc())
        .limit(40)
        .all()
    )
    if len(signals) < 5:
        return [], "none"
    signal_block = "\n".join(
        f"- [{s.ticker.symbol if s.ticker else 'MACRO'}|重要性{s.materiality}] "
        f"{s.title}" + (f" ({s.so_what})" if s.so_what else "")
        for s in signals
    )
    prompt = prompts.NARRATIVE_SUGGEST_PROMPT.format(
        existing=existing_block, signals=signal_block
    )
    result, engine = provider.complete_json(
        db, prompt, prompts.NARRATIVE_SUGGEST_SYSTEM, max_tokens=2500
    )
    if not isinstance(result, list):
        raise ValueError("narrative suggestions malformed")
    return result[:3], engine
