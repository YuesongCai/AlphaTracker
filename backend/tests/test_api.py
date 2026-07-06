"""API smoke tests against a temp database (no network, no scheduler)."""
import os
import tempfile

os.environ["MOSAIC_NO_SCHED"] = "1"
os.environ["MOSAIC_DEMO"] = "1"  # these tests exercise the demo fixture set
os.environ["MOSAIC_DATA_DIR"] = tempfile.mkdtemp(prefix="mosaic-test-")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_healthz():
    with client:
        assert client.get("/healthz").json()["ok"] is True


def test_seeded_dashboard():
    with client:
        data = client.get("/api/dashboard").json()
        assert len(data["tickers"]) == 10
        assert data["pipeline_counts"].get("thesis") == 1
        assert data["llm"]["backend"] in ("api", "cli", "off")


def test_narrative_crud_and_momentum_fields():
    with client:
        listed = client.get("/api/narratives").json()
        assert len(listed) >= 6
        assert {"momentum_score", "heat_7d", "status"} <= set(listed[0].keys())

        created = client.post("/api/narratives", json={
            "title": "测试叙事", "question": "?", "keywords": ["test keyword"],
        }).json()
        detail = client.get(f"/api/narratives/{created['id']}").json()
        assert detail["title"] == "测试叙事"
        assert "timeline" in detail
        assert client.delete(f"/api/narratives/{created['id']}").json()["ok"]


def test_idea_pipeline_flow():
    with client:
        ideas = client.get("/api/ideas").json()
        uber = next(i for i in ideas if i["ticker"]["symbol"] == "UBER")
        assert uber["stage"] == "thesis"

        detail = client.get(f"/api/ideas/{uber['id']}").json()
        assert len(detail["drivers"]) == 3
        assert detail["thesis"]["kill_criteria"]
        assert len(detail["journal"]) >= 4

        # manual idea + advance + kill leaves a journal trail
        tickers = client.get("/api/tickers").json()
        nvda = next(t for t in tickers if t["symbol"] == "NVDA")
        idea = client.post("/api/ideas", json={
            "ticker_id": nvda["id"], "title": "NVDA 测试想法"}).json()
        advanced = client.post(f"/api/ideas/{idea['id']}/advance", json={"note": "x"}).json()
        assert advanced["stage"] == "hypothesis"
        killed = client.post(f"/api/ideas/{idea['id']}/kill", json={"note": "不值得"}).json()
        assert killed["stage"] == "killed"
        journal = client.get(f"/api/ideas/{idea['id']}").json()["journal"]
        assert any("否决" in j["content"] for j in journal)


def test_manual_signal_gets_triaged():
    with client:
        created = client.post("/api/signals", json={
            "title": "Company cuts guidance for 2027", "url": "https://example.com/x",
        }).json()
        assert created["triaged"] is True
        assert created["event_type"] == "guidance"
        assert created["materiality"] == 5


def test_settings_roundtrip_masks_key():
    with client:
        client.put("/api/settings", json={"settings": {"llm.api_key": "sk-test-123"}})
        settings = client.get("/api/settings").json()["settings"]
        assert settings["llm.api_key"] == "••••••••"
        # masked value round-trip must not overwrite the stored key
        client.put("/api/settings", json={"settings": {"llm.api_key": "••••••••"}})
        status = client.get("/api/llm/status").json()
        assert status["api_key_set"] is True
