"""Official case facts for Laura Gao. Do not mix WInS simulation P&L into these cash flows."""

from __future__ import annotations

CONTRIB_2027 = 300_000.0
CONTRIB_2028 = 150_000.0
PAY_AMOUNT = 50_000.0
PAY_START = 2033
PAY_END = 2042
N_PAYMENTS = 10
START_YEAR = 2027
END_YEAR = 2042
RESERVE_YEAR = 2033
FACILITY_ESTIMATE_YEAR = 2031
INFLATION_INDEX_DEFAULT = False
CLIENT_NAME = "Laura Gao"

PHILOSOPHY = (
    "We don't invest in a security just because it scores highly. "
    "We invest when we find a strong, durable thesis that the market may not have fully recognized, "
    "identify why the market disagrees, and test whether that thesis can survive different future scenarios "
    "while serving Laura's specific long-term needs."
)

TENSION_LINE = "We don't invest when every strategy agrees. We investigate when strong strategies disagree."

WINS_NOT_LAURA = (
    "The WInS simulation portfolio is NOT Laura's actual long-term portfolio. "
    "Long-term projections begin with the case cash flows and reasonable return assumptions — "
    "never WInS simulated gains or losses."
)

LAURA_ROLES = (
    "Growth",
    "Diversification",
    "Defensive",
    "Liquidity",
    "Income",
    "Inflation protection",
    "Capital preservation",
    "Structural growth",
)

HALF_LIFE_BUCKETS = {
    "SHORT": "<2 years",
    "MEDIUM": "2–4 years",
    "LONG": "4–7 years",
    "STRUCTURAL": "7+ years",
}


def contribution_for_year(year: int) -> float:
    if year == 2027:
        return CONTRIB_2027
    if year == 2028:
        return CONTRIB_2028
    return 0.0


def payment_for_year(year: int, inflation: float = 0.0, indexed: bool = False) -> float:
    if year < PAY_START or year > PAY_END:
        return 0.0
    if indexed:
        return PAY_AMOUNT * ((1.0 + inflation) ** (year - PAY_START))
    return PAY_AMOUNT


def years_to_2033(as_of_year: int) -> int:
    return RESERVE_YEAR - as_of_year


def capital_clock_emphasis(as_of_year: int) -> dict:
    """Increase preservation/liquidity emphasis as 2033 approaches. Not a hard-coded allocation."""
    remaining = max(0, years_to_2033(as_of_year))
    span = RESERVE_YEAR - START_YEAR
    proximity = 1.0 - (remaining / span) if span else 1.0
    proximity = min(1.0, max(0.0, proximity))
    return {
        "as_of_year": as_of_year,
        "years_to_2033": remaining,
        "proximity_to_2033": proximity,
        "increase": [
            "capital preservation",
            "liquidity",
            "downside protection",
            "thesis durability",
            "scenario resilience",
        ],
        "decrease_tolerance": [
            "extremely short thesis life",
            "excessive concentration",
            "highly speculative exposure",
            "unreliable liquidity",
        ],
    }
