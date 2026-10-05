"""Valuation models. All outputs are MODEL ESTIMATE unless the input ratio itself was uploaded."""

from __future__ import annotations

from typing import Optional

from .provenance import MODEL_ESTIMATE, na_field, make_field


def pe_ratio(price, eps):
    if price is None or eps is None or eps == 0:
        return na_field("P/E = Price / EPS", "How many years of current earnings the price capitalizes.", "Negative or missing EPS → N/A.")
    return make_field(price / eps, MODEL_ESTIMATE, formula="P/E = Price / EPS", interpretation="Higher = more paid per unit of earnings.", limitations="Uses trailing EPS unless specified.")


def forward_pe(price, fwd_eps):
    if price is None or fwd_eps is None or fwd_eps == 0:
        return na_field("Forward P/E = Price / Forward EPS")
    return make_field(price / fwd_eps, MODEL_ESTIMATE, formula="Price / Forward EPS", limitations="Forward EPS is an estimate, not a fact.")


def pb(price, bvps):
    if price is None or bvps is None or bvps == 0:
        return na_field("P/B = Price / Book value per share")
    return make_field(price / bvps, MODEL_ESTIMATE, formula="P/B = Price / BVPS")


def ps(price, sps):
    if price is None or sps is None or sps == 0:
        return na_field("P/S = Price / Sales per share")
    return make_field(price / sps, MODEL_ESTIMATE, formula="P/S = Price / SPS")


def peg(pe, growth):
    if pe is None or growth is None or growth == 0:
        return na_field("PEG = (P/E) / (growth × 100 if growth is decimal)")
    g = growth * 100 if abs(growth) < 1 else growth
    if g == 0:
        return na_field("PEG = P/E / growth%")
    return make_field(pe / g, MODEL_ESTIMATE, formula="PEG = (P/E) / expected growth %", limitations="Sensitive to the growth assumption.")


def ev_ebitda(ev, ebitda):
    if ev is None or ebitda is None or ebitda == 0:
        return na_field("EV/EBITDA")
    return make_field(ev / ebitda, MODEL_ESTIMATE, formula="EV / EBITDA")


def ev_sales(ev, sales):
    if ev is None or sales is None or sales == 0:
        return na_field("EV/Sales")
    return make_field(ev / sales, MODEL_ESTIMATE, formula="EV / Sales")


def fcf_yield(fcf, mkt_cap):
    if fcf is None or mkt_cap is None or mkt_cap == 0:
        return na_field("FCF yield = FCF / Market cap")
    return make_field(fcf / mkt_cap, MODEL_ESTIMATE, formula="FCF / Market cap")


def gordon_growth(d1, k, g):
    formula = "P = D1 / (k − g)"
    if d1 is None or k is None or g is None or k <= g:
        return {
            "value": None,
            "source": MODEL_ESTIMATE,
            "formula": formula,
            "assumptions": {"D1": d1, "k": k, "g": g},
            "limitations": "Requires k > g. MODEL ESTIMATE, not true value.",
            "sensitivity": None,
        }
    p = d1 / (k - g)
    sens = {round(g + dg, 4): d1 / (k - (g + dg)) for dg in (-0.01, 0.0, 0.01) if k > g + dg}
    return {
        "value": p,
        "source": MODEL_ESTIMATE,
        "formula": formula,
        "assumptions": {"D1": d1, "k": k, "g": g},
        "limitations": "Perpetuity assumption is strong. MODEL ESTIMATE, not true value.",
        "sensitivity": sens,
    }


def ddm_finite(dividends: list[float], k: float, terminal: Optional[float] = None) -> dict:
    formula = "P = Σ Dt/(1+k)^t + Terminal/(1+k)^n"
    if not dividends or k is None or k <= -1:
        return {"value": None, "source": MODEL_ESTIMATE, "formula": formula, "assumptions": {}, "limitations": "Need dividend path and discount rate."}
    p = 0.0
    for t, d in enumerate(dividends, 1):
        p += d / ((1 + k) ** t)
    if terminal is not None:
        p += terminal / ((1 + k) ** len(dividends))
    return {
        "value": p,
        "source": MODEL_ESTIMATE,
        "formula": formula,
        "assumptions": {"dividends": dividends, "k": k, "terminal": terminal},
        "limitations": "MODEL ESTIMATE — cash-flow path is an assumption.",
        "sensitivity": None,
    }


def lynch_fair_value(eps, growth):
    """Peter Lynch-style: fair P/E ≈ growth rate (%). FV = EPS × g%."""
    formula = "Lynch FV ≈ EPS × (expected growth %)"
    if eps is None or growth is None:
        return {"value": None, "source": MODEL_ESTIMATE, "formula": formula, "assumptions": {}, "limitations": "Need EPS and growth."}
    g = growth * 100 if abs(growth) < 1 else growth
    fv = eps * g
    return {
        "value": fv,
        "source": MODEL_ESTIMATE,
        "formula": formula,
        "assumptions": {"eps": eps, "growth_pct": g},
        "limitations": "Heuristic, not a DCF. MODEL ESTIMATE, not true value.",
        "sensitivity": {"growth-1": eps * (g - 1), "growth": fv, "growth+1": eps * (g + 1)},
    }


def price_to_lynch(price, fv):
    if price is None or fv is None or fv == 0:
        return na_field("Price / Lynch FV")
    return make_field(price / fv, MODEL_ESTIMATE, formula="Price / Lynch fair value estimate", interpretation=">1 means price above the heuristic.", limitations="MODEL ESTIMATE.")


def valuation_pack(inputs: dict) -> dict:
    price = inputs.get("price")
    eps = inputs.get("eps")
    pe = None
    pe_f = pe_ratio(price, eps)
    if pe_f.available:
        pe = pe_f.value
    lynch = lynch_fair_value(eps, inputs.get("eps_growth") or inputs.get("growth"))
    return {
        "pe": pe_f,
        "forward_pe": forward_pe(price, inputs.get("forward_eps")),
        "pb": pb(price, inputs.get("bvps")),
        "ps": ps(price, inputs.get("sps")),
        "peg": peg(pe, inputs.get("eps_growth") or inputs.get("growth")),
        "ev_ebitda": ev_ebitda(inputs.get("ev"), inputs.get("ebitda")),
        "ev_sales": ev_sales(inputs.get("ev"), inputs.get("sales")),
        "fcf_yield": fcf_yield(inputs.get("fcf"), inputs.get("market_cap")),
        "gordon": gordon_growth(inputs.get("d1"), inputs.get("k"), inputs.get("g")),
        "ddm": ddm_finite(inputs.get("dividends") or [], inputs.get("k") or 0.08, inputs.get("terminal")),
        "lynch": lynch,
        "price_to_lynch": price_to_lynch(price, lynch.get("value")),
    }
