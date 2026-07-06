"""Brief assembly (morning/evening/manual) and instant alerts.

Template does the structure; the LLM (when available) writes the synthesis.
Falls back to pure template so briefs never stop flowing.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .. import config
from ..ai import prompts, provider
from ..db import get_setting
from ..models import Brief, Evidence, Idea, Narrative, Signal, Ticker
from . import feishu, narratives as narrative_service

log = logging.getLogger(__name__)

STAGE_LABEL = {"hunch": "Hunch", "hypothesis": "Hypothesis", "thesis": "Thesis"}


def _beijing_now() -> datetime:
    return datetime.now(config.BEIJING)


def _collect(db: Session, hours: int) -> dict:
    """Gather structured data for a brief window."""
    since = datetime.utcnow() - timedelta(hours=hours)

    signals = (
        db.query(Signal)
        .filter(Signal.published_at >= since, Signal.materiality >= 3,
                Signal.relevance >= 0.4)
        .order_by(Signal.materiality.desc(), Signal.published_at.desc())
        .limit(30)
        .all()
    )

    # group by first linked narrative (fallback: ticker bucket)
    groups: dict[str, list[Signal]] = {}
    for s in signals:
        if s.narrative_links:
            key = s.narrative_links[0].narrative.title
        elif s.ticker:
            key = f"{s.ticker.symbol} 个股"
        else:
            key = "宏观 / 其他"
        groups.setdefault(key, []).append(s)

    driver_alerts = (
        db.query(Evidence)
        .join(Evidence.signal)
        .filter(Evidence.created_at >= since, Signal.materiality >= 3)
        .all()
    )

    week_ahead = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    earnings = (
        db.query(Ticker)
        .filter(Ticker.active.is_(True), Ticker.next_earnings.isnot(None),
                Ticker.next_earnings >= today, Ticker.next_earnings <= week_ahead)
        .order_by(Ticker.next_earnings)
        .all()
    )

    movers = (
        db.query(Narrative)
        .filter(Narrative.status == "accelerating")
        .order_by(Narrative.momentum_score.desc())
        .limit(5)
        .all()
    )

    stale = (
        db.query(Idea)
        .filter(Idea.stage.in_(["hunch", "hypothesis"]),
                Idea.updated_at < datetime.utcnow() - timedelta(days=7))
        .all()
    )

    from ..models import NarrativeCandidate
    candidates = (
        db.query(NarrativeCandidate)
        .filter(NarrativeCandidate.status == "pending",
                NarrativeCandidate.created_at >= since)
        .order_by(NarrativeCandidate.score.desc())
        .limit(3).all()
    )
    return {"groups": groups, "driver_alerts": driver_alerts, "earnings": earnings,
            "movers": movers, "stale_ideas": stale, "candidates": candidates}


def _render_template(data: dict, kind_label: str) -> str:
    """Deterministic fallback rendering (also the LLM's raw material)."""
    now = _beijing_now()
    lines = [f"**Mosaic {kind_label}** · {now:%m-%d %H:%M} 北京时间", ""]

    if data.get("candidates"):
        lines.append("◈ **雷达新发现**(待审叙事候选)")
        for cand in data["candidates"]:
            why = f" —— {cand.why_now}" if cand.why_now else ""
            lines.append(f"  · **{cand.title or cand.cluster_key}**"
                         f"(热度{cand.score:.0f},{cand.breadth_pub}源){why}")
        lines.append("")

    if data["movers"]:
        movers = " · ".join(
            f"{n.title}(动量 {n.momentum_score}{'↑' if n.momentum_ratio > 1.2 else ''})"
            for n in data["movers"]
        )
        lines += [f"🔥 **叙事升温**:{movers}", ""]

    if data["groups"]:
        lines.append("📡 **要闻信号**")
        for group, signals in list(data["groups"].items())[:6]:
            lines.append(f"▸ {group}")
            for s in signals[:3]:
                tick = s.ticker.symbol if s.ticker else "宏观"
                so_what = s.so_what or s.title
                mark = "⚡" if s.materiality >= 4 else "·"
                link = f"[原文]({s.url})" if s.url else ""
                lines.append(f"  {mark} **{tick}** {so_what} {link}")
        lines.append("")
    else:
        lines += ["📡 窗口期内无重要性≥3的信号。", ""]

    if data["driver_alerts"]:
        lines.append("🎯 **Driver 警报**(证据触及活跃 thesis)")
        for ev in data["driver_alerts"][:5]:
            stance = {"confirm": "✅ 支持", "refute": "❌ 证伪", "neutral": "◽ 中性"}[ev.stance]
            lines.append(
                f"  {stance} {ev.driver.idea.ticker.symbol} · {ev.driver.name}:{ev.signal.title[:60]}"
            )
        lines.append("")

    if data["earnings"]:
        earnings = " · ".join(f"{t.symbol}({t.next_earnings[5:]})" for t in data["earnings"])
        lines += [f"📅 **本周财报**:{earnings}", ""]

    if data["stale_ideas"]:
        stale = " · ".join(
            f"{i.ticker.symbol}[{STAGE_LABEL.get(i.stage, i.stage)}]" for i in data["stale_ideas"][:5]
        )
        lines += [f"⏳ **管线提醒**:{stale} 超过7天未推进", ""]

    lines.append("—— 信号非结论 · Mosaic")
    return "\n".join(lines)


def _llm_polish(db: Session, data: dict, kind_label: str, template_md: str) -> str:
    """Ask the LLM to write the brief from structured data; fallback to template."""
    try:
        compact = []
        for group, signals in data["groups"].items():
            for s in signals[:4]:
                compact.append(
                    f"[{group}] {s.ticker.symbol if s.ticker else '宏观'} "
                    f"重要性{s.materiality} 情绪{s.sentiment:+d}: {s.title}"
                    + (f" | so-what: {s.so_what}" if s.so_what else "")
                    + (f" | url: {s.url}" if s.url else "")
                )
        payload = (
            "雷达新发现(叙事候选): " + "; ".join(
                f"{c.title or c.cluster_key}(热度{c.score:.0f})"
                for c in data.get("candidates") or []
            )
            + "\n\n信号:\n" + "\n".join(compact[:25])
            + "\n\n叙事动量: " + "; ".join(
                f"{n.title}(分数{n.momentum_score},比率{n.momentum_ratio})" for n in data["movers"]
            )
            + "\n\n本周财报: " + ", ".join(
                f"{t.symbol} {t.next_earnings}" for t in data["earnings"]
            )
            + "\n\nDriver警报: " + "; ".join(
                f"{ev.driver.idea.ticker.symbol}/{ev.driver.name}[{ev.stance}] {ev.signal.title[:50]}"
                for ev in data["driver_alerts"][:5]
            )
        )
        text, _engine = provider.complete(
            db,
            prompts.BRIEF_PROMPT.format(kind_label=kind_label, data=payload),
            prompts.BRIEF_SYSTEM,
            max_tokens=2000,
        )
        text = text.strip()
        if len(text) > 80:
            return text + "\n\n—— 信号非结论 · Mosaic"
    except provider.LLMUnavailable as exc:
        log.info("brief LLM polish unavailable: %s", exc)
    except Exception as exc:  # noqa: BLE001
        log.warning("brief LLM polish failed: %s", exc)
    return template_md


def generate_brief(db: Session, kind: str = "manual", send: bool = True,
                   use_llm: bool = True) -> Brief:
    kind_label = {"morning": "晨报", "evening": "晚报", "manual": "简报"}.get(kind, "简报")
    hours = {"morning": 14, "evening": 11}.get(kind, 24)

    narrative_service.refresh_all(db)
    data = _collect(db, hours)
    template_md = _render_template(data, kind_label)
    content = _llm_polish(db, data, kind_label, template_md) if use_llm else template_md

    brief = Brief(kind=kind, title=f"{kind_label} {_beijing_now():%m-%d}", content_md=content)
    db.add(brief)
    db.commit()

    if send:
        ok, err = feishu.send_markdown(db, content)
        brief.sent = ok
        brief.send_error = err
        db.commit()
    return brief


# ------------------------------------------------------------ instant alerts --

def instant_alerts(db: Session) -> int:
    """Push materiality>=threshold signals on thesis names (or 5 anywhere).

    Called after each triage cycle. De-duped via a marker journal in briefs.
    """
    if not get_setting(db, "alerts.enabled", True):
        return 0
    threshold = int(get_setting(db, "alerts.min_materiality", 4))

    thesis_ticker_ids = {
        i.ticker_id for i in db.query(Idea).filter(Idea.stage == "thesis").all()
    }
    since = datetime.utcnow() - timedelta(hours=3)
    candidates = (
        db.query(Signal)
        .filter(Signal.triaged.is_(True), Signal.published_at >= since,
                Signal.relevance >= 0.5)
        .all()
    )
    already = {
        b.title for b in db.query(Brief).filter(
            Brief.kind == "instant", Brief.created_at >= since - timedelta(hours=3)
        ).all()
    }
    sent = 0
    for s in candidates:
        hot = s.materiality >= 5 or (s.materiality >= threshold and s.ticker_id in thesis_ticker_ids)
        if not hot:
            continue
        marker = f"alert:{s.id}"
        if marker in already:
            continue
        tick = s.ticker.symbol if s.ticker else "宏观"
        md = (f"⚡ **Mosaic 即时警报** · {tick}\n\n"
              f"**{s.title}**\n\n"
              f"{('So what: ' + s.so_what) if s.so_what else ''}\n"
              f"重要性 {s.materiality}/5 · 情绪 {s.sentiment:+d} · {s.event_type}"
              + (f" · [原文]({s.url})" if s.url else ""))
        ok, err = feishu.send_markdown(db, md)
        db.add(Brief(kind="instant", title=marker, content_md=md, sent=ok, send_error=err))
        db.commit()
        sent += 1
        if sent >= 5:  # never spam
            break
    return sent
