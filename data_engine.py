"""Ingest universe, prices, holdings, financials, research. Track provenance. Never fabricate."""

from __future__ import annotations

import io
from typing import Optional

import pandas as pd

from .provenance import DEMO, USER_UPLOADED, utc_now

UNIVERSE_COLS = ["ticker", "name", "asset_class"]
PRICE_LONG = ["ticker", "date", "close"]
HOLDINGS_COLS = ["etf_ticker", "holding_ticker", "holding_name", "weight"]
FIN_COLS = ["ticker", "as_of"]
RESEARCH_COLS = ["ticker", "date", "field", "value", "source", "notes"]


def _read_table(file_or_text, filename: str = "") -> pd.DataFrame:
    name = (filename or "").lower()
    if hasattr(file_or_text, "read"):
        raw = file_or_text.read()
        if isinstance(raw, bytes):
            bio = io.BytesIO(raw)
        else:
            bio = io.StringIO(str(raw))
        if name.endswith(".xlsx") or name.endswith(".xls"):
            return pd.read_excel(bio)
        bio.seek(0)
        try:
            return pd.read_csv(bio)
        except Exception:
            bio.seek(0)
            return pd.read_csv(bio, sep="\t")
    text = str(file_or_text).strip()
    if not text:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(text))


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    aliases = {
        "symbol": "ticker",
        "security_name": "name",
        "assetclass": "asset_class",
        "adj_close": "close",
        "adjclose": "close",
        "price": "close",
        "etf": "etf_ticker",
        "holding": "holding_ticker",
        "weight_%": "weight",
        "wgt": "weight",
    }
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})
    return df


def parse_universe(file_or_text, filename: str = "") -> dict:
    df = _norm_cols(_read_table(file_or_text, filename))
    if df.empty or "ticker" not in df.columns:
        return {"ok": False, "error": "Universe needs a ticker (or symbol) column.", "rows": []}
    seen = set()
    dup = 0
    rows = []
    extra_numeric = {
        "market_cap",
        "pe_ratio",
        "dividend_yield",
        "eps",
        "profit_margin",
        "roe",
        "expense_ratio",
        "aum",
        "bond_yield",
        "bond_duration",
        "bond_maturity",
        "news_sentiment",
        "news_count",
        "pb_ratio",
        "ps_ratio",
        "peg",
        "holdings_count",
        "top10_concentration",
        "largest_holding",
        "sec_yield",
        "avg_maturity",
    }
    for _, r in df.iterrows():
        t = str(r.get("ticker", "")).strip().upper()
        if not t or t == "NAN":
            continue
        if t in seen:
            dup += 1
            continue
        seen.add(t)
        attrs = {}
        extras = {}
        for c in df.columns:
            if c in ("ticker", "name", "asset_class"):
                continue
            val = r.get(c)
            if pd.isna(val) or val == "":
                continue
            if c in extra_numeric:
                extras[c] = val
            else:
                attrs[c] = val
        wins = str(r.get("wins_approved", r.get("wins_eligible", "UNKNOWN"))).strip().upper()
        if wins in ("TRUE", "YES", "1", "Y"):
            wins = "TRUE"
        elif wins in ("FALSE", "NO", "0", "N"):
            wins = "FALSE"
        else:
            wins = "UNKNOWN"
        rows.append(
            {
                "t": t,
                "n": "" if pd.isna(r.get("name", "")) else str(r.get("name", "")),
                "c": "" if pd.isna(r.get("asset_class", "")) else str(r.get("asset_class", "")),
                "a": {k: (None if pd.isna(v) else v) for k, v in attrs.items()},
                "x": extras,
                "wins_approved": wins,
            }
        )
    return {"ok": True, "rows": rows, "dup": dup, "at": utc_now(), "source": USER_UPLOADED, "n": len(rows)}


def parse_prices(file_or_text, filename: str = "", source: str = USER_UPLOADED) -> dict:
    df = _norm_cols(_read_table(file_or_text, filename))
    if df.empty:
        return {"ok": False, "error": "Empty price file.", "px": {}, "rej": 0, "dup": 0}
    px: dict[str, list] = {}
    rej = 0
    dup = 0
    if {"ticker", "date", "close"}.issubset(df.columns):
        for _, r in df.iterrows():
            t = str(r["ticker"]).strip().upper()
            ds = str(r["date"])[:10]
            try:
                p = float(r["close"])
            except (TypeError, ValueError):
                rej += 1
                continue
            px.setdefault(t, []).append((ds, p))
    elif df.columns[0] == "date":
        for col in df.columns[1:]:
            t = str(col).strip().upper()
            for _, r in df.iterrows():
                ds = str(r["date"])[:10]
                try:
                    p = float(r[col])
                except (TypeError, ValueError):
                    rej += 1
                    continue
                px.setdefault(t, []).append((ds, p))
    else:
        return {
            "ok": False,
            "error": "Prices CSV: ticker,date,close OR date,TICKER1,TICKER2,… (YYYY-MM-DD).",
            "px": {},
            "rej": 0,
            "dup": 0,
        }

    cleaned = {}
    for t, rows in px.items():
        m = {}
        for ds, p in rows:
            if not _valid_date(ds) or not (p > 0):
                rej += 1
                continue
            if ds in m:
                dup += 1
            m[ds] = p
        cleaned[t] = sorted(m.items())
    return {"ok": True, "px": cleaned, "rej": rej, "dup": dup, "source": source, "at": utc_now()}


def parse_holdings(file_or_text, filename: str = "") -> dict:
    df = _norm_cols(_read_table(file_or_text, filename))
    if df.empty or "etf_ticker" not in df.columns:
        return {"ok": False, "error": "Holdings need etf_ticker, holding_ticker, weight.", "rows": []}
    rows = []
    for _, r in df.iterrows():
        etf = str(r.get("etf_ticker", "")).upper().strip()
        ht = str(r.get("holding_ticker", "")).upper().strip()
        if not etf or not ht or etf == "NAN":
            continue
        w = r.get("weight")
        try:
            w = float(w)
            if w > 1.5:
                w = w / 100.0
        except (TypeError, ValueError):
            w = None
        rows.append(
            {
                "etf": etf,
                "holding": ht,
                "name": "" if pd.isna(r.get("holding_name")) else str(r.get("holding_name")),
                "weight": w,
            }
        )
    return {"ok": True, "rows": rows, "source": USER_UPLOADED, "at": utc_now()}


def parse_financials(file_or_text, filename: str = "") -> dict:
    df = _norm_cols(_read_table(file_or_text, filename))
    if df.empty or "ticker" not in df.columns:
        return {"ok": False, "error": "Financials need a ticker column.", "by_ticker": {}}
    by = {}
    for _, r in df.iterrows():
        t = str(r.get("ticker")).upper().strip()
        rec = {c: (None if pd.isna(r[c]) else r[c]) for c in df.columns if c != "ticker"}
        rec["_source"] = USER_UPLOADED
        rec["_at"] = utc_now()
        by[t] = rec
    return {"ok": True, "by_ticker": by}


def parse_research(file_or_text, filename: str = "") -> dict:
    df = _norm_cols(_read_table(file_or_text, filename))
    if df.empty:
        return {"ok": False, "error": "Empty research file.", "rows": []}
    rows = df.to_dict("records")
    return {"ok": True, "rows": rows, "source": USER_UPLOADED}


def _valid_date(ds: str) -> bool:
    if len(ds) < 10:
        return False
    parts = ds[:10].split("-")
    if len(parts) != 3:
        return False
    y, m, d = parts
    return len(y) == 4 and y.isdigit() and m.isdigit() and d.isdigit()
