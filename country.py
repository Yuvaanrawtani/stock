"""Country → industry → security. Evidence-based; never auto-reject on one metric."""

from __future__ import annotations

COUNTRY_FIELDS = [
    "country",
    "developed_emerging",
    "gdp_growth",
    "inflation",
    "interest_rates",
    "currency",
    "demographics",
    "regulatory_environment",
    "political_risk",
    "structural_trends",
    "evidence",
    "source",
    "source_date",
]


def score_country(row: dict) -> dict:
    """Soft score from team-supplied evidence. Missing evidence → N/A, not rejection."""
    present = [k for k in COUNTRY_FIELDS if row.get(k) not in (None, "")]
    if not row.get("evidence") and not row.get("gdp_growth"):
        return {
            "country": row.get("country"),
            "score": None,
            "decision": "INSUFFICIENT EVIDENCE",
            "reason": "No automatic rejection. Upload or enter country evidence before scoring.",
            "fields_filled": present,
        }
    notes = []
    pts = []
    de = str(row.get("developed_emerging") or "").lower()
    if de == "developed":
        pts.append(1)
        notes.append("Developed-market classification (team/source).")
    elif de == "emerging":
        pts.append(0)
        notes.append("Emerging-market classification — not an automatic reject.")
    try:
        g = float(row.get("gdp_growth"))
        pts.append(1 if g > 0 else 0)
        notes.append(f"GDP growth input {g} (not a forecast).")
    except (TypeError, ValueError):
        notes.append("GDP growth N/A.")
    score = sum(pts) / len(pts) * 100 if pts else None
    return {
        "country": row.get("country"),
        "score": score,
        "decision": "REVIEW",
        "reason": "Country score is evidence-weighted, not a hard gate. "
        + " ".join(notes),
        "fields_filled": present,
        "evidence": row.get("evidence") or "N/A",
        "source": row.get("source") or "TEAM INPUT",
        "source_date": row.get("source_date") or "N/A",
    }
