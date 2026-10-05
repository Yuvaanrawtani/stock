"""Laura funding schedule. WInS simulation P&L is never an input."""

from __future__ import annotations

from .case import (
    END_YEAR,
    INFLATION_INDEX_DEFAULT,
    START_YEAR,
    contribution_for_year,
    payment_for_year,
)


def project_path(
    annual_return: float,
    inflation: float = 0.0,
    indexed: bool = INFLATION_INDEX_DEFAULT,
    shock_year: int | None = None,
    shock_return: float = 0.0,
) -> list[dict]:
    rows = []
    b = 0.0
    for y in range(START_YEAR, END_YEAR + 1):
        add = contribution_for_year(y)
        pay = payment_for_year(y, inflation, indexed)
        b += add
        start = b
        paid = min(b, pay)
        shortfall = pay - paid
        b -= paid
        r = shock_return if shock_year is not None and y == shock_year else annual_return
        b *= 1.0 + r
        rows.append(
            {
                "year": y,
                "beginning": start,
                "contribution": add,
                "return_rate": r,
                "withdrawal": paid,
                "shortfall": shortfall,
                "ending": b,
            }
        )
    return rows


def reserve_requirement(inflation: float, indexed: bool, rf: float) -> float:
    """PV at start of 2033 of the ten beginning-of-year payments (first payment undiscounted)."""
    s = 0.0
    for k in range(10):
        pay = 50_000.0 * ((1.0 + inflation) ** k) if indexed else 50_000.0
        s += pay / ((1.0 + rf) ** k)
    return s


def path_summary(rows: list[dict], inflation: float, indexed: bool, rf: float) -> dict:
    b33 = next(r["beginning"] for r in rows if r["year"] == 2033)
    need = reserve_requirement(inflation, indexed, rf)
    short = sum(r["shortfall"] for r in rows)
    all_funded = short <= 1e-8
    ending = rows[-1]["ending"]
    if short > 0:
        status = "SHORTFALL"
    elif b33 >= need:
        status = "GREEN"
    else:
        status = "WATCH"
    return {
        "rows": rows,
        "balance_2033_pre_payment": b33,
        "reserve_requirement": need,
        "total_shortfall": short,
        "all_ten_funded": all_funded,
        "ending_wealth": ending,
        "status": status,
        "label": "MODEL ESTIMATE — NOT PREDICTION",
        "uses_wins_simulation": False,
    }
