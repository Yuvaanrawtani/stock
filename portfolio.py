"""Growth engine vs commitment engine. Allocations are derived, not hard-coded percentages."""

from __future__ import annotations

import numpy as np

from .case import capital_clock_emphasis
from .metrics import sample_cov


def historical_portfolio_stats(returns_by_ticker: dict[str, list[float]], weights: dict[str, float], rf: float = 0.04) -> dict | None:
    tickers = [t for t in returns_by_ticker if t in weights]
    if len(tickers) < 2:
        return None
    n = min(len(returns_by_ticker[t]) for t in tickers)
    R = np.vstack([np.asarray(returns_by_ticker[t][-n:], dtype=float) for t in tickers])
    raw = np.array([max(0.0, float(weights.get(t, 0))) for t in tickers])
    if raw.sum() == 0:
        raw = np.ones(len(tickers))
    w = raw / raw.sum()
    pr = w @ R
    ret = float(pr.mean() * 252)
    vol = float(np.sqrt(sample_cov(pr, pr) * 252))
    c = 1.0
    pk = 1.0
    dd = 0.0
    for r in pr:
        c *= 1 + r
        pk = max(pk, c)
        dd = min(dd, c / pk - 1)
    corr_sum = 0.0
    pairs = 0
    mx = {"c": -2.0, "a": "", "b": ""}
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            k = sample_cov(R[i], R[j]) / np.sqrt(sample_cov(R[i], R[i]) * sample_cov(R[j], R[j]))
            corr_sum += k
            pairs += 1
            if k > mx["c"]:
                mx = {"c": float(k), "a": tickers[i], "b": tickers[j]}
    vp = sample_cov(pr, pr)
    rows = []
    for i, t in enumerate(tickers):
        rc = w[i] * sample_cov(R[i], pr) / vp if vp else 0
        rows.append({"t": t, "w": float(w[i]), "rc": float(rc)})
    return {
        "tickers": tickers,
        "weights": w,
        "rows": rows,
        "ret": ret,
        "vol": vol,
        "sharpe": (ret - rf) / vol if vol else None,
        "dd": dd,
        "avg_corr": corr_sum / pairs if pairs else None,
        "max_pair": mx,
        "n_obs": n,
        "label": "Historical statistics — not forecasts.",
    }


def derive_engines(
    as_of_year: int,
    funding_prob: float | None,
    portfolio_vol: float | None,
    avg_half_life_years: float | None,
    scenario_shortfall: bool,
) -> dict:
    clock = capital_clock_emphasis(as_of_year)
    p = 0.5 if funding_prob is None else funding_prob
    vol = 0.12 if portfolio_vol is None else portfolio_vol
    dur = 5.0 if avg_half_life_years is None else avg_half_life_years
    # Commitment share rises with 2033 proximity, lower funding probability, higher vol, shorter theses, failed stress.
    commit = (
        0.25 * clock["proximity_to_2033"]
        + 0.25 * (1 - p)
        + 0.20 * min(1.0, vol / 0.20)
        + 0.15 * (1 - min(1.0, dur / 8.0))
        + (0.15 if scenario_shortfall else 0.0)
    )
    commit = min(0.85, max(0.15, commit))
    growth = 1.0 - commit
    return {
        "as_of_year": as_of_year,
        "growth_engine": growth,
        "commitment_engine": commit,
        "inputs": {
            "funding_probability": funding_prob,
            "portfolio_vol": portfolio_vol,
            "avg_half_life_years": avg_half_life_years,
            "scenario_shortfall": scenario_shortfall,
            "years_to_2033": clock["years_to_2033"],
        },
        "note": "Derived blend, not a hard-coded 60/40. Markowitz still cannot override client constraints.",
        "clock": clock,
        "source": "MODEL ESTIMATE",
    }


def risk_score_security(vol, max_dd, beta, concentration) -> dict:
    parts = []
    if vol is not None:
        parts.append(min(100, vol / 0.40 * 100))
    if max_dd is not None:
        parts.append(min(100, abs(max_dd) / 0.60 * 100))
    if beta is not None:
        parts.append(min(100, abs(beta) / 1.5 * 100))
    if concentration is not None:
        parts.append(min(100, concentration * 100))
    if not parts:
        return {"score": None, "reason": "N/A — insufficient risk inputs."}
    s = sum(parts) / len(parts)
    return {"score": s, "reason": f"Equal-weight of available risk components ({len(parts)}). Higher = more risk.", "source": "MODEL ESTIMATE"}
