"""Thesis Tension Engine — the decision framework. Scores never equal BUY."""

from __future__ import annotations

from .case import HALF_LIFE_BUCKETS, LAURA_ROLES, TENSION_LINE, capital_clock_emphasis
from .provenance import TEAM_INPUT, utc_now

THESIS_FIELDS = [
    "thesis",
    "thesis_half_life",
    "half_life_override",
    "half_life_reason",
    "market_tension",
    "what_thesis_says",
    "what_market_says",
    "catalyst",
    "catalyst_timeframe",
    "catalyst_evidence",
    "catalyst_confidence",
    "catalyst_source",
    "invalidation",
    "bear",
    "base",
    "bull",
    "laura_role",
    "laura_role_why",
    "final_decision",
    "decision_why",
]


def bucket_half_life(years: float | None, override: str | None = None) -> dict:
    if override:
        return {"bucket": override, "years": years, "source": "TEAM INPUT override"}
    if years is None:
        return {"bucket": "N/A", "years": None, "source": "N/A"}
    if years < 2:
        b = "SHORT"
    elif years < 4:
        b = "MEDIUM"
    elif years < 7:
        b = "LONG"
    else:
        b = "STRUCTURAL"
    return {"bucket": b, "years": years, "source": "MODEL ESTIMATE", "meaning": HALF_LIFE_BUCKETS[b]}


def default_card(ticker: str) -> dict:
    return {
        "ticker": ticker,
        "thesis": "",
        "thesis_half_life_years": None,
        "half_life_override": "",
        "half_life_reason": "",
        "market_tension": "",
        "what_thesis_says": "",
        "what_market_says": "",
        "catalyst": "",
        "catalyst_timeframe": "",
        "catalyst_evidence": "",
        "catalyst_confidence": "",
        "catalyst_source": "",
        "invalidation": "",
        "bear": "",
        "base": "",
        "bull": "",
        "laura_role": "",
        "laura_role_why": "",
        "final_decision": "",
        "decision_why": "",
        "updated": None,
    }


def completeness(card: dict) -> dict:
    required = [
        "thesis",
        "market_tension",
        "catalyst",
        "invalidation",
        "bear",
        "base",
        "bull",
        "laura_role",
        "decision_why",
    ]
    missing = [k for k in required if not str(card.get(k) or "").strip()]
    return {"missing": missing, "complete": not missing}


def dna_vector(card: dict, scores: dict) -> dict:
    """0–100 profile. Missing qualitative evidence stays N/A (None), not a fake 50."""
    hl = bucket_half_life(card.get("thesis_half_life_years"), card.get("half_life_override") or None)
    hl_map = {"SHORT": 25, "MEDIUM": 50, "LONG": 75, "STRUCTURAL": 100}
    return {
        "Thesis Strength": scores.get("thesis_strength"),
        "Thesis Half-Life": hl_map.get(hl["bucket"]),
        "Market Tension": scores.get("market_tension"),
        "Catalyst Visibility": scores.get("catalyst"),
        "Scenario Resilience": scores.get("scenario_resilience"),
        "Fundamental Quality": scores.get("fundamental_quality"),
        "Valuation": scores.get("valuation"),
        "Risk": None if scores.get("risk") is None else 100 - scores["risk"],
        "Laura Alignment": scores.get("laura_alignment"),
        "Funding Compatibility": scores.get("funding_compatibility"),
        "half_life": hl,
        "philosophy": TENSION_LINE,
    }


def explain_decision(card: dict, overall: float | None, as_of_year: int) -> dict:
    clock = capital_clock_emphasis(as_of_year)
    comp = completeness(card)
    decision = card.get("final_decision") or ""
    if not decision:
        decision = "WATCH" if not comp["complete"] else "WATCH"
        auto = True
    else:
        auto = False
    if overall is not None and overall >= 80 and decision == "INVEST" and auto:
        pass
    return {
        "decision": decision if decision in ("INVEST", "WATCH", "REJECT") else "WATCH",
        "overall_score_is_not_buy": True,
        "missing": comp["missing"],
        "capital_clock": clock,
        "roles": LAURA_ROLES,
        "note": "Overall score never equals INVEST. Human (or explicit team field) decides INVEST / WATCH / REJECT.",
        "updated": utc_now(),
        "source": TEAM_INPUT,
    }
