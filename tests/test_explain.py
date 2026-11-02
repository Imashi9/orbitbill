from orbitbill.explain import explain, summarise


def test_template_fallback_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    s = {"total_spend": 100.0, "events": 2, "spend_by_product": {"spot": 100.0},
         "free_km2_used": 0, "anomalies": []}
    text, source = explain(s)
    assert source == "template" and "100.00" in text
