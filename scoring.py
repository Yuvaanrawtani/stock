"""Transparent scoring + screening funnel + rejection log. Score ≠ BUY."""

from __future__ import annotations

import json
from pathlib import Path

WEIGHTS_PATH = Path(__file__).resolve().parents[1] / "config" / "scoring_weights.json"

DEFAULT_WEIGHTS = json.loads(WEIGHTS_PATH.read_text()) if WEIGHTS_PATH.exists() else {
    "thesis_strength": 0.12,
    "thesis_durability": 0.10,
    "market_tension": 0.08,
    "catalyst": 0.08,
    "fundamental_quality": 0.12,
    "valuation": 0.10,
    "risk": 0.10,
    "diversification": 0.06,
    "scenario_resilience": 0.08,
    "laura_alignment": 0.08,
    "funding_compatibility": 0.05,
    "data_confidence": 0.03,
}

LOW_BETTER = {"risk"}


def weighted_score(parts: dict[str, float | None], weights: dict[str, float] | None = None) -> dict:
    w = dict(weights or DEFAULT_WEIGHTS)
    rows = []
    tw = 0.0
    total = 0.0
    miss = []
    for k, wt in w.items():
        v = parts.get(k)
        if v is None or wt <= 0:
            miss.append(k)
            continue
        n = float(v)
        if k in LOW_BETTER:
            n = 100 - n
        n = min(100.0, max(0.0, n))
        rows.append({"k": k, "raw": v, "n": n, "w": wt})
        tw += wt
    for r in rows:
        r["wn"] = r["w"] / tw if tw else 0
        r["c"] = r["n"] * r["wn"]
        total += r["c"]
    return {
        "score": total if rows else None,
        "rows": rows,
        "missing": miss,
        "weights": w,
        "note": "Weights are visible and editable. Overall score is not a BUY decision.",
    }


def min_max_rank(values: dict[str, float], low_better: bool = False) -> dict[str, float]:
    xs = [v for v in values.values() if v is not None]
    if not xs:
        return {k: None for k in values}
    lo, hi = min(xs), max(xs)
    out = {}
    for k, v in values.items():
        if v is None or hi == lo:
            out[k] = 50.0 if v is not None else None
        else:
            n = (v - lo) / (hi - lo) * 100
            out[k] = 100 - n if low_better else n
    return out


FUNNEL_STAGES = [
    "WInS universe",
    "Country / Geography",
    "Industry / Theme",
    "ETF/Security quality",
    "Valuation",
    "Risk",
    "Underlying holdings quality",
    "Thesis Tension",
    "Scenario resilience",
    "Laura alignment",
    "Portfolio construction",
    "Funding test",
    "Human review",
]


def run_funnel(securities: list[dict], reject_fn) -> dict:
    """reject_fn(stage, sec) -> reason or None."""
    remaining = list(securities)
    stages = []
    log = []
    for stage in FUNNEL_STAGES:
        start = len(remaining)
        keep = []
        for sec in remaining:
            reason = reject_fn(stage, sec)
            if reason:
                log.append(
                    {
                        "ticker": sec.get("t"),
                        "stage": stage,
                        "reason": reason,
                        "data_used": sec.get("data_used", "see metrics"),
                        "override": sec.get("override"),
                    }
                )
            else:
                keep.append(sec)
        stages.append({"n": stage, "a": start, "r": start - len(keep), "remaining": len(keep)})
        remaining = keep
    return {"st": stages, "L": remaining, "log": log}
