"""Editable IPS generator. Pulls case facts + model outputs; flags human sections."""

from __future__ import annotations

from .case import (
    CLIENT_NAME,
    CONTRIB_2027,
    CONTRIB_2028,
    N_PAYMENTS,
    PAY_AMOUNT,
    PAY_END,
    PAY_START,
    PHILOSOPHY,
    TENSION_LINE,
    WINS_NOT_LAURA,
)


def build_ips(state: dict) -> str:
    fc = state.get("fc", {})
    weights = state.get("pw", {})
    thesis = state.get("thesis", {})
    funding = state.get("last_funding_summary") or {}
    sections = []

    def sec(n, title, body, human=False):
        tag = "\n[TEAM INPUT REQUIRED — interpret for the judges]\n" if human else "\n"
        sections.append(f"## {n}. {title}{tag}{body.strip()}\n")

    sec(1, "Client", f"Client: {CLIENT_NAME}. WInS is a virtual competition. {WINS_NOT_LAURA}")
    sec(
        2,
        "Objectives",
        "Primary: fund ten fixed $50,000 operating payments (2033–2042) with a high degree of certainty.\n"
        "Secondary: after protecting the operating commitment, consider a responsible 2033 facility contribution.\n"
        "Growth of residual wealth is subordinate to payment certainty.",
        human=True,
    )
    sec(
        3,
        "Constraints",
        "Eligible securities: WInS universe only (WINS_APPROVED). No real brokerage trading. "
        "Payments are not inflation-indexed in the case (model default: inflation indexing OFF).",
    )
    sec(4, "Time horizon", "Investment period begins 2027. Operating decumulation 2033–2042. Analysis year for facility range: 2031.")
    sec(5, "Risk", "Risk is the chance of missing an operating payment or needing a distressed sale near 2033 — not tracking error vs a stock index.", human=True)
    sec(6, "Liquidity", "Liquidity tolerance falls as 2033 approaches (Capital Clock). Unreliable liquidity is de-emphasized near funding years.", human=True)
    sec(
        7,
        "Operating commitments",
        f"Beginning 2027: ${CONTRIB_2027:,.0f}. Beginning 2028: +${CONTRIB_2028:,.0f}. "
        f"Beginning {PAY_START}–{PAY_END}: {N_PAYMENTS} × ${PAY_AMOUNT:,.0f} (total $500,000).",
    )
    sec(8, "Strategy", f"{PHILOSOPHY}\n\n{TENSION_LINE}\nThesis Tension is the decision framework; models are tools.", human=True)
    alloc = ", ".join(f"{t} {w:.1%}" for t, w in weights.items()) or "No portfolio weights yet."
    sec(9, "Asset allocation", f"Current working weights: {alloc}\nGrowth vs Commitment engines are derived from funding probability, risk, durability, and calendar — not a fixed 60/40.")
    sec(10, "Security selection", "Country → Industry → Security. WInS-eligible only. Thesis card required for INVEST.", human=True)
    sec(11, "Diversification", "Watch pairwise correlation, country/sector concentration, and single-name underlying holdings concentration.")
    sec(12, "Risk management", "Invalidation conditions are fundamental/strategic, not a price drop alone. Overrides require a written reason.")
    sec(13, "Monitoring", "Refresh uploaded prices/fundamentals; flag stale series (>7 days); re-read thesis half-life vs Capital Clock.")
    sec(14, "Rebalancing", "Rebalancing implements strategy; it is not a license for excessive virtual trading.", human=True)
    sec(15, "Scenario planning", "Bear/base/bull plus named stress tests. Status GREEN / WATCH / SHORTFALL is a model estimate.")
    fund_txt = (
        f"Assumed mean {fc.get('r', 0):.2%}, vol {fc.get('sd', 0):.2%}, inflation indexing {fc.get('idx', False)}."
        if fc
        else "No funding run yet."
    )
    if funding:
        fund_txt += f" Last model P(all payments) shown in the Funding/Monte Carlo tabs. Label: MODEL ESTIMATE — NOT PREDICTION."
    sec(16, "Funding confidence", fund_txt)
    th = [f"- {t}: {c.get('final_decision') or 'WATCH'} — {(c.get('thesis') or 'N/A')[:180]}" for t, c in thesis.items()]
    sections.append("## Thesis Tension register\n" + ("\n".join(th) if th else "No thesis cards yet.") + "\n")
    return "# Investment Policy Statement (working draft)\n\n" + "\n".join(sections)
