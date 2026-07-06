"""Discovery engine: cluster scoring + entity canonicalization + heuristic entities."""
from datetime import datetime, timedelta

from app.ai.heuristics import extract_entities
from app.services.discovery import STOPLIST, canon, score_cluster

NOW = datetime(2026, 7, 6, 12, 0, 0)


def _sig(hours_ago: float, materiality: int = 3, publisher: str = "WSJ",
         lane: str = "markets") -> dict:
    return {"published_at": NOW - timedelta(hours=hours_ago),
            "materiality": materiality, "publisher": publisher, "lane": lane}


def test_breadth_multiplies_score():
    same_pub = [_sig(2, 3, "WSJ"), _sig(3, 3, "WSJ"), _sig(4, 3, "WSJ")]
    multi_pub = [_sig(2, 3, "WSJ"), _sig(3, 3, "CNBC"), _sig(4, 3, "金十数据")]
    low = score_cluster(same_pub, baseline_count=0, now=NOW)
    high = score_cluster(multi_pub, baseline_count=0, now=NOW)
    assert high["score"] > low["score"]
    assert high["breadth_pub"] == 3 and low["breadth_pub"] == 1


def test_cross_lane_boost():
    one_lane = [_sig(2, 3, "WSJ", "markets"), _sig(3, 3, "CNBC", "markets")]
    two_lane = [_sig(2, 3, "WSJ", "markets"), _sig(3, 3, "金十数据", "macro")]
    assert (score_cluster(two_lane, 0, NOW)["score"]
            > score_cluster(one_lane, 0, NOW)["score"])


def test_novelty_boost_and_flag():
    signals = [_sig(2), _sig(5), _sig(9)]
    fresh = score_cluster(signals, baseline_count=0, now=NOW)
    chronic = score_cluster(signals, baseline_count=25, now=NOW)
    assert fresh["novelty"] is True and chronic["novelty"] is False
    assert fresh["score"] > chronic["score"]


def test_recency_decay():
    recent = [_sig(1), _sig(2), _sig(3)]
    stale = [_sig(40), _sig(44), _sig(47)]
    assert (score_cluster(recent, 0, NOW)["heat"]
            > score_cluster(stale, 0, NOW)["heat"] * 2)


def test_canon_and_stoplist():
    assert canon("nvda") == "NVDA"
    assert canon(" $TSLA ") == "TSLA"
    assert canon("AI capex") == "AI capex"  # multiword themes keep casing
    assert "AI" in STOPLIST and "STOCKS" in STOPLIST


def test_extract_entities_heuristic():
    known = {"NVDA", "0700.HK", "UBER"}
    ents = extract_entities("Nvidia and $AMD rally as 腾讯 unveils AI plan", known)
    assert "NVDA" in ents and "AMD" in ents and "0700.HK" in ents
    # word boundary: UBER must not fire on 'Uberto' — but plain uber does
    assert "UBER" not in extract_entities("Uberto Pasolini wins award", known)
    assert "UBER" in extract_entities("Uber expands robotaxi deal", known)
