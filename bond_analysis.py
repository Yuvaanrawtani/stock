"""Bond / fixed-income ETF metrics. Equity ratios are not applied blindly."""

from __future__ import annotations

BOND_KEYS = [
    "bond_yield",
    "sec_yield",
    "bond_duration",
    "avg_maturity",
    "bond_maturity",
    "credit_quality",
    "ig_hy",
    "issuer_type",
    "expense_ratio",
    "aum",
]

EQUITY_ONLY = {
    "pe_ratio",
    "pb_ratio",
    "ps_ratio",
    "peg",
    "piotroski",
    "beneish",
    "altman",
    "roe",
    "eps",
}


def bond_pack(extras: dict, price_metrics: dict | None) -> dict:
    out = {k: extras.get(k) for k in BOND_KEYS}
    out["interest_rate_sensitivity"] = extras.get("bond_duration")
    out["credit_risk"] = extras.get("credit_quality") or extras.get("ig_hy")
    out["inflation_sensitivity"] = extras.get("inflation_sensitivity")
    if price_metrics:
        out["volatility"] = price_metrics.get("volatility")
        out["sharpe"] = price_metrics.get("sharpe")
        out["max_drawdown"] = price_metrics.get("max_drawdown")
    out["skipped_equity_metrics"] = sorted(EQUITY_ONLY)
    out["note"] = (
        "Fixed-income analysis uses yield, duration, credit, and risk statistics. "
        "P/E, Piotroski, and other equity screens are not applied to this bond ETF."
    )
    return out


def is_bond(sec: dict) -> bool:
    c = (sec.get("c") or "").lower()
    return "bond" in c or "fixed" in c
