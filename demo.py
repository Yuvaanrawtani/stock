"""Synthetic demo prices (labelled DEMO DATA). Port of the HTML RNG generator."""

from __future__ import annotations

import math
from datetime import date, timedelta

from .universe import EQ_SAMPLE, FI_SAMPLE, sample_universe_rows


def _rng(seed: int):
    a = seed & 0xFFFFFFFF

    def rnd():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = (t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        t ^= t >> 14
        return (t & 0xFFFFFFFF) / 4294967296

    return rnd


def _hash(s: str) -> int:
    h = 2166136261
    for c in s:
        h = ((h ^ ord(c)) * 16777619) & 0xFFFFFFFF
    return h


def demo_prices(ticker: str, n: int = 800, end: date | None = None) -> list[tuple[str, float]]:
    end = end or date(2025, 12, 31)
    mk = _rng(42)
    r = _rng(_hash(ticker))
    spy = ticker == "SPY"
    beta = 1.0 if spy else 0.4 + r() * 1.2
    iv = 0.0005 if spy else 0.006 + r() * 0.006
    p = 50 + r() * 200
    days = []
    d = end
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d -= timedelta(days=1)
    days = list(reversed(days))
    out = []
    for ds in days:
        # Box-Muller
        u1, u2 = 1 - mk(), mk()
        gz1 = math.sqrt(-2 * math.log(max(u1, 1e-12))) * math.cos(2 * math.pi * u2)
        u1, u2 = 1 - r(), r()
        gz2 = math.sqrt(-2 * math.log(max(u1, 1e-12))) * math.cos(2 * math.pi * u2)
        p *= 1 + beta * (0.0004 + 0.01 * gz1) + iv * gz2
        out.append((ds, round(p, 4)))
    return out


def load_demo(n_days: int = 800) -> dict:
    rows = sample_universe_rows()
    px = {}
    src = {}
    at = {}
    from .provenance import utc_now

    ts = utc_now()
    tickers = [u["t"] for u in rows] + ["SPY"]
    for t in tickers:
        px[t] = demo_prices(t, n_days)
        src[t] = "demo"
        at[t] = ts
    return {
        "u": rows,
        "px": px,
        "src": src,
        "at": at,
        "sample": True,
        "note": "USER-PROVIDED SAMPLE TICKERS — NOT VERIFIED AS COMPLETE OFFICIAL WInS UNIVERSE. Prices are SYNTHETIC demo data ending 2025-12-31.",
    }
