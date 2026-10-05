"""WInS virtual trading planner. No real orders."""

from __future__ import annotations

from .provenance import utc_now


def new_trade(**kwargs) -> dict:
    t = {
        "date": kwargs.get("date") or utc_now()[:10],
        "ticker": (kwargs.get("ticker") or "").upper(),
        "side": kwargs.get("side") or "buy",
        "quantity": kwargs.get("quantity"),
        "price": kwargs.get("price"),
        "position_value": None,
        "portfolio_pct": kwargs.get("portfolio_pct"),
        "thesis": kwargs.get("thesis") or "",
        "reason": kwargs.get("reason") or "",
        "catalyst": kwargs.get("catalyst") or "",
        "thesis_half_life": kwargs.get("thesis_half_life") or "",
        "invalidation": kwargs.get("invalidation") or "",
        "risk": kwargs.get("risk") or "",
        "laura_role": kwargs.get("laura_role") or "",
        "expected_impact": kwargs.get("expected_impact") or "",
        "evidence": kwargs.get("evidence") or "",
        "created": utc_now(),
        "virtual": True,
    }
    q, p = t["quantity"], t["price"]
    try:
        t["position_value"] = float(q) * float(p)
    except (TypeError, ValueError):
        t["position_value"] = None
    return t
