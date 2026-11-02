"""Usage anomaly detection: IsolationForest on per-day aggregates, gated by a robust z-score."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest

from .models import LedgerEntry

FEATURES = ["events", "area_km2", "spend", "rush_share"]


@dataclass
class Anomaly:
    day: int
    spend: float
    events: int
    reason: str
    score: float


def daily_features(ledger: list[LedgerEntry]) -> dict[int, list[float]]:
    days: dict[int, list[LedgerEntry]] = {}
    for e in ledger:
        days.setdefault(int(e.timestamp // 24), []).append(e)
    out = {}
    for d, es in days.items():
        rush = sum(1 for e in es if "rush" in e.note)
        out[d] = [len(es), sum(e.area_km2 for e in es), sum(e.charged for e in es), rush / len(es)]
    return out


def _robust_z(x: np.ndarray) -> np.ndarray:
    med = np.median(x, axis=0)
    mad = np.median(np.abs(x - med), axis=0) * 1.4826
    mad[mad == 0] = 1.0
    return (x - med) / mad


def detect(ledger: list[LedgerEntry], z_gate: float = 6.0, seed: int = 0) -> list[Anomaly]:
    feats = daily_features(ledger)
    if len(feats) < 8:
        return []
    days = sorted(feats)
    x = np.array([feats[d] for d in days])
    forest = IsolationForest(contamination="auto", random_state=seed).fit(x)
    scores = -forest.score_samples(x)           # higher = more anomalous
    flagged = forest.predict(x) == -1
    z = _robust_z(x)
    found = []
    for i, d in enumerate(days):
        # the forest proposes, the z-score confirms: keeps false alarms low on small data
        if flagged[i] and z[i].max() >= z_gate:
            worst = int(np.argmax(z[i]))
            reason = (f"{FEATURES[worst]} is {z[i][worst]:.1f} robust-sigma above the account's normal "
                      f"({x[i][worst]:.1f} vs median {np.median(x[:, worst]):.1f})")
            found.append(Anomaly(d, round(x[i][2], 2), int(x[i][0]), reason, round(float(scores[i]), 3)))
    return sorted(found, key=lambda a: -a.score)
