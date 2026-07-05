"""Unit tests for the pure logic: momentum, EV, heuristics, dedup."""
from datetime import datetime, timedelta

from app.ai.heuristics import triage_one
from app.services.ideas import scenario_ev
from app.services.ingest import _hash, _norm_title
from app.services.narratives import compute_momentum

NOW = datetime(2026, 7, 6, 12, 0, 0)


class TestMomentum:
    def test_empty(self):
        result = compute_momentum(NOW, [])
        assert result["heat_7d"] == 0
        assert result["momentum_score"] == 0
        assert result["status"] in ("forming", "cooling")

    def test_accelerating(self):
        # heavy recent flow, quiet prior month
        signals = [(NOW - timedelta(days=i % 5), 4, 1) for i in range(10)]
        signals += [(NOW - timedelta(days=20), 2, 0)]
        result = compute_momentum(NOW, signals)
        assert result["status"] == "accelerating"
        assert result["momentum_ratio"] > 1.6
        assert result["momentum_score"] > 30

    def test_cooling(self):
        # active a month ago, silent now
        signals = [(NOW - timedelta(days=10 + i), 3, 0) for i in range(12)]
        result = compute_momentum(NOW, signals)
        assert result["heat_7d"] == 0
        assert result["status"] == "cooling"

    def test_sentiment_shift(self):
        signals = [(NOW - timedelta(days=1), 3, 2), (NOW - timedelta(days=2), 3, 2),
                   (NOW - timedelta(days=15), 3, -2), (NOW - timedelta(days=16), 3, -2)]
        result = compute_momentum(NOW, signals)
        assert result["sentiment_7d"] == 2
        assert result["sentiment_shift"] > 0

    def test_score_bounded(self):
        signals = [(NOW - timedelta(hours=i), 5, 0) for i in range(100)]
        result = compute_momentum(NOW, signals)
        assert result["momentum_score"] <= 100


class TestScenarioEV:
    SCEN = {"bull": {"target": 200, "prob": 0.30},
            "base": {"target": 95, "prob": 0.45},
            "bear": {"target": 25, "prob": 0.25}}

    def test_podcast_numbers(self):
        result = scenario_ev(self.SCEN, 75.0)
        # EV = .3*(200/75-1) + .45*(95/75-1) + .25*(25/75-1) = 0.4533...
        assert abs(result["ev_return"] - 0.4533) < 0.001
        assert result["skew"] > 2  # upside 1.67x vs downside 0.67x

    def test_prob_normalization(self):
        scen = {k: {"target": v["target"], "prob": v["prob"] * 2}
                for k, v in self.SCEN.items()}
        assert scenario_ev(scen, 75.0)["ev_return"] == scenario_ev(self.SCEN, 75.0)["ev_return"]

    def test_bad_input(self):
        assert scenario_ev({}, 75.0) is None
        assert scenario_ev(self.SCEN, None) is None
        assert scenario_ev({"bull": {"target": "x", "prob": 1}}, 75.0) is None


class TestHeuristics:
    def test_mna_is_material(self):
        result = triage_one("Chipmaker agrees to $30bn acquisition of rival")
        assert result["event_type"] == "mna"
        assert result["materiality"] == 5

    def test_guidance_cut(self):
        result = triage_one("Company cuts guidance for fiscal 2027")
        assert result["event_type"] == "guidance"
        assert result["materiality"] == 5

    def test_noise_filtered(self):
        result = triage_one("3 Top Stocks to Buy Now According to Analysts")
        assert result["relevance"] <= 0.2
        assert result["materiality"] == 1

    def test_edgar_8k(self):
        result = triage_one("[8-K] 重大事件公告", source="edgar", form="8-K")
        assert result["materiality"] == 4
        assert result["relevance"] >= 0.8

    def test_sentiment_words(self):
        assert triage_one("Shares surge after record quarter")["sentiment"] >= 1
        assert triage_one("Stock plunges on earnings miss")["sentiment"] <= -1


class TestDedup:
    def test_url_hash_stable(self):
        assert _hash("https://example.com/a-long-article-url-here", "t") == \
               _hash("https://example.com/a-long-article-url-here", "different title")

    def test_short_url_falls_back_to_title(self):
        a = _hash("", "NVIDIA beats Q2 estimates!")
        b = _hash("", "NVIDIA beats Q2 estimates")
        assert a == b  # punctuation-insensitive title normalization

    def test_norm_title_cjk(self):
        assert _norm_title("腾讯发布Q2财报:超预期!") == _norm_title("腾讯发布Q2财报 超预期")
