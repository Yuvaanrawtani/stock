"""Provenance wrappers. Never silently substitute synthetic data for real data."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

REAL = "REAL DATA"
USER_UPLOADED = "USER UPLOADED DATA"
DEMO = "DEMO DATA"
MODEL_ESTIMATE = "MODEL ESTIMATE"
TEAM_INPUT = "TEAM INPUT"
NA_SOURCE = "N/A"

NA_TEXT = "N/A — unavailable"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Field:
    value: Any = None
    source: str = NA_SOURCE
    date: Optional[str] = None
    timestamp: Optional[str] = None
    provider: str = ""
    frequency: str = ""
    confidence: str = "none"
    stale: bool = True
    formula: str = ""
    interpretation: str = ""
    limitations: str = ""
    available: bool = False

    def display(self) -> str:
        if not self.available or self.value is None:
            return NA_TEXT
        return str(self.value)

    def as_dict(self) -> dict:
        return asdict(self)


def na_field(formula: str = "", interpretation: str = "", limitations: str = "") -> Field:
    return Field(
        value=None,
        source=NA_SOURCE,
        formula=formula,
        interpretation=interpretation,
        limitations=limitations or "Value was not provided and was not imputed.",
        available=False,
        confidence="none",
        stale=True,
    )


def make_field(
    value: Any,
    source: str,
    *,
    formula: str = "",
    interpretation: str = "",
    limitations: str = "",
    provider: str = "",
    frequency: str = "",
    confidence: str = "medium",
    date: Optional[str] = None,
    timestamp: Optional[str] = None,
    stale_days: Optional[float] = None,
) -> Field:
    if value is None or (isinstance(value, float) and value != value):  # NaN
        return na_field(formula, interpretation, limitations)
    ts = timestamp or utc_now()
    stale = False
    if stale_days is not None:
        stale = stale_days > 7
    if source == DEMO:
        confidence = "demo"
        limitations = (limitations + " " if limitations else "") + "DEMO DATA — not live market data."
    return Field(
        value=value,
        source=source,
        date=date,
        timestamp=ts,
        provider=provider,
        frequency=frequency,
        confidence=confidence,
        stale=stale,
        formula=formula,
        interpretation=interpretation,
        limitations=limitations,
        available=True,
    )


@dataclass
class MetricCard:
    name: str
    field: Field
    what: str
    why: str

    def as_dict(self) -> dict:
        return {"name": self.name, "what": self.what, "why": self.why, **self.field.as_dict()}


def classify_source(raw: str) -> str:
    s = (raw or "").upper()
    if "DEMO" in s:
        return DEMO
    if "ESTIMATE" in s or "MODEL" in s:
        return MODEL_ESTIMATE
    if "TEAM" in s:
        return TEAM_INPUT
    if "UPLOAD" in s or "CSV" in s or "XLSX" in s or "USER" in s:
        return USER_UPLOADED
    if s in ("", "N/A", "NA"):
        return NA_SOURCE
    return USER_UPLOADED
