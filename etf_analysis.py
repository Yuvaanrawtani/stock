"""ETF wrapper metrics vs underlying company aggregates. Never copy company scores onto the ETF."""

from __future__ import annotations

from statistics import median
from typing import Optional

from .fundamentals import altman_z_score, beneish_m_score, piotroski_f_score, ratios_from_row


def etf_wrapper_fields(sec: dict, extras: dict) -> dict:
    out = {}
    for k in (
        "expense_ratio",
        "aum",
        "holdings_count",
        "top10_concentration",
        "largest_holding",
        "geography",
        "sector",
        "industry",
        "theme",
        "market_cap_exposure",
        "growth_value",
        "benchmark",
        "category",
    ):
        if k in extras and extras[k] not in (None, ""):
            out[k] = extras[k]
        elif k in sec.get("a", {}) and sec["a"][k] not in (None, ""):
            out[k] = sec["a"][k]
        else:
            out[k] = None
    return out


def aggregate_holdings_quality(holdings: list[dict], financials: dict[str, dict]) -> dict:
    """Weight-aware distribution of company scores. Labelled as ETF quality *exposure*, not ETF F-score."""
    f_scores = []
    m_scores = []
    z_scores = []
    ratio_buckets = {
        "roe": [],
        "roa": [],
        "roic": [],
        "debt_to_capital": [],
        "debt_to_assets": [],
        "quick_ratio": [],
        "eps": [],
        "gross_margin": [],
        "operating_margin": [],
        "net_margin": [],
        "revenue_growth": [],
        "eps_growth": [],
        "fcf": [],
    }
    used = 0
    missing = 0
    w_known = 0.0
    for h in holdings:
        fin = financials.get(h["holding"])
        w = h.get("weight") or 0.0
        if not fin:
            missing += 1
            continue
        used += 1
        w_known += w
        f = piotroski_f_score(fin)
        m = beneish_m_score(fin)
        z = altman_z_score(fin)
        if f["score"] is not None:
            f_scores.append((w, f["score"]))
        if m["score"] is not None:
            m_scores.append((w, m["score"]))
        if z["score"] is not None:
            z_scores.append((w, z["score"]))
        rats = ratios_from_row(fin)
        for k, v in rats.items():
            if k in ratio_buckets and v is not None:
                ratio_buckets[k].append((w, v))

    def dist(pairs):
        if not pairs:
            return None
        vals = [v for _, v in pairs]
        ww = [w for w, _ in pairs]
        sw = sum(ww) or 1.0
        wavg = sum(w * v for w, v in pairs) / sw
        return {
            "n": len(pairs),
            "min": min(vals),
            "median": median(vals),
            "max": max(vals),
            "weighted_avg": wavg,
        }

    return {
        "label": "ETF Quality Exposure (underlying companies) — NOT an ETF Piotroski/Beneish/Altman score",
        "holdings_with_financials": used,
        "holdings_missing_financials": missing,
        "weight_with_financials": w_known,
        "piotroski_exposure": dist(f_scores),
        "beneish_exposure": dist(m_scores),
        "altman_exposure": dist(z_scores),
        "ratio_exposure": {k: dist(v) for k, v in ratio_buckets.items()},
        "limitation": "Aggregates describe the holdings sample you uploaded. Missing holdings are N/A, not assumed average.",
    }
