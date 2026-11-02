from fastapi.testclient import TestClient

from orbitbill.api import app

client = TestClient(app)


def test_summary_flags_spike():
    client.post("/api/simulate?spike=true")
    s = client.get("/api/summary").json()
    assert any(a["day"] == 21 for a in s["anomalies"])


def test_task_reserves_then_commits():
    client.post("/api/simulate?spike=false")
    before = client.get("/api/summary").json()["balance"]
    r = client.post("/api/task", json={"product": "spot", "area_km2": 10}).json()
    assert [s["step"] for s in r["steps"]] == ["reserve", "commit"]
    assert client.get("/api/summary").json()["balance"] == round(before - r["charged"], 2)


def test_insufficient_balance_returns_402():
    client.post("/api/simulate?spike=false")
    codes = [client.post("/api/task", json={"product": "spot", "area_km2": 5000, "rush": True}).status_code
             for _ in range(4)]
    assert 402 in codes


def test_explain_endpoint(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post("/api/explain", json={}).json()
    assert r["source"] == "template" and r["answer"]


def test_live_request_stays_inside_simulation_days():
    client.post("/api/simulate?spike=false")
    client.post("/api/task", json={"product": "spot", "area_km2": 10})
    days = [d["day"] for d in client.get("/api/summary").json()["daily_spend"]]
    assert max(days) < 60
