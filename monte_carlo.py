"""Monte Carlo on case cash flows. MODEL ESTIMATE — NOT PREDICTION."""

from __future__ import annotations

import numpy as np

from .case import END_YEAR, INFLATION_INDEX_DEFAULT, START_YEAR, contribution_for_year, payment_for_year
from .funding import reserve_requirement


def simulate(
    n: int = 5000,
    mu: float = 0.05,
    sd: float = 0.10,
    inflation: float = 0.025,
    indexed: bool = INFLATION_INDEX_DEFAULT,
    rf: float = 0.03,
    seed: int = 7,
) -> dict:
    n = max(100, int(n))
    rng = np.random.default_rng(seed)
    m = np.log(1.0 + mu) - 0.5 * sd * sd
    ending = np.empty(n)
    b33 = np.empty(n)
    short = np.empty(n)
    funded = 0
    years = list(range(START_YEAR, END_YEAR + 1))
    z = rng.standard_normal((n, len(years)))
    for p in range(n):
        b = 0.0
        sh = 0.0
        bal33 = 0.0
        for i, y in enumerate(years):
            b += contribution_for_year(y)
            if y == 2033:
                bal33 = b
            if y >= 2033:
                pay = payment_for_year(y, inflation, indexed)
                pd = min(b, pay)
                sh += pay - pd
                b -= pd
            b *= np.exp(m + sd * z[p, i])
        if sh <= 0:
            funded += 1
        ending[p] = b
        b33[p] = bal33
        short[p] = sh
    def q(a, pctl):
        return float(np.quantile(a, pctl))

    need = reserve_requirement(inflation, indexed, rf)
    room = b33 - need
    return {
        "n": n,
        "p_all_funded": funded / n,
        "p_shortfall": 1.0 - funded / n,
        "ending": {
            "p5": q(ending, 0.05),
            "p10": q(ending, 0.10),
            "p25": q(ending, 0.25),
            "p50": q(ending, 0.50),
            "p75": q(ending, 0.75),
            "p90": q(ending, 0.90),
            "p95": q(ending, 0.95),
        },
        "reserve_2033": {
            "p5": q(b33, 0.05),
            "p10": q(b33, 0.10),
            "p25": q(b33, 0.25),
            "p50": q(b33, 0.50),
            "p75": q(b33, 0.75),
            "p90": q(b33, 0.90),
            "p95": q(b33, 0.95),
        },
        "facility_contribution_range_2033": {
            "note": "Indicative room above the PV reserve at start of 2033. MODEL ESTIMATE for 2031 discussion.",
            "p10": float(np.quantile(np.maximum(0, room), 0.10)),
            "p50": float(np.quantile(np.maximum(0, room), 0.50)),
            "p90": float(np.quantile(np.maximum(0, room), 0.90)),
        },
        "max_shortfall": float(short.max()),
        "reserve_requirement": need,
        "assumptions": {
            "mu": mu,
            "sd": sd,
            "inflation": inflation,
            "indexed": indexed,
            "rf": rf,
            "seed": seed,
            "process": "i.i.d. lognormal annual returns; case cash flows only; no WInS simulation P&L.",
        },
        "label": "MODEL ESTIMATE — NOT PREDICTION",
    }
