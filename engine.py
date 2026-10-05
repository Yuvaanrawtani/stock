"""Compute security datapoints from session state. No silent imputation."""

from __future__ import annotations

from .bond_analysis import bond_pack, is_bond
from .data_quality import quality_rows
from .etf_analysis import aggregate_holdings_quality, etf_wrapper_fields
from .fundamentals import (
    altman_z_score,
    beneish_m_score,
    classify_growth,
    piotroski_f_score,
    ratios_from_row,
    sustainable_growth_rate,
)
from .metrics import compute_price_metrics
from .portfolio import risk_score_security
from .provenance import DEMO, USER_UPLOADED
from .universe import classify_asset


def datapoints(state: dict) -> dict:
    out = {}
    bench = state["cfg"]["bench"]
    rf = state["cfg"]["rf"]
    lb = state["cfg"]["lb"]
    bpx = _px_list(state, bench)
    ml = (state.get("ml") or {}).get("s") or {}
    for u in state["u"]:
        t = u["t"]
        o = {}
        src = state["src"].get(t, "")
        st = "DEMO" if src == "demo" else "OK"
        at = state["at"].get(t)
        px = _px_list(state, t)
        if px:
            o["last_close"] = {"v": px[-1][1], "st": st, "at": at, "source": DEMO if src == "demo" else USER_UPLOADED}
            c = compute_price_metrics(px, bpx, rf, lb) if bpx else None
            if c:
                for k, v in c.items():
                    if k in ("period", "n_obs"):
                        continue
                    if v is not None and v == v:
                        o[k] = {"v": v, "st": st, "at": at, "source": DEMO if src == "demo" else USER_UPLOADED}
                o["_period"] = c.get("period")
                o["_n"] = c.get("n_obs")
        extras = state.get("ex", {}).get(t) or u.get("x") or {}
        for k, v in extras.items():
            o[k] = {"v": v, "st": "OK", "at": state["at"].get("_u"), "source": USER_UPLOADED}
        if t in ml:
            o["ml_score"] = {
                "v": ml[t],
                "st": "DEMO" if (state.get("ml") or {}).get("demo") else "OK",
                "at": (state.get("ml") or {}).get("at"),
                "source": "MODEL ESTIMATE",
            }
        fin = state.get("fin", {}).get(t)
        if fin and classify_asset(u.get("c", ""), t) == "stock":
            o["_piotroski"] = piotroski_f_score(fin)
            o["_beneish"] = beneish_m_score(fin)
            o["_altman"] = altman_z_score(fin)
            rats = ratios_from_row(fin)
            sgr = sustainable_growth_rate(rats.get("roe"), rats.get("payout_ratio"))
            o["_sgr"] = sgr
            o["_growth"] = classify_growth(rats.get("revenue_growth"), sgr.get("sgr"), None)
        if is_bond(u):
            pm = {k: o[k]["v"] for k in o if isinstance(o[k], dict) and "v" in o[k]}
            o["_bond"] = bond_pack(extras if isinstance(extras, dict) else {}, pm)
        o["_wrapper"] = etf_wrapper_fields(u, extras if isinstance(extras, dict) else {})
        conc = extras.get("top10_concentration") if isinstance(extras, dict) else None
        try:
            conc = float(conc) if conc is not None else None
            if conc and conc > 1.5:
                conc = conc / 100.0
        except (TypeError, ValueError):
            conc = None
        o["_risk"] = risk_score_security(
            o.get("volatility", {}).get("v") if isinstance(o.get("volatility"), dict) else None,
            o.get("max_drawdown", {}).get("v") if isinstance(o.get("max_drawdown"), dict) else None,
            o.get("beta", {}).get("v") if isinstance(o.get("beta"), dict) else None,
            conc,
        )
        out[t] = o
    return out


def holdings_quality_by_etf(state: dict) -> dict:
    by = {}
    for h in state.get("holdings") or []:
        by.setdefault(h["etf"], []).append(h)
    return {etf: aggregate_holdings_quality(hs, state.get("fin") or {}) for etf, hs in by.items()}


def returns_map(state: dict, tickers: list[str]) -> dict[str, list[float]]:
    bench = _px_list(state, state["cfg"]["bench"])
    out = {}
    if not bench:
        return out
    dates = [d for d, _ in bench]
    for t in tickers:
        m = dict(_px_list(state, t))
        last = None
        px = []
        for d in dates:
            if d in m:
                last = m[d]
            px.append(last)
        if px and all(v is not None for v in px):
            out[t] = [px[i] / px[i - 1] - 1 for i in range(1, len(px))]
    return out


def data_mode(state: dict) -> str:
    s = set(state.get("src", {}).values())
    if "upload" in s and "demo" in s:
        return "MIXED (demo + upload)"
    if "demo" in s:
        return "DEMO — synthetic data"
    if "upload" in s:
        return "UPLOADED DATA"
    return "NO DATA"


def _px_list(state: dict, t: str) -> list:
    rows = state.get("px", {}).get(t) or []
    return [(str(d)[:10], float(p)) for d, p in rows]
