from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .anomaly import detect
from .credit_control import ChargingEngine, InsufficientBalance
from .explain import explain, summarise
from .models import Product, UsageEvent
from .simulator import generate

ACCOUNT = "acme-maritime"
START_BALANCE = 250_000.0
STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="OrbitBill", description="AI-assisted convergent charging for satellite imagery (simulated)")
engine = ChargingEngine()
_counter = {"n": 0}


class TaskRequest(BaseModel):
    product: Product
    area_km2: float = Field(gt=0, le=5000)
    resolution_m: float = Field(1.0, gt=0)
    rush: bool = False


def _reset(spike: bool = True) -> dict:
    global engine
    engine = ChargingEngine()
    engine.open_account(ACCOUNT, START_BALANCE)
    billed = dups = 0
    for e in generate(ACCOUNT, inject_spike_day=21 if spike else None):
        if engine.charge(e):
            billed += 1
        else:
            dups += 1
    return {"billed": billed, "duplicates_dropped": dups}


_reset()


@app.post("/api/simulate")
def simulate(spike: bool = True):
    return _reset(spike)


@app.get("/api/summary")
def summary():
    acct = engine.accounts[ACCOUNT]
    anomalies = detect(acct.ledger)
    s = summarise(acct.ledger, anomalies)
    daily: dict[int, float] = {}
    for e in acct.ledger:
        daily[int(e.timestamp // 24)] = daily.get(int(e.timestamp // 24), 0) + e.charged
    return {**s, "balance": acct.balance, "reserved": acct.reserved, "available": acct.available,
            "free_archive_left": acct.free_archive_left,
            "daily_spend": [{"day": d, "spend": round(v, 2)} for d, v in sorted(daily.items())],
            "recent": [{"id": e.event_id, "note": e.note, "charged": e.charged} for e in acct.ledger[-8:][::-1]]}


@app.post("/api/task")
def task(req: TaskRequest):
    """Request a new acquisition: reserve funds, 'deliver', then commit."""
    _counter["n"] += 1
    ev = UsageEvent(f"live-{_counter['n']:05d}", ACCOUNT, req.product, req.area_km2,
                    req.resolution_m, req.rush, time.time())
    try:
        res = engine.reserve(ev)
    except InsufficientBalance as exc:
        raise HTTPException(402, str(exc))
    steps = [{"step": "reserve", "amount": res.amount, "available": engine.accounts[ACCOUNT].available}]
    entry = engine.commit(ev.event_id)
    steps.append({"step": "commit", "amount": entry.charged, "available": engine.accounts[ACCOUNT].available})
    return {"event_id": ev.event_id, "note": entry.note, "charged": entry.charged, "steps": steps}


class Question(BaseModel):
    question: str = "Explain my bill"


@app.post("/api/explain")
def explain_bill(q: Question):
    acct = engine.accounts[ACCOUNT]
    s = summarise(acct.ledger, detect(acct.ledger))
    answer, source = explain(s, q.question)
    return {"answer": answer, "source": source}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
