"""ORM models — the object model mirrors PRODUCT.md section 3."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)  # json-encoded


class Ticker(Base):
    __tablename__ = "tickers"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    market: Mapped[str] = mapped_column(String(10), default="US")  # US | HK
    sector: Mapped[str] = mapped_column(String(80), default="")
    news_query: Mapped[str] = mapped_column(String(200), default="")
    cik: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # EDGAR
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # quote snapshot
    last_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    quote_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_earnings: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD

    # stocktwits snapshot
    st_bull_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0..1
    st_watchers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    st_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    signals: Mapped[list["Signal"]] = relationship(back_populates="ticker")
    ideas: Mapped[list["Idea"]] = relationship(back_populates="ticker")


class Signal(Base):
    """One piece of incoming information: news, filing, social snapshot, manual note."""

    __tablename__ = "signals"
    __table_args__ = (UniqueConstraint("url_hash", name="uq_signal_urlhash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tickers.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(20), index=True)
    # google_news|rss|jin10|hn|edgar|edgar_stream|stocktwits|manual
    lane: Mapped[str] = mapped_column(String(12), default="company", index=True)
    # company | markets | macro | tech | filings
    publisher: Mapped[str] = mapped_column(String(120), default="")
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, default="")
    url_hash: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # triage output
    triaged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    triage_engine: Mapped[str] = mapped_column(String(20), default="")  # api|cli|heuristic|seed
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    materiality: Mapped[int] = mapped_column(Integer, default=0, index=True)  # 1..5
    sentiment: Mapped[int] = mapped_column(Integer, default=0)  # -2..2
    event_type: Mapped[str] = mapped_column(String(20), default="other", index=True)
    so_what: Mapped[str] = mapped_column(Text, default="")
    variant: Mapped[bool] = mapped_column(Boolean, default=False)
    entities: Mapped[Any] = mapped_column(JSON, default=list)
    # canonical tags for clustering: tickers ("NVDA") + themes ("AI capex")

    ticker: Mapped[Optional[Ticker]] = relationship(back_populates="signals")
    narrative_links: Mapped[list["SignalNarrative"]] = relationship(
        back_populates="signal", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="signal")


class Narrative(Base):
    """A debated question the market is trading on."""

    __tablename__ = "narratives"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    question: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    stance_bull: Mapped[str] = mapped_column(Text, default="")
    stance_bear: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(10), default="company")  # company | theme
    status: Mapped[str] = mapped_column(String(15), default="forming", index=True)
    # forming | accelerating | cooling | resolved
    keywords: Mapped[Any] = mapped_column(JSON, default=list)  # extra news queries
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # cached momentum (recomputed after each ingest)
    heat_7d: Mapped[float] = mapped_column(Float, default=0.0)
    momentum_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    momentum_score: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_7d: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_shift: Mapped[float] = mapped_column(Float, default=0.0)

    ticker_links: Mapped[list["NarrativeTicker"]] = relationship(
        back_populates="narrative", cascade="all, delete-orphan"
    )
    signal_links: Mapped[list["SignalNarrative"]] = relationship(
        back_populates="narrative", cascade="all, delete-orphan"
    )


class NarrativeTicker(Base):
    __tablename__ = "narrative_tickers"
    __table_args__ = (UniqueConstraint("narrative_id", "ticker_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    narrative_id: Mapped[int] = mapped_column(ForeignKey("narratives.id"), index=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id"), index=True)

    narrative: Mapped[Narrative] = relationship(back_populates="ticker_links")
    ticker: Mapped[Ticker] = relationship()


class SignalNarrative(Base):
    __tablename__ = "signal_narratives"
    __table_args__ = (UniqueConstraint("signal_id", "narrative_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), index=True)
    narrative_id: Mapped[int] = mapped_column(ForeignKey("narratives.id"), index=True)

    signal: Mapped[Signal] = relationship(back_populates="narrative_links")
    narrative: Mapped[Narrative] = relationship(back_populates="signal_links")


class NarrativeCandidate(Base):
    """An emerging-narrative candidate surfaced by the discovery engine.

    The user promotes it into a tracked Narrative or dismisses it —
    the engine feeds narratives to the analyst, not the other way round.
    """

    __tablename__ = "narrative_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_key: Mapped[str] = mapped_column(String(80), index=True)  # canonical entity
    title: Mapped[str] = mapped_column(String(200), default="")
    question: Mapped[str] = mapped_column(Text, default="")
    why_now: Mapped[str] = mapped_column(Text, default="")
    driver_question: Mapped[str] = mapped_column(Text, default="")
    stance_bull: Mapped[str] = mapped_column(Text, default="")
    stance_bear: Mapped[str] = mapped_column(Text, default="")
    ticker_symbols: Mapped[Any] = mapped_column(JSON, default=list)
    keywords: Mapped[Any] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[Any] = mapped_column(JSON, default=list)  # signal ids
    score: Mapped[float] = mapped_column(Float, default=0.0)
    heat: Mapped[float] = mapped_column(Float, default=0.0)
    breadth_pub: Mapped[int] = mapped_column(Integer, default=0)
    breadth_lane: Mapped[int] = mapped_column(Integer, default=0)
    novelty: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    # pending | promoted | dismissed | ai_skip
    engine: Mapped[str] = mapped_column(String(20), default="heuristic")
    ai_rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Idea(Base):
    """Hunch -> Hypothesis -> Thesis pipeline item."""

    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    direction: Mapped[str] = mapped_column(String(10), default="long")  # long | short | watch
    stage: Mapped[str] = mapped_column(String(12), default="hunch", index=True)
    # hunch | hypothesis | thesis | killed
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    sniff: Mapped[Any] = mapped_column(JSON, default=dict)       # sniff test report
    hypothesis: Mapped[Any] = mapped_column(JSON, default=dict)  # propositions / confirm / refute
    research_plan: Mapped[Any] = mapped_column(JSON, default=dict)
    thesis: Mapped[Any] = mapped_column(JSON, default=dict)      # scenarios / variant view / kill criteria
    notes: Mapped[str] = mapped_column(Text, default="")

    ticker: Mapped[Ticker] = relationship(back_populates="ideas")
    drivers: Mapped[list["Driver"]] = relationship(
        back_populates="idea", cascade="all, delete-orphan"
    )
    journal: Mapped[list["JournalEntry"]] = relationship(
        back_populates="idea", cascade="all, delete-orphan"
    )


class Driver(Base):
    """A key driver of an idea, with signposts to monitor."""

    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    signposts: Mapped[Any] = mapped_column(JSON, default=list)
    # [{text, direction: confirm|refute, hit: bool}]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    idea: Mapped[Idea] = relationship(back_populates="drivers")
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="driver", cascade="all, delete-orphan"
    )


class Evidence(Base):
    """A signal mapped onto a driver with a stance."""

    __tablename__ = "evidence"
    __table_args__ = (UniqueConstraint("driver_id", "signal_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), index=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), index=True)
    stance: Mapped[str] = mapped_column(String(10), default="neutral")  # confirm|neutral|refute
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    driver: Mapped[Driver] = relationship(back_populates="evidence")
    signal: Mapped[Signal] = relationship(back_populates="evidence")


class JournalEntry(Base):
    """Process journal: stage changes, Bayesian belief updates, notes."""

    __tablename__ = "journal"

    id: Mapped[int] = mapped_column(primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), index=True)
    entry_type: Mapped[str] = mapped_column(String(20), default="note")
    # stage_change | belief_update | note | ai_flag
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    idea: Mapped[Idea] = relationship(back_populates="journal")


class Brief(Base):
    """Generated briefs and instant alerts (also the Feishu send log)."""

    __tablename__ = "briefs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)  # morning|evening|instant|manual
    title: Mapped[str] = mapped_column(String(200), default="")
    content_md: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    send_error: Mapped[str] = mapped_column(Text, default="")


class OpsLog(Base):
    """Last-run bookkeeping for scheduler jobs (shown in settings page)."""

    __tablename__ = "ops_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    job: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(10), default="ok")  # ok | error
    detail: Mapped[str] = mapped_column(Text, default="")
    ran_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
