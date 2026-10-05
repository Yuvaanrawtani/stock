"""Data-quality scoring. Demo data can never be HIGH CONFIDENCE."""

from __future__ import annotations

from datetime import datetime, timezone

from .universe import classify_asset, expected_metric_keys


def _stale(ts: str | None) -> bool:
    if not ts:
        return True
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).total_seconds() > 7 * 86400
    except Exception:
        return True


def quality_rows(universe: list[dict], datapoints: dict, src: dict) -> dict:
    rows = []
    for u in universe:
        kind = classify_asset(u.get("c", ""), u.get("t", ""))
        keys = expected_metric_keys(kind)
        o = datapoints.get(u["t"], {})
        miss = [k for k in keys if k not in o]
        p = 1 - len(miss) / len(keys) if keys else 0
        at = None
        demo = src.get(u["t"]) == "demo" or any(
            (o[k].get("st") == "DEMO") if isinstance(o.get(k), dict) else False for k in o
        )
        ats = []
        for v in o.values():
            if isinstance(v, dict) and v.get("at"):
                ats.append(v["at"])
        at = sorted(ats)[-1] if ats else None
        stale = _stale(at)
        label = _label(p, stale, demo)
        rows.append({"t": u["t"], "p": p, "miss": miss, "stale": stale, "demo": demo, "l": label, "wins": u.get("wins_approved", "UNKNOWN")})
    avg = sum(r["p"] for r in rows) / len(rows) if rows else 0
    overall = _label(avg, any(r["stale"] for r in rows), any(r["demo"] for r in rows)) if rows else "INSUFFICIENT DATA"
    return {"rows": rows, "avg": avg, "all": overall}


def _label(p, stale, demo):
    if demo:
        return "PARTIAL DATA" if p >= 0.5 else "INSUFFICIENT DATA"
    if p >= 0.9 and not stale and not demo:
        return "HIGH CONFIDENCE"
    if p >= 0.5:
        return "PARTIAL DATA"
    return "INSUFFICIENT DATA"
