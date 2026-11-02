from orbitbill.anomaly import detect
from orbitbill.credit_control import ChargingEngine
from orbitbill.simulator import generate


def run(**kw):
    eng = ChargingEngine()
    eng.open_account("acme-maritime", 10_000_000)
    for e in generate(**kw):
        eng.charge(e)
    return eng.accounts["acme-maritime"].ledger


def test_spike_day_detected():
    found = detect(run(inject_spike_day=21))
    assert any(a.day == 21 for a in found)


def test_no_spike_no_alarm():
    assert detect(run(inject_spike_day=None)) == []


def test_duplicates_billed_once():
    events = generate(duplicates=3)
    eng = ChargingEngine()
    eng.open_account("acme-maritime", 10_000_000)
    billed = [eng.charge(e) for e in events]
    assert sum(b is None for b in billed) == 3
