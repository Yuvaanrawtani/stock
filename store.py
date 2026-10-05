"""Persistent session store (JSON)."""

from __future__ import annotations

import json
from pathlib import Path

from .provenance import utc_now
from .scenario_engine import DEFAULT_SCENARIOS
from .scoring import DEFAULT_WEIGHTS

STATE_PATH = Path(__file__).resolve().parents[1] / ".wins_state.json"


def default_state() -> dict:
    return {
        "u": [],
        "px": {},
        "src": {},
        "at": {},
        "ex": {},
        "fin": {},
        "holdings": [],
        "research": [],
        "countries": {},
        "industries": {},
        "cfg": {"rf": 0.04, "bench": "SPY", "lb": 1095},
        "last": None,
        "log": [],
        "rej": 0,
        "dupU": 0,
        "dupP": 0,
        "ml": None,
        "sample": False,
        "w_legacy": {"sharpe": 0.3, "cagr": 0.2, "alpha": 0.1, "volatility": 0.2, "max_drawdown": 0.2},
        "score_weights": dict(DEFAULT_WEIGHTS),
        "f": {"a": {}, "lo": {}, "hi": {}, "q": ""},
        "dec": {},
        "pw": {},
        "sel": "",
        "thesis": {},
        "overrides": [],
        "trades": [],
        "notes": [],
        "fc": {"r": 0.05, "sd": 0.10, "inf": 0.025, "rf": 0.03, "idx": False, "n": 5000},
        "sc": DEFAULT_SCENARIOS,
        "as_of_year": 2027,
        "manual_scores": {},
    }


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    serial = json.loads(json.dumps(state, default=str))
    path.write_text(json.dumps(serial))


def load_state(path: Path = STATE_PATH) -> dict:
    base = default_state()
    if path.exists():
        try:
            base.update(json.loads(path.read_text()))
        except Exception:
            pass
    return base
