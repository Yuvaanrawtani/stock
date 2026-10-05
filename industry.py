"""Industry / theme filter with Porter, SWOT, STEEPLE, McKinsey 7S, CSR/ESG as evidence slots."""

from __future__ import annotations

INDUSTRY_FIELDS = [
    "industry",
    "theme",
    "industry_growth",
    "competitive_intensity",
    "profitability",
    "cyclicality",
    "capital_intensity",
    "barriers_to_entry",
    "technological_disruption",
    "regulation",
    "demand",
    "structural_growth",
    "evidence",
    "source",
    "source_date",
]

PORTER = ["rivalry", "new_entrants", "supplier_power", "buyer_power", "substitutes"]
SWOT = ["strengths", "weaknesses", "opportunities", "threats"]
STEEPLE = ["social", "technological", "economic", "environmental", "political", "legal", "ethical"]
MCK7 = ["strategy", "structure", "systems", "shared_values", "skills", "style", "staff"]
ESG = ["csr_esg_evidence"]


def qualitative_block(prefix: str, keys: list[str], row: dict) -> dict:
    out = {}
    filled = 0
    for k in keys:
        v = row.get(f"{prefix}_{k}") if prefix else row.get(k)
        if prefix:
            v = row.get(f"{prefix}_{k}", row.get(k))
        out[k] = v if v not in (None, "") else "N/A"
        if out[k] != "N/A":
            filled += 1
    return {"items": out, "filled": filled, "n": len(keys), "source": row.get("source") or "TEAM INPUT"}


def analyze_industry(row: dict) -> dict:
    facts = {k: row.get(k) if row.get(k) not in (None, "") else "N/A" for k in INDUSTRY_FIELDS}
    porter = qualitative_block("porter", PORTER, row)
    swot = qualitative_block("", SWOT, row)
    steeple = qualitative_block("steeple", STEEPLE, row)
    m7 = qualitative_block("m7", MCK7, row)
    esg = qualitative_block("", ESG, row)
    if facts["evidence"] == "N/A" and porter["filled"] == 0:
        decision = "INSUFFICIENT EVIDENCE"
        reason = "Qualitative scores are not generated without evidence. No fake industry facts."
        score = None
    else:
        decision = "REVIEW"
        reason = "Industry view is only as strong as the cited evidence."
        score = 100.0 * (porter["filled"] / porter["n"]) if porter["n"] else None
    return {
        "facts": facts,
        "porter": porter,
        "swot": swot,
        "steeple": steeple,
        "mckinsey_7s": m7,
        "csr_esg": esg,
        "score": score,
        "decision": decision,
        "reason": reason,
        "limitation": "Never treat a blank Porter/SWOT box as a completed analysis.",
    }
