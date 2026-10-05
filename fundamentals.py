"""Piotroski, Beneish, Altman, ratios, SGR. Company-level only — never assigned as an ETF score."""

from __future__ import annotations

from typing import Any, Optional


def _f(x) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v:
        return None
    return v


def piotroski_f_score(row: dict) -> dict:
    """Nine binary signals. Missing inputs => that signal is N/A, not assumed 0."""
    signals = {}
    roa = _f(row.get("roa"))
    cfo = _f(row.get("cfo"))
    ni = _f(row.get("net_income"))
    roa_py = _f(row.get("roa_py"))
    ltd_ta = _f(row.get("ltd_to_assets"))
    ltd_ta_py = _f(row.get("ltd_to_assets_py"))
    cr = _f(row.get("current_ratio"))
    cr_py = _f(row.get("current_ratio_py"))
    shares = _f(row.get("shares"))
    shares_py = _f(row.get("shares_py"))
    gm = _f(row.get("gross_margin"))
    gm_py = _f(row.get("gross_margin_py"))
    at = _f(row.get("asset_turnover"))
    at_py = _f(row.get("asset_turnover_py"))

    def b(name, cond, needed):
        if any(v is None for v in needed):
            signals[name] = None
        else:
            signals[name] = 1 if cond else 0

    b("roa_positive", roa is not None and roa > 0, [roa])
    b("cfo_positive", cfo is not None and cfo > 0, [cfo])
    b("roa_improved", roa is not None and roa_py is not None and roa > roa_py, [roa, roa_py])
    b("accrual", cfo is not None and ni is not None and cfo > ni, [cfo, ni])
    b("leverage_down", ltd_ta is not None and ltd_ta_py is not None and ltd_ta < ltd_ta_py, [ltd_ta, ltd_ta_py])
    b("current_ratio_up", cr is not None and cr_py is not None and cr > cr_py, [cr, cr_py])
    b("no_dilution", shares is not None and shares_py is not None and shares <= shares_py, [shares, shares_py])
    b("gross_margin_up", gm is not None and gm_py is not None and gm > gm_py, [gm, gm_py])
    b("asset_turnover_up", at is not None and at_py is not None and at > at_py, [at, at_py])

    known = [v for v in signals.values() if v is not None]
    score = sum(known) if known else None
    return {
        "score": score,
        "max_possible_from_available": len(known),
        "signals": signals,
        "formula": "Sum of 9 binary financial-health signals (Piotroski 2000).",
        "interpretation": _piotroski_interp(score, len(known)),
        "limitations": "Incomplete inputs reduce the maximum; missing signals are N/A, not zero. Company-level only.",
    }


def _piotroski_interp(score, n):
    if score is None:
        return "N/A — insufficient company financials."
    if n < 9:
        return f"Partial F-score {score}/{n} available signals (not a full 9-point score)."
    if score >= 7:
        return "High financial-strength signal in the Piotroski framework (not a buy recommendation)."
    if score <= 3:
        return "Weak financial-strength signal in the Piotroski framework."
    return "Mixed financial-strength signal."


def beneish_m_score(row: dict) -> dict:
    dsri = _f(row.get("dsri"))
    gmi = _f(row.get("gmi"))
    aqi = _f(row.get("aqi"))
    sgi = _f(row.get("sgi"))
    depi = _f(row.get("depi"))
    sgai = _f(row.get("sgai"))
    tata = _f(row.get("tata"))
    lvgi = _f(row.get("lvgi"))
    parts = [dsri, gmi, aqi, sgi, depi, sgai, tata, lvgi]
    formula = "M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI"
    if any(p is None for p in parts):
        return {
            "score": None,
            "formula": formula,
            "interpretation": "N/A — all eight Beneish indices are required; none were imputed.",
            "limitations": "Do not treat a missing M-score as clean or as fraudulent.",
        }
    m = (
        -4.84
        + 0.92 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )
    return {
        "score": m,
        "formula": formula,
        "interpretation": "M > -2.22 is often cited as a higher manipulation-risk zone (Beneish). Not a legal finding.",
        "limitations": "Accounting-based screen; false positives/negatives are common.",
    }


def altman_z_score(row: dict) -> dict:
    wc = _f(row.get("working_capital"))
    ta = _f(row.get("total_assets"))
    re = _f(row.get("retained_earnings"))
    ebit = _f(row.get("ebit"))
    mve = _f(row.get("market_value_equity"))
    tl = _f(row.get("total_liabilities"))
    sales = _f(row.get("sales"))
    formula = "Z = 1.2*(WC/TA) + 1.4*(RE/TA) + 3.3*(EBIT/TA) + 0.6*(MVE/TL) + 1.0*(Sales/TA)"
    if any(v is None for v in (wc, ta, re, ebit, mve, tl, sales)) or not ta or not tl:
        return {
            "score": None,
            "formula": formula,
            "interpretation": "N/A — manufacturing-style Altman inputs incomplete.",
            "limitations": "Original Z-score is calibrated to manufacturing firms; not blindly applied to banks or bond ETFs.",
        }
    z = 1.2 * (wc / ta) + 1.4 * (re / ta) + 3.3 * (ebit / ta) + 0.6 * (mve / tl) + 1.0 * (sales / ta)
    if z > 2.99:
        band = "Safe zone (original manufacturing calibration)."
    elif z > 1.81:
        band = "Grey zone."
    else:
        band = "Distress zone (original manufacturing calibration)."
    return {
        "score": z,
        "formula": formula,
        "interpretation": band,
        "limitations": "Not a default probability. Do not assign this Z-score to an ETF wrapper.",
    }


def sustainable_growth_rate(roe: Optional[float], payout: Optional[float]) -> dict:
    formula = "SGR = ROE × (1 − payout) = ROE × retention"
    if roe is None or payout is None:
        return {
            "sgr": None,
            "formula": formula,
            "interpretation": "N/A — need ROE and payout/retention.",
            "classification": None,
        }
    sgr = roe * (1.0 - payout)
    return {
        "sgr": sgr,
        "formula": formula,
        "interpretation": "Internal growth rate if leverage and ROE persist and no new equity is issued.",
        "classification": None,
    }


def classify_growth(actual: Optional[float], sgr: Optional[float], prior_actual: Optional[float] = None) -> dict:
    if actual is None or sgr is None:
        return {
            "label": "N/A",
            "explanation": "Need both actual growth and sustainable growth. Missing values were not imputed.",
        }
    if actual <= sgr * 1.05:
        label = "sustainable growth"
        expl = "Actual growth is at or below the retention×ROE capacity (allowing a small band)."
    else:
        label = "potentially unsustainable growth"
        expl = "Actual growth exceeds SGR — it may require more leverage, new equity, or falling payouts."
    if prior_actual is not None:
        if actual > prior_actual:
            label = label  # keep
            trend = "improving growth"
        elif actual < prior_actual:
            trend = "deteriorating growth"
        else:
            trend = "stable growth"
    else:
        trend = "N/A — no prior growth rate"
    return {"label": label, "trend": trend, "explanation": expl}


def ratios_from_row(row: dict) -> dict:
    keys = [
        "roe",
        "roa",
        "roic",
        "debt_to_capital",
        "debt_to_assets",
        "quick_ratio",
        "eps",
        "gross_margin",
        "operating_margin",
        "net_margin",
        "revenue_growth",
        "eps_growth",
        "fcf",
        "fcf_growth",
        "interest_coverage",
        "debt_to_ebitda",
        "dividend_growth",
        "payout_ratio",
        "fcf_yield",
        "ev_ebitda",
        "ev_sales",
        "forward_pe",
        "pe",
        "pb",
        "ps",
        "peg",
    ]
    return {k: _f(row.get(k)) for k in keys}
