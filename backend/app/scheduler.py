"""Background jobs: ingest cycles + morning/evening briefs (Beijing time)."""
from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import config
from .db import get_setting, session_scope
from .models import OpsLog

log = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone=str(config.BEIJING))


def _safe(job_name: str, fn) -> None:
    """Run a job with its own session; failures land in ops_log, never crash."""
    try:
        with session_scope() as db:
            fn(db)
    except Exception as exc:  # noqa: BLE001 - scheduler must survive anything
        log.exception("job %s failed", job_name)
        try:
            with session_scope() as db:
                db.add(OpsLog(job=job_name, status="error", detail=str(exc)[:500]))
        except Exception:  # noqa: BLE001
            pass


def _job_ingest_news() -> None:
    from .services import brief, ingest, narratives

    def run(db):
        ingest.ingest_news(db)
        narratives.refresh_all(db)
        brief.instant_alerts(db)

    _safe("ingest_news", run)


def _job_refresh_quotes() -> None:
    from .services import ingest
    _safe("refresh_quotes", ingest.refresh_quotes)


def _job_ingest_slow() -> None:
    from .services import brief, ingest, narratives

    def run(db):
        ingest.ingest_slow(db)
        narratives.refresh_all(db)
        brief.instant_alerts(db)

    _safe("ingest_slow", run)


def _job_brief(kind: str) -> None:
    from .services import brief
    _safe(f"brief_{kind}", lambda db: brief.generate_brief(db, kind=kind, send=True))


def _parse_hhmm(value: str, fallback: tuple[int, int]) -> tuple[int, int]:
    try:
        hour, minute = value.strip().split(":")
        return max(0, min(23, int(hour))), max(0, min(59, int(minute)))
    except (ValueError, AttributeError):
        return fallback


def reschedule_briefs() -> None:
    """(Re)apply brief cron times from settings; called on settings save."""
    with session_scope() as db:
        morning = _parse_hhmm(get_setting(db, "brief.morning", "08:00"), (8, 0))
        evening = _parse_hhmm(get_setting(db, "brief.evening", "19:30"), (19, 30))
    for job_id, (hour, minute), kind in (
        ("brief_morning", morning, "morning"),
        ("brief_evening", evening, "evening"),
    ):
        trigger = CronTrigger(hour=hour, minute=minute, timezone=str(config.BEIJING))
        if scheduler.get_job(job_id):
            scheduler.reschedule_job(job_id, trigger=trigger)
        else:
            scheduler.add_job(lambda k=kind: _job_brief(k), trigger,
                              id=job_id, name=job_id)


def start() -> None:
    with session_scope() as db:
        news_min = int(get_setting(db, "ingest.news_minutes", 20))
        quote_min = int(get_setting(db, "ingest.quotes_minutes", 30))
        slow_min = int(get_setting(db, "ingest.slow_minutes", 60))

    scheduler.add_job(_job_ingest_news, "interval", minutes=max(news_min, 5),
                      id="ingest_news", name="ingest_news", jitter=60)
    scheduler.add_job(_job_refresh_quotes, "interval", minutes=max(quote_min, 5),
                      id="refresh_quotes", name="refresh_quotes", jitter=60)
    scheduler.add_job(_job_ingest_slow, "interval", minutes=max(slow_min, 15),
                      id="ingest_slow", name="ingest_slow", jitter=120)
    reschedule_briefs()

    # Fresh install: pull data right away instead of waiting for the first tick.
    with session_scope() as db:
        from .models import Signal
        is_empty = db.query(Signal.id).first() is None
    if is_empty:
        def _first_boot() -> None:
            _job_refresh_quotes()
            _job_ingest_news()
            _job_ingest_slow()
        scheduler.add_job(_first_boot, "date", id="first_boot", name="first_boot")

    scheduler.start()
    log.info("scheduler started (news=%sm quotes=%sm slow=%sm)",
             news_min, quote_min, slow_min)


def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def job_overview() -> list[dict]:
    if not scheduler.running:
        return []
    out = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        out.append({
            "id": job.id,
            "next_run": next_run.astimezone(config.BEIJING).strftime("%m-%d %H:%M")
            if next_run else None,
        })
    return out
