"""Plain-language bill explanation. Uses Claude when ANTHROPIC_API_KEY is set, else a template."""
from __future__ import annotations

import os
from collections import defaultdict

from .anomaly import Anomaly
from .models import LedgerEntry

MODEL = "claude-sonnet-5-5"


def summarise(ledger: list[LedgerEntry], anomalies: list[Anomaly]) -> dict:
    by_product: dict[str, float] = defaultdict(float)
    for e in ledger:
        by_product[e.product.value] += e.charged
    total = round(sum(by_product.values()), 2)
    return {
        "total_spend": total,
        "events": len(ledger),
        "spend_by_product": {k: round(v, 2) for k, v in sorted(by_product.items(), key=lambda kv: -kv[1])},
        "free_km2_used": round(sum(e.free_km2_used for e in ledger), 1),
        "anomalies": [{"day": a.day, "spend": a.spend, "events": a.events, "reason": a.reason}
                      for a in anomalies],
    }


def _template(s: dict) -> str:
    if not s["events"]:
        return "No usage has been billed yet."
    top, top_amt = next(iter(s["spend_by_product"].items()))
    lines = [f"You were charged {s['total_spend']:,.2f} EUR across {s['events']} billed requests. "
             f"Most of it ({top_amt / s['total_spend']:.0%}) came from {top} products."]
    if s["free_km2_used"]:
        lines.append(f"Your free archive allowance covered {s['free_km2_used']:g} km2.")
    for a in s["anomalies"]:
        lines.append(f"Check day {a['day']}: {a['events']} requests cost {a['spend']:,.2f} EUR; {a['reason']}. "
                     "This looks like a runaway script or a duplicated feed.")
    if not s["anomalies"]:
        lines.append("No unusual usage was detected.")
    return " ".join(lines)


def explain(summary: dict, question: str = "Explain my bill") -> tuple[str, str]:
    """Return (answer, source) where source is 'claude' or 'template'."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _template(summary), "template"
    try:
        import anthropic
        msg = anthropic.Anthropic().messages.create(
            model=MODEL, max_tokens=400,
            system=("You explain usage-based bills for a satellite imagery service to a non-technical customer. "
                    "Use only the JSON provided, never invent numbers, be concise (under 120 words), "
                    "and call out anomalies with a suggested action."),
            messages=[{"role": "user", "content": f"Bill data: {summary}\n\nQuestion: {question}"}])
        return msg.content[0].text, "claude"
    except Exception:  # network/key problems must not break billing
        return _template(summary), "template"
