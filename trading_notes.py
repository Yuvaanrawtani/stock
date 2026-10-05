"""Trading notes database and three-note analysis."""

from __future__ import annotations

from .provenance import utc_now

NOTE_FIELDS = [
    "what_we_did",
    "why",
    "evidence",
    "strategy_fit",
    "risk_accepted",
    "what_would_prove_wrong",
    "what_happened",
    "thesis_evolution",
]


def new_note(**kwargs) -> dict:
    n = {k: kwargs.get(k) or "" for k in NOTE_FIELDS}
    n["date"] = kwargs.get("date") or utc_now()[:10]
    n["ticker"] = (kwargs.get("ticker") or "").upper()
    n["sources"] = kwargs.get("sources") or ""
    n["created"] = utc_now()
    return n


def analyze_three(notes: list[dict]) -> dict:
    if len(notes) != 3:
        return {"ok": False, "error": "Select exactly three trading notes."}
    rows = []
    for n in notes:
        evo = (n.get("thesis_evolution") or "").lower()
        if "strengthen" in evo:
            tag = "STRENGTHENED"
        elif "weaken" in evo:
            tag = "WEAKENED"
        elif "remain" in evo:
            tag = "REMAINED"
        else:
            tag = "N/A — team has not classified thesis evolution"
        rows.append(
            {
                "date": n.get("date"),
                "ticker": n.get("ticker"),
                "decision": n.get("what_we_did") or "N/A",
                "thesis": n.get("why") or "N/A",
                "evidence": n.get("evidence") or "N/A",
                "strategy_alignment": n.get("strategy_fit") or "N/A",
                "outcome": n.get("what_happened") or "N/A",
                "lessons": n.get("what_would_prove_wrong") or "N/A",
                "thesis_evolution": tag,
                "repeat?": "Only if invalidation still false and Laura role unchanged — team judgment.",
            }
        )
    return {"ok": True, "rows": rows, "note": "Analysis quotes stored notes. It does not invent outcomes."}
