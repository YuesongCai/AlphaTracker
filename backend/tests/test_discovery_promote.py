"""Promote flow: candidate -> tracked narrative + coverage + evidence links."""
import os
import tempfile

os.environ["MOSAIC_DATA_DIR"] = tempfile.mkdtemp(prefix="mosaic-test-")

from app.db import init_db, session_scope  # noqa: E402
from app.models import (Narrative, NarrativeCandidate, Signal,  # noqa: E402
                        SignalNarrative, Ticker)
from app.services import discovery  # noqa: E402


def test_promote_creates_narrative_coverage_and_links():
    init_db()
    with session_scope() as db:
        sig = Signal(source="rss", lane="markets", title="OPEC+ raises output",
                     url="https://x/1", url_hash="h1", publisher="WSJ")
        db.add(sig)
        db.flush()
        cand = NarrativeCandidate(
            cluster_key="OPEC", title="OPEC × 增产周期:油价的下行压力有多持久?",
            question="增产是趋势还是一次性?", stance_bull="份额策略",
            stance_bear="需求疲软", ticker_symbols=["XOM"], keywords=["OPEC output"],
            evidence_ids=[sig.id], score=9.9,
        )
        db.add(cand)
        db.commit()

        narrative = discovery.promote(db, cand)

        assert cand.status == "promoted"
        assert db.query(Narrative).filter_by(id=narrative.id).one().title.startswith("OPEC")
        # discovered ticker auto-joins coverage
        xom = db.query(Ticker).filter_by(symbol="XOM").one()
        assert xom is not None
        # evidence signal linked to the new narrative
        link = db.query(SignalNarrative).filter_by(
            signal_id=sig.id, narrative_id=narrative.id).one_or_none()
        assert link is not None
        # dismissed key suppression works
        cand2 = NarrativeCandidate(cluster_key="MEME", title="x", evidence_ids=[])
        db.add(cand2)
        db.commit()
        discovery.dismiss(db, cand2)
        assert "MEME" in discovery._tracked_keys(db)
