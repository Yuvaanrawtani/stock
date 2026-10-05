"""Bear / base / bull causal chains. User-editable assumptions."""

from __future__ import annotations

from .funding import path_summary, project_path

DEFAULT_SCENARIOS = [
    {"n": "Base case", "dr": 0.0, "sy": 2029, "sr": 0.0},
    {"n": "Low return", "dr": -0.03, "sy": 2029, "sr": 0.0},
    {"n": "High volatility", "dr": -0.01, "sy": 2030, "sr": -0.20, "note": "Shock proxy for a high-vol year."},
    {"n": "Equity drawdown", "dr": 0.0, "sy": 2029, "sr": -0.35},
    {"n": "Recession", "dr": -0.01, "sy": 2031, "sr": -0.25},
    {"n": "High inflation", "dr": 0.0, "sy": 2029, "sr": 0.0, "inf": 0.06, "idx": True},
    {"n": "Interest-rate shock", "dr": -0.01, "sy": 2028, "sr": -0.12},
    {"n": "Combined stress", "dr": -0.03, "sy": 2032, "sr": -0.35, "inf": 0.06, "idx": True},
]


def run_scenarios(base_r: float, inflation: float, indexed: bool, rf: float, scenarios: list[dict]) -> list[dict]:
    out = []
    for s in scenarios:
        inf = s.get("inf", inflation)
        idx = s.get("idx", indexed)
        r = base_r + float(s.get("dr") or 0)
        rows = project_path(r, inf, idx, s.get("sy"), float(s.get("sr") or 0))
        summary = path_summary(rows, inf, idx, rf)
        chain = (
            f"{s['n']}: return assumption {r:.2%} "
            f"{'(shock year ' + str(s.get('sy')) + ' at ' + format(float(s.get('sr') or 0), '.0%') + ')' if s.get('sr') else ''} "
            f"→ path of portfolio wealth → 2033 pre-payment {summary['balance_2033_pre_payment']:.0f} "
            f"vs reserve {summary['reserve_requirement']:.0f} → {summary['status']}."
        )
        out.append({**summary, "name": s["n"], "assumptions": s, "causal_chain": chain})
    return out


def security_scenarios(ret_bear, ret_base, ret_bull) -> dict:
    return {
        "bear": {"expected_return": ret_bear, "source": "TEAM INPUT or MODEL ESTIMATE"},
        "base": {"expected_return": ret_base, "source": "TEAM INPUT or MODEL ESTIMATE"},
        "bull": {"expected_return": ret_bull, "source": "TEAM INPUT or MODEL ESTIMATE"},
        "label": "MODEL ESTIMATE paths — not predictions.",
    }
