"""Evidence-only qualitative helpers."""

from __future__ import annotations

from .industry import analyze_industry, qualitative_block


def require_evidence(text: str, source: str, date: str) -> dict:
    if not (text and str(text).strip()) or str(text).strip().upper() in ("N/A", "NA"):
        return {"ok": False, "text": "N/A", "source": "N/A", "date": "N/A"}
    return {
        "ok": True,
        "text": text.strip(),
        "source": source or "TEAM INPUT",
        "date": date or "N/A",
    }
