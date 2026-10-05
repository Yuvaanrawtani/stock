"""Sentiment creates MARKET TENSION. It never auto-overrides fundamentals."""

from __future__ import annotations

from typing import Optional


def tension_from_sentiment(
    fundamental_quality: Optional[float],
    valuation_rich: Optional[bool],
    sentiment: Optional[float],
    momentum: Optional[float],
) -> dict:
    parts = []
    if fundamental_quality is not None and sentiment is not None and valuation_rich is True and sentiment > 0.5:
        parts.append(
            "Strong fundamentals + rich valuation + positive sentiment → investigate whether expectations are already priced in."
        )
    if fundamental_quality is not None and sentiment is not None and fundamental_quality >= 70 and sentiment < 0:
        parts.append("Quality vs Sentiment: fundamentals look stronger than sentiment.")
    if momentum is not None and sentiment is not None and momentum > 0 and sentiment < 0:
        parts.append("Momentum vs Contrarian: price momentum positive while sentiment is negative.")
    if not parts:
        if sentiment is None:
            parts.append("Sentiment N/A — no override, no automatic tension from news.")
        else:
            parts.append("Sentiment recorded as a signal, not a decision.")
    return {
        "sentiment": sentiment,
        "momentum": momentum,
        "market_tension_notes": parts,
        "overrides_fundamentals": False,
        "rule": "Sentiment is not allowed to automatically override fundamentals.",
    }
