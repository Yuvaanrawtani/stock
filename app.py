from __future__ import annotations
import sys
sys.path.append('.')
import sys
sys.path.append('.')
"""WInS Investment Research Engine — Streamlit app (Thesis Tension for Laura Gao)."""

from __future__ import annotations

import json
from io import StringIO

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.bond_analysis import is_bond
from src.case import (
    CLIENT_NAME,
    LAURA_ROLES,
    PHILOSOPHY,
    TENSION_LINE,
    WINS_NOT_LAURA,
    capital_clock_emphasis,
)
from src.country import score_country
from src.data_engine import (
    parse_financials,
    parse_holdings,
    parse_prices,
    parse_research,
    parse_universe,
)
from src.data_quality import quality_rows
from src.demo import load_demo
from src.engine import data_mode, datapoints, holdings_quality_by_etf, returns_map
from src.explain import INFO
from src.funding import path_summary, project_path, reserve_requirement
from src.industry import analyze_industry
from src.ips import build_ips
from src.markowitz import apply_group_caps, efficient_frontier, optimize
from src.metrics import correlation_matrix
from src.ml import walk_forward_ridge
from src.monte_carlo import simulate
from src.portfolio import derive_engines, historical_portfolio_stats
from src.reports import build_report
from src.scenario_engine import run_scenarios
from src.scoring import FUNNEL_STAGES, min_max_rank, run_funnel, weighted_score
from src.sentiment import tension_from_sentiment
from src.store import default_state, load_state, save_state
from src.thesis_engine import bucket_half_life, completeness, default_card, dna_vector, explain_decision
from src.trading import new_trade
from src.trading_notes import analyze_three, new_note
from src.universe import classify_asset, wins_gate
from src.valuation import valuation_pack

st.set_page_config(page_title="WInS Thesis Tension Engine", layout="wide")

PCT = {
    "daily_return",
    "monthly_return",
    "ann_return",
    "cagr",
    "volatility",
    "alpha",
    "max_drawdown",
    "dividend_yield",
    "profit_margin",
    "roe",
    "expense_ratio",
    "sharpe",
}


def S():
    if "S" not in st.session_state:
        st.session_state.S = load_state()
        if not st.session_state.S.get("u"):
            demo = load_demo()
            st.session_state.S["u"] = demo["u"]
            st.session_state.S["px"] = demo["px"]
            st.session_state.S["src"] = demo["src"]
            st.session_state.S["at"] = demo["at"]
            st.session_state.S["sample"] = True
            st.session_state.S["log"] = [demo["note"]]
            st.session_state.S["last"] = demo["at"].get("SPY") if isinstance(demo["at"], dict) else None
    return st.session_state.S


def persist():
    save_state(S())


def money(v):
    if v is None:
        return "N/A"
    return f"${v:,.0f}"


def fmt(k, v):
    if v is None:
        return "N/A — unavailable"
    if k == "last_close":
        return f"{v:.2f}"
    if k in PCT or (isinstance(v, float) and k in ("sharpe",)):
        if k == "sharpe" or k == "beta" or k == "correlation" or k == "r_squared":
            return f"{v:.2f}"
        if k in PCT and k != "sharpe":
            return f"{v*100:.1f}%"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def banner(label):
    if "HIGH" in label:
        st.success(f"Result confidence: {label}")
    elif "PARTIAL" in label:
        st.warning(f"Result confidence: {label} — demo data can never be HIGH CONFIDENCE.")
    else:
        st.error(f"Result confidence: {label}")


def metric_table(cards: dict):
    rows = []
    for k, cell in cards.items():
        if not isinstance(cell, dict) or "v" not in cell:
            continue
        src = cell.get("source") or cell.get("st")
        rows.append(
            {
                "metric": k,
                "value": fmt(k, cell["v"]),
                "source": src,
                "date": cell.get("at") or "N/A",
                "confidence": "demo" if cell.get("st") == "DEMO" else "uploaded/model",
                "limitations": "DEMO DATA" if cell.get("st") == "DEMO" else "",
            }
        )
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def keepers():
    s = S()
    return [u for u in s["u"] if (s.get("dec") or {}).get(u["t"], {}).get("d") in ("Keep", "INVEST")]


# ---------- pages ----------

def page_home():
    s = S()
    st.title("WInS Investment Research Engine")
    st.caption(f"Client: {CLIENT_NAME} · Virtual competition system · No live brokerage")
    st.info(PHILOSOPHY)
    st.write(f"**Strategy line:** {TENSION_LINE}")
    st.warning(WINS_NOT_LAURA)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Universe", len(s["u"]))
    c2.metric("Data mode", data_mode(s))
    c3.metric("As-of (Capital Clock)", s.get("as_of_year", 2027))
    c4.metric("Last refresh", s.get("last") or "never")
    if s.get("sample"):
        st.warning("USER-PROVIDED SAMPLE — NOT verified as the complete official WInS universe. Prices may be DEMO DATA.")
    clock = capital_clock_emphasis(int(s.get("as_of_year", 2027)))
    st.subheader("Capital Clock")
    st.write(clock)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=clock["proximity_to_2033"] * 100,
            title={"text": "Proximity to 2033 (%)"},
            gauge={"axis": {"range": [0, 100]}},
        )
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        """
The system does **not** pick ETFs because they score highly.

It asks: durable thesis + market tension + catalyst + invalidation + fundamentals + valuation
+ scenario resilience + appropriate risk + a job for Laura + 2033–2042 funding compatibility.
"""
    )


def page_data():
    s = S()
    st.header("DATA")
    st.write("Live prices cannot be assumed. Upload CSVs/XLSX, paste tables, or load DEMO DATA (labelled).")
    a, b, c = st.columns(3)
    if a.button("Load demo data", type="primary"):
        demo = load_demo()
        s["u"] = demo["u"]
        s["px"] = demo["px"]
        s["src"] = demo["src"]
        s["at"] = demo["at"]
        s["sample"] = True
        s["ex"] = {}
        s["dec"] = {}
        s["pw"] = {}
        s["ml"] = None
        s["log"] = [demo["note"]]
        persist()
        st.rerun()
    if b.button("Clear all data"):
        st.session_state.S = default_state()
        persist()
        st.rerun()

    st.subheader("WInS universe")
    uf = st.file_uploader("Universe CSV/XLSX", type=["csv", "xlsx", "xls"], key="uni")
    paste_u = st.text_area("Or paste universe CSV", height=80)
    if st.button("Load universe") and (uf or paste_u.strip()):
        src = uf if uf else paste_u
        name = uf.name if uf else "paste.csv"
        r = parse_universe(src, name)
        if not r["ok"]:
            st.error(r["error"])
        else:
            s["u"] = r["rows"]
            s["ex"] = {row["t"]: row.get("x") or {} for row in r["rows"]}
            s["dupU"] = r.get("dup", 0)
            s["sample"] = False
            s["at"]["_u"] = r["at"]
            s["log"] = [f"Loaded universe: {r['n']} securities, {s['dupU']} duplicates skipped."]
            persist()
            st.success(s["log"][0])

    st.subheader("Prices")
    pf = st.file_uploader("Prices CSV/XLSX", type=["csv", "xlsx", "xls"], key="px")
    paste_p = st.text_area("Or paste prices CSV", height=80)
    if st.button("Load prices") and (pf or paste_p.strip()):
        src = pf if pf else paste_p
        name = pf.name if pf else "paste.csv"
        r = parse_prices(src, name, source="upload")
        if not r["ok"]:
            st.error(r["error"])
        else:
            s["px"].update(r["px"])
            for t in r["px"]:
                s["src"][t] = "upload"
                s["at"][t] = r["at"]
            s["rej"] = r["rej"]
            s["dupP"] = r["dup"]
            s["log"] = [f"Loaded prices for {len(r['px'])} tickers; rejected {r['rej']} invalid rows."]
            persist()
            st.success(s["log"][0])

    st.subheader("Holdings / financials / research")
    h = st.file_uploader("Holdings CSV", type=["csv", "xlsx"], key="hld")
    if h and st.button("Load holdings"):
        r = parse_holdings(h, h.name)
        if r["ok"]:
            s["holdings"] = r["rows"]
            persist()
            st.success(f"{len(r['rows'])} holding rows")
        else:
            st.error(r["error"])
    fin = st.file_uploader("Company financials CSV", type=["csv", "xlsx"], key="fin")
    if fin and st.button("Load financials"):
        r = parse_financials(fin, fin.name)
        if r["ok"]:
            s["fin"] = r["by_ticker"]
            persist()
            st.success(f"Financials for {len(r['by_ticker'])} tickers")
        else:
            st.error(r["error"])
    res = st.file_uploader("Research records CSV", type=["csv", "xlsx"], key="res")
    if res and st.button("Load research"):
        r = parse_research(res, res.name)
        if r["ok"]:
            s["research"] = r["rows"]
            persist()
            st.success(f"{len(r['rows'])} research rows")

    st.subheader("Manual security")
    with st.form("manual"):
        t = st.text_input("Ticker").upper()
        n = st.text_input("Name")
        ac = st.text_input("Asset class")
        wins = st.selectbox("WINS_APPROVED", ["UNKNOWN", "TRUE", "FALSE"])
        if st.form_submit_button("Add/update security") and t:
            s["u"] = [u for u in s["u"] if u["t"] != t] + [
                {"t": t, "n": n, "c": ac, "a": {}, "x": {}, "wins_approved": wins}
            ]
            persist()
            st.success(t)

    st.subheader("Settings")
    s["cfg"]["rf"] = st.number_input("Risk-free rate", value=float(s["cfg"]["rf"]), step=0.005, format="%.3f")
    s["cfg"]["bench"] = st.text_input("Benchmark ticker", value=s["cfg"]["bench"]).upper()
    s["cfg"]["lb"] = int(st.number_input("Lookback days", value=int(s["cfg"]["lb"]), step=30))
    s["as_of_year"] = int(st.number_input("Capital Clock year", value=int(s.get("as_of_year", 2027)), min_value=2027, max_value=2042))
    persist()
    st.code("\n".join(s.get("log") or []))


def page_universe():
    s = S()
    D = datapoints(s)
    st.header("UNIVERSE")
    st.write("The WInS universe is authoritative. External ETFs are not assumed eligible.")
    rows = []
    for u in s["u"]:
        g = wins_gate(u)
        rows.append(
            {
                "ticker": u["t"],
                "name": u.get("n"),
                "asset_class": u.get("c"),
                "WINS_APPROVED": u.get("wins_approved", "UNKNOWN"),
                "kind": classify_asset(u.get("c"), u["t"]),
                "has_prices": u["t"] in s.get("px", {}),
                "price_source": s.get("src", {}).get(u["t"], "N/A"),
                "gate": g["reason"],
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    q = st.text_input("Search", value=s["f"].get("q", ""))
    s["f"]["q"] = q
    persist()


def _funnel_and_scores():
    s = S()
    D = datapoints(s)
    # legacy min-max ranks for price metrics
    keys = ["sharpe", "cagr", "alpha", "volatility", "max_drawdown"]
    ranks = {}
    for k in keys:
        vals = {u["t"]: D[u["t"]].get(k, {}).get("v") if isinstance(D[u["t"]].get(k), dict) else None for u in s["u"]}
        ranks[k] = min_max_rank({t: v for t, v in vals.items() if v is not None}, low_better=(k in ("volatility", "max_drawdown")))
    SC = {}
    for u in s["u"]:
        t = u["t"]
        parts = {
            "thesis_strength": None,
            "thesis_durability": None,
            "market_tension": None,
            "catalyst": None,
            "fundamental_quality": None,
            "valuation": None,
            "risk": (D[t].get("_risk") or {}).get("score"),
            "diversification": None,
            "scenario_resilience": None,
            "laura_alignment": None,
            "funding_compatibility": None,
            "data_confidence": 20 if s.get("src", {}).get(t) == "demo" else (70 if s.get("src", {}).get(t) == "upload" else None),
        }
        # fill from thesis completeness
        card = s.get("thesis", {}).get(t) or {}
        comp = completeness(card) if card else {"missing": ["thesis"], "complete": False}
        if card.get("thesis"):
            parts["thesis_strength"] = 60 if not comp["complete"] else 75
        hl = bucket_half_life(card.get("thesis_half_life_years"), card.get("half_life_override") or None)
        parts["thesis_durability"] = {"SHORT": 30, "MEDIUM": 55, "LONG": 75, "STRUCTURAL": 90}.get(hl["bucket"])
        if card.get("market_tension") or card.get("what_thesis_says"):
            parts["market_tension"] = 65
        if card.get("catalyst"):
            parts["catalyst"] = 60
        if card.get("laura_role"):
            parts["laura_alignment"] = 70
        if card.get("bear") and card.get("base") and card.get("bull"):
            parts["scenario_resilience"] = 65
        ms = s.get("manual_scores", {}).get(t) or {}
        for k, v in ms.items():
            if v is not None and v != "":
                try:
                    parts[k] = float(v)
                except ValueError:
                    pass
        # blend in ranked price quality as a partial fundamental proxy only when no company financials
        if parts["fundamental_quality"] is None:
            rs = [ranks[k].get(t) for k in ("sharpe", "cagr") if t in ranks[k]]
            if rs:
                parts["fundamental_quality"] = sum(rs) / len(rs)
        SC[t] = weighted_score(parts, s.get("score_weights"))
        SC[t]["parts"] = parts
        SC[t]["ranks"] = {k: ranks[k].get(t) for k in ranks}

    def reject(stage, sec):
        t = sec["t"]
        d = D[t]
        f = s["f"]
        if stage == "WInS universe":
            g = wins_gate(sec)
            if not g["pass"]:
                return g["reason"]
            return None
        if stage == "Country / Geography":
            want = f["a"].get("country")
            if want and str(sec.get("a", {}).get("country") or "") != want:
                return f"Country filter {want}"
            return None
        if stage == "Industry / Theme":
            for key in ("sector", "industry", "theme"):
                want = f["a"].get(key)
                if want and str(sec.get("a", {}).get(key) or "") != want:
                    return f"{key} filter {want}"
            q = f.get("q") or ""
            if q and q.lower() not in (sec["t"] + " " + (sec.get("n") or "")).lower():
                return "Search filter"
            return None
        if stage == "ETF/Security quality":
            lo, hi = f.get("lo", {}), f.get("hi", {})
            for k in ("sharpe", "cagr", "volatility", "max_drawdown", "expense_ratio"):
                if lo.get(k) in (None, "") and hi.get(k) in (None, ""):
                    continue
                cell = d.get(k)
                if not cell:
                    return f"Missing {k} (missing data = excluded at this gate)"
                v = cell["v"] * (100 if k in PCT and k != "sharpe" else 1)
                if k == "sharpe":
                    v = cell["v"]
                if lo.get(k) not in (None, "") and v < float(lo[k]):
                    return f"{k} below min"
                if hi.get(k) not in (None, "") and v > float(hi[k]):
                    return f"{k} above max"
            return None
        if stage == "Valuation":
            lo, hi = f.get("lo", {}), f.get("hi", {})
            k = "pe_ratio"
            if lo.get(k) not in (None, "") or hi.get(k) not in (None, ""):
                cell = d.get(k)
                if not cell:
                    return "Missing P/E at valuation gate"
                v = cell["v"]
                if lo.get(k) not in (None, "") and v < float(lo[k]):
                    return "P/E below min"
                if hi.get(k) not in (None, "") and v > float(hi[k]):
                    return "P/E above max"
            return None
        if stage == "Risk":
            if f.get("lo", {}).get("beta") not in (None, "") or f.get("hi", {}).get("beta") not in (None, ""):
                cell = d.get("beta")
                if not cell:
                    return "Missing beta"
                v = cell["v"]
                if f["lo"].get("beta") not in (None, "") and v < float(f["lo"]["beta"]):
                    return "beta below min"
                if f["hi"].get("beta") not in (None, "") and v > float(f["hi"]["beta"]):
                    return "beta above max"
            return None
        if stage == "Underlying holdings quality":
            return None  # informational; do not auto-reject without data
        if stage == "Thesis Tension":
            card = s.get("thesis", {}).get(t)
            if (s.get("dec") or {}).get(t, {}).get("d") == "Remove":
                return "Team marked Remove"
            return None
        if stage == "Human review":
            if (s.get("dec") or {}).get(t, {}).get("d") == "Remove":
                return "Human review: Remove"
            return None
        return None

    F = run_funnel(s["u"], reject)
    return D, SC, F


def page_country():
    s = S()
    st.header("COUNTRY")
    st.write("Country → Industry → Security. One weak metric is **not** an automatic reject.")
    countries = sorted({str(u.get("a", {}).get("country")) for u in s["u"] if u.get("a", {}).get("country")})
    st.write("Countries present in universe attributes:", countries or "N/A — upload universe columns or enter below.")
    name = st.text_input("Country name")
    de = st.selectbox("Developed / emerging", ["", "developed", "emerging"])
    gdp = st.text_input("GDP growth (team/source — not invented)")
    evidence = st.text_area("Evidence")
    source = st.text_input("Source")
    sdate = st.text_input("Source date")
    if st.button("Score country") and name:
        row = {
            "country": name,
            "developed_emerging": de,
            "gdp_growth": gdp,
            "evidence": evidence,
            "source": source,
            "source_date": sdate,
        }
        s["countries"][name] = score_country(row)
        persist()
    if s.get("countries"):
        st.json(s["countries"])


def page_industry():
    s = S()
    st.header("INDUSTRY / THEME")
    st.write("Porter / SWOT / STEEPLE / McKinsey 7S / ESG are evidence slots. Blank ≠ completed analysis.")
    industry = st.text_input("Industry or theme")
    evidence = st.text_area("Evidence (required for any score)")
    source = st.text_input("Source", key="indsrc")
    porter = {f"porter_{k}": st.text_area(f"Porter: {k}", key=f"p{k}") for k in ["rivalry", "new_entrants", "supplier_power", "buyer_power", "substitutes"]}
    if st.button("Analyze industry") and industry:
        row = {"industry": industry, "evidence": evidence, "source": source, **porter}
        s["industries"][industry] = analyze_industry(row)
        persist()
    if s.get("industries"):
        st.json(s["industries"])


def page_screener_like(title):
    s = S()
    D, SC, F = _funnel_and_scores()
    Q = quality_rows(s["u"], D, s.get("src") or {})
    st.header(title)
    banner(Q["all"])
    st.subheader("Filters")
    s["f"]["q"] = st.text_input("Search ticker/name", value=s["f"].get("q", ""))
    cols = st.columns(5)
    for i, k in enumerate(["sharpe", "cagr", "volatility", "max_drawdown", "pe_ratio"]):
        with cols[i]:
            s["f"].setdefault("lo", {})
            s["f"].setdefault("hi", {})
            s["f"]["lo"][k] = st.text_input(f"{k} min", value=str(s["f"]["lo"].get(k) or ""))
            s["f"]["hi"][k] = st.text_input(f"{k} max", value=str(s["f"]["hi"].get(k) or ""))
    persist()
    fig = px.funnel(pd.DataFrame([{"stage": x["n"], "remaining": x["remaining"]} for x in F["st"]]), x="remaining", y="stage", title="Screening funnel")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(pd.DataFrame(F["st"]), use_container_width=True, hide_index=True)
    if F["log"]:
        st.subheader("Rejection log")
        st.dataframe(pd.DataFrame(F["log"]), use_container_width=True, hide_index=True)
    rows = []
    for u in F["L"]:
        t = u["t"]
        rows.append(
            {
                "ticker": t,
                "name": u.get("n"),
                "class": u.get("c"),
                "WINS": u.get("wins_approved"),
                "score": None if SC[t]["score"] is None else round(SC[t]["score"], 1),
                "CAGR": fmt("cagr", D[t].get("cagr", {}).get("v") if isinstance(D[t].get("cagr"), dict) else None),
                "Vol": fmt("volatility", D[t].get("volatility", {}).get("v") if isinstance(D[t].get("volatility"), dict) else None),
                "Sharpe": fmt("sharpe", D[t].get("sharpe", {}).get("v") if isinstance(D[t].get("sharpe"), dict) else None),
                "team": (s.get("dec") or {}).get(t, {}).get("d") or "—",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    tickers = [u["t"] for u in s["u"]]
    s["sel"] = st.selectbox("Open security", [""] + tickers, index=tickers.index(s["sel"]) + 1 if s.get("sel") in tickers else 0)
    persist()
    t = s.get("sel")
    if t:
        show_security(t, D, SC)


def show_security(t, D, SC):
    s = S()
    u = next(x for x in s["u"] if x["t"] == t)
    st.subheader(f"{t} — {u.get('n') or ''} ({u.get('c')})")
    st.caption(f"WINS_APPROVED={u.get('wins_approved')} · kind={classify_asset(u.get('c'), t)} · prices={s.get('src', {}).get(t, 'N/A')}")
    z = SC[t]
    st.write("**Why this score?** Weights are visible. Score ≠ INVEST.")
    if z["rows"]:
        st.dataframe(pd.DataFrame(z["rows"]), use_container_width=True, hide_index=True)
        st.metric("Weighted score", f"{z['score']:.1f}" if z["score"] is not None else "N/A")
    if z["missing"]:
        st.caption("Not scored (missing, weights re-spread): " + ", ".join(z["missing"]))
    st.markdown("**Editable score weights**")
    wcols = st.columns(4)
    for i, (k, v) in enumerate(list(s["score_weights"].items())):
        s["score_weights"][k] = wcols[i % 4].number_input(k, value=float(v), step=0.01, key=f"w{k}")
    persist()
    st.markdown("**Manual component override (still not a BUY)**")
    ms = s.setdefault("manual_scores", {}).setdefault(t, {})
    for k in list(s["score_weights"]):
        ms[k] = st.text_input(f"manual {k}", value=str(ms.get(k) or ""), key=f"ms{t}{k}")
    persist()
    d = s.setdefault("dec", {}).get(t) or {}
    choice = st.radio("Team classification", ["", "Keep", "Watch", "Remove", "INVEST", "REJECT"], index=["", "Keep", "Watch", "Remove", "INVEST", "REJECT"].index(d.get("d") or ""))
    why = st.text_input("Reason (required for overrides/report)", value=d.get("why") or "")
    if st.button("Save decision"):
        s["dec"][t] = {"d": choice or "Watch", "why": why}
        if why:
            s.setdefault("overrides", []).append({"ticker": t, "decision": choice, "reason": why})
        persist()
        st.success("Saved")
    st.markdown("**Price & uploaded metrics**")
    metric_table(D[t])
    with st.expander("What does this mean?"):
        for k, txt in INFO.items():
            st.markdown(f"**{k}** — {txt}")
    if D[t].get("_bond"):
        st.markdown("**Fixed-income pack**")
        st.json(D[t]["_bond"])
    if D[t].get("_piotroski"):
        st.markdown("**Company-level quality (not an ETF score)**")
        st.json({k: D[t][k] for k in ("_piotroski", "_beneish", "_altman", "_sgr", "_growth") if k in D[t]})
    hq = holdings_quality_by_etf(s).get(t)
    if hq:
        st.markdown("**ETF Quality Exposure (underlying)**")
        st.json(hq)


def page_etf():
    page_screener_like("ETF ANALYSIS")


def page_fundamentals():
    s = S()
    st.header("FUNDAMENTALS")
    st.write("Company ratios stay at company level. ETF views are *exposure* aggregates.")
    D = datapoints(s)
    t = st.selectbox("Ticker", [u["t"] for u in s["u"]])
    if not t:
        return
    u = next(x for x in s["u"] if x["t"] == t)
    if classify_asset(u.get("c"), t) != "stock" and not (s.get("fin") or {}).get(t):
        st.info("No company financials for this ticker. Upload financial-data CSV. Do not treat ETF wrapper as a company.")
    show = D[t]
    for k in ("_piotroski", "_beneish", "_altman", "_sgr", "_growth"):
        if show.get(k):
            st.subheader(k)
            st.json(show[k])
    hq = holdings_quality_by_etf(s)
    if hq:
        st.subheader("Underlying holdings quality by ETF")
        pick = st.selectbox("ETF with holdings", list(hq))
        st.json(hq[pick])
        pe = hq[pick].get("piotroski_exposure")
        if pe:
            st.caption(hq[pick]["label"])


def page_valuation():
    s = S()
    st.header("VALUATION")
    st.write("Every model is a **MODEL ESTIMATE**, not true value. Assumptions are exposed.")
    t = st.selectbox("Ticker", [u["t"] for u in s["u"]], key="vt")
    D = datapoints(s)
    price = D[t].get("last_close", {}).get("v") if isinstance(D[t].get("last_close"), dict) else None
    fin = s.get("fin", {}).get(t) or {}
    extras = s.get("ex", {}).get(t) or {}
    c1, c2, c3 = st.columns(3)
    px = c1.number_input("Price", value=float(price or 0) or 0.0)
    eps = c2.number_input("EPS", value=float(fin.get("eps") or extras.get("eps") or 0))
    g = c3.number_input("Growth (decimal)", value=float(fin.get("eps_growth") or 0.08))
    d1 = st.number_input("Next dividend D1 (Gordon)", value=float(fin.get("d1") or 0))
    k = st.number_input("Discount rate k", value=0.08)
    gg = st.number_input("Perpetuity g", value=0.03)
    pack = valuation_pack(
        {
            "price": px or None,
            "eps": eps or None,
            "eps_growth": g or None,
            "forward_eps": fin.get("forward_eps"),
            "bvps": fin.get("bvps"),
            "sps": fin.get("sps"),
            "ev": fin.get("ev"),
            "ebitda": fin.get("ebitda"),
            "sales": fin.get("sales"),
            "fcf": fin.get("fcf"),
            "market_cap": extras.get("market_cap") or fin.get("market_cap"),
            "d1": d1 or None,
            "k": k,
            "g": gg,
            "dividends": [d1] * 5 if d1 else [],
        }
    )
    st.json({k: (v.as_dict() if hasattr(v, "as_dict") else v) for k, v in pack.items()})


def page_risk():
    s = S()
    st.header("RISK")
    D, SC, F = _funnel_and_scores()
    rows = []
    for u in s["u"]:
        d = D[u["t"]]
        rs = d.get("_risk") or {}
        rows.append(
            {
                "ticker": u["t"],
                "vol": d.get("volatility", {}).get("v") if isinstance(d.get("volatility"), dict) else None,
                "beta": d.get("beta", {}).get("v") if isinstance(d.get("beta"), dict) else None,
                "max_dd": d.get("max_drawdown", {}).get("v") if isinstance(d.get("max_drawdown"), dict) else None,
                "r2": d.get("r_squared", {}).get("v") if isinstance(d.get("r_squared"), dict) else None,
                "security_risk_score": rs.get("score"),
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    ks = [u["t"] for u in keepers() if u["t"] in s.get("px", {})]
    rm = returns_map(s, ks)
    if len(rm) >= 2:
        names = list(rm)
        n = min(len(rm[t]) for t in names)
        mat = correlation_matrix({t: rm[t][-n:] for t in names})
        if mat is not None:
            fig = px.imshow(mat, x=names, y=names, title="Correlation matrix (Keep/INVEST names)")
            st.plotly_chart(fig, use_container_width=True)
        P = historical_portfolio_stats(rm, {t: s.get("pw", {}).get(t, 1) for t in names}, s["cfg"]["rf"])
        if P:
            st.metric("Portfolio risk score (vol-based)", f"{min(100, P['vol']/0.25*100):.0f}")
            st.write(P["label"])


def page_sentiment():
    s = S()
    st.header("SENTIMENT")
    st.write("Sentiment creates **market tension**. It cannot override fundamentals.")
    t = st.selectbox("Ticker", [u["t"] for u in s["u"]], key="sentt")
    extras = s.get("ex", {}).get(t) or {}
    sent = extras.get("news_sentiment")
    try:
        sent = float(sent) if sent is not None else None
    except ValueError:
        sent = None
    sent = st.number_input("News/analyst sentiment (−1 to 1), blank via 99 = N/A", value=float(sent if sent is not None else 99))
    sent_v = None if sent == 99 else sent
    mom = st.number_input("Momentum (decimal, 99=N/A)", value=99.0)
    mom_v = None if mom == 99 else mom
    q = st.number_input("Fundamental quality 0–100 (99=N/A)", value=99.0)
    qv = None if q == 99 else q
    rich = st.checkbox("Valuation appears rich (team view)")
    st.json(tension_from_sentiment(qv, rich, sent_v, mom_v))


def page_thesis():
    s = S()
    st.header("THESIS TENSION")
    st.info(TENSION_LINE)
    t = st.selectbox("Candidate ticker", [u["t"] for u in s["u"]], key="tht")
    card = s.setdefault("thesis", {}).setdefault(t, default_card(t))
    card["thesis"] = st.text_area("1. THESIS — Why should this perform well?", value=card.get("thesis") or "")
    card["thesis_half_life_years"] = st.number_input("Thesis half-life (years of validity)", value=float(card.get("thesis_half_life_years") or 0) or 0.0)
    card["half_life_override"] = st.selectbox("Half-life override", ["", "SHORT", "MEDIUM", "LONG", "STRUCTURAL"], index=["", "SHORT", "MEDIUM", "LONG", "STRUCTURAL"].index(card.get("half_life_override") or ""))
    card["half_life_reason"] = st.text_input("Why this half-life?", value=card.get("half_life_reason") or "")
    st.caption(str(bucket_half_life(card["thesis_half_life_years"] or None, card["half_life_override"] or None)))
    card["what_thesis_says"] = st.text_area("WHAT OUR THESIS SAYS", value=card.get("what_thesis_says") or "")
    card["what_market_says"] = st.text_area("WHAT THE MARKET / OTHER SIGNALS SUGGEST", value=card.get("what_market_says") or "")
    card["market_tension"] = st.text_area("3. MARKET TENSION (disagreement, not auto-reject)", value=card.get("market_tension") or "")
    card["catalyst"] = st.text_area("4. CATALYST", value=card.get("catalyst") or "")
    card["catalyst_timeframe"] = st.text_input("Catalyst timeframe", value=card.get("catalyst_timeframe") or "")
    card["catalyst_evidence"] = st.text_input("Catalyst evidence", value=card.get("catalyst_evidence") or "")
    card["catalyst_confidence"] = st.text_input("Catalyst confidence", value=card.get("catalyst_confidence") or "")
    card["catalyst_source"] = st.text_input("Catalyst source", value=card.get("catalyst_source") or "")
    card["invalidation"] = st.text_area("5. INVALIDATION (not a price drop)", value=card.get("invalidation") or "")
    card["bear"] = st.text_area("6. BEAR CASE", value=card.get("bear") or "")
    card["base"] = st.text_area("7. BASE CASE", value=card.get("base") or "")
    card["bull"] = st.text_area("8. BULL CASE", value=card.get("bull") or "")
    _roles = [""] + list(LAURA_ROLES)
    _ri = _roles.index(card.get("laura_role")) if card.get("laura_role") in _roles else 0
    card["laura_role"] = st.selectbox("9. LAURA'S ROLE", _roles, index=_ri)
    card["laura_role_why"] = st.text_area("Why this role for Laura", value=card.get("laura_role_why") or "")
    st.write("10. CAPITAL CLOCK", capital_clock_emphasis(int(s.get("as_of_year", 2027))))
    card["final_decision"] = st.selectbox("11. FINAL DECISION", ["", "INVEST", "WATCH", "REJECT"], index=["", "INVEST", "WATCH", "REJECT"].index(card.get("final_decision") or ""))
    card["decision_why"] = st.text_area("Decision explanation", value=card.get("decision_why") or "")
    if st.button("Save thesis card"):
        if card.get("final_decision") and not card.get("decision_why"):
            st.error("Override/decision requires a reason.")
        else:
            s["thesis"][t] = card
            persist()
            st.success("Saved — TEAM INPUT stored, nothing invented.")
    D, SC, F = _funnel_and_scores()
    dna = dna_vector(card, SC[t]["parts"])
    st.subheader("Thesis DNA")
    labels = [k for k, v in dna.items() if isinstance(v, (int, float))]
    values = [dna[k] for k in labels]
    if labels:
        fig = go.Figure(go.Scatterpolar(r=values, theta=labels, fill="toself", name=t))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), title="Thesis DNA (N/A axes omitted)")
        st.plotly_chart(fig, use_container_width=True)
    st.json(explain_decision(card, SC[t]["score"], int(s.get("as_of_year", 2027))))
    st.caption("Missing qualitative facts stay N/A. The engine does not invent catalysts or company news.")


def page_scenarios():
    s = S()
    st.header("SCENARIOS / STRESS")
    fc = s["fc"]
    st.write("Edit assumptions. Does Laura still meet all ten payments?")
    results = run_scenarios(fc["r"], fc["inf"], fc["idx"], fc["rf"], s["sc"])
    df = pd.DataFrame(
        [
            {
                "scenario": r["name"],
                "2033 balance": r["balance_2033_pre_payment"],
                "reserve": r["reserve_requirement"],
                "shortfall": r["total_shortfall"],
                "ending": r["ending_wealth"],
                "all 10 funded": r["all_ten_funded"],
                "status": r["status"],
            }
            for r in results
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    fig = px.bar(df, x="scenario", y="2033 balance", title="2033 pre-payment balance by scenario")
    st.plotly_chart(fig, use_container_width=True)
    for i, sc in enumerate(s["sc"]):
        with st.expander(sc["n"]):
            sc["dr"] = st.number_input("Return shift", value=float(sc.get("dr") or 0), key=f"dr{i}")
            sc["sy"] = st.number_input("Shock year", value=int(sc.get("sy") or 2029), key=f"sy{i}")
            sc["sr"] = st.number_input("Shock return", value=float(sc.get("sr") or 0), key=f"sr{i}")
            st.write(results[i]["causal_chain"])
            if results[i]["total_shortfall"] > 0:
                st.error(f"Shortfall {money(results[i]['total_shortfall'])}. Caused by the return/shock/inflation path above, not by WInS simulation P&L.")
    persist()


def page_portfolio():
    s = S()
    st.header("PORTFOLIO")
    ks = keepers()
    st.write(f"Working set from Keep/INVEST: {len(ks)} names. Weights default equal.")
    if len(ks) < 2:
        st.warning("Mark at least two securities Keep or INVEST.")
        return
    tickers = [u["t"] for u in ks]
    for t in tickers:
        s.setdefault("pw", {})
        s["pw"][t] = st.number_input(f"{t} weight (unnormalized)", value=float(s["pw"].get(t) or 1.0), key=f"pw{t}")
    persist()
    rm = returns_map(s, tickers)
    P = historical_portfolio_stats(rm, {t: s["pw"].get(t, 1) for t in tickers}, s["cfg"]["rf"])
    if not P:
        st.error("Need overlapping price history.")
        return
    c = st.columns(5)
    c[0].metric("Hist. return", f"{P['ret']*100:.1f}%")
    c[1].metric("Vol", f"{P['vol']*100:.1f}%")
    c[2].metric("Sharpe", f"{P['sharpe']:.2f}" if P["sharpe"] else "N/A")
    c[3].metric("Max DD", f"{P['dd']*100:.1f}%")
    c[4].metric("Avg corr", f"{P['avg_corr']:.2f}" if P["avg_corr"] is not None else "N/A")
    st.caption(P["label"] + " · " + data_mode(s))
    fig = px.pie(pd.DataFrame(P["rows"]), names="t", values="w", title="Allocation")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(pd.DataFrame(P["rows"]), use_container_width=True, hide_index=True)
    fig2 = px.bar(pd.DataFrame(P["rows"]), x="t", y="rc", title="Portfolio risk contribution")
    st.plotly_chart(fig2, use_container_width=True)
    mc = simulate(n=min(2000, int(s["fc"]["n"])), mu=s["fc"]["r"], sd=s["fc"]["sd"], inflation=s["fc"]["inf"], indexed=s["fc"]["idx"], rf=s["fc"]["rf"])
    stress = run_scenarios(s["fc"]["r"], s["fc"]["inf"], s["fc"]["idx"], s["fc"]["rf"], s["sc"])
    short = any(x["total_shortfall"] > 0 for x in stress)
    hl_years = []
    for u in ks:
        card = s.get("thesis", {}).get(u["t"]) or {}
        if card.get("thesis_half_life_years"):
            hl_years.append(float(card["thesis_half_life_years"]))
    engines = derive_engines(int(s.get("as_of_year", 2027)), mc["p_all_funded"], P["vol"], sum(hl_years) / len(hl_years) if hl_years else None, short)
    st.subheader("Growth Engine vs Commitment Engine")
    st.json(engines)
    fig3 = px.pie(names=["Growth engine", "Commitment engine"], values=[engines["growth_engine"], engines["commitment_engine"]])
    st.plotly_chart(fig3, use_container_width=True)


def page_markowitz():
    s = S()
    st.header("MARKOWITZ")
    st.write("Mean-variance is a **construction tool**, not the decision-maker. Client constraints still apply.")
    ks = keepers()
    if len(ks) < 2:
        st.warning("Need ≥2 Keep/INVEST names with prices.")
        return
    tickers = [u["t"] for u in ks]
    rm = returns_map(s, tickers)
    names = [t for t in tickers if t in rm]
    if len(names) < 2:
        st.error("Insufficient overlapping returns.")
        return
    n = min(len(rm[t]) for t in names)
    R = np.vstack([rm[t][-n:] for t in names])
    mu = R.mean(axis=1) * 252
    cov = np.cov(R, ddof=1) * 252
    max_w = st.slider("Max position size", 0.1, 1.0, 0.35)
    rf = s["cfg"]["rf"]
    front = efficient_frontier(mu, cov, rf=rf, max_weight=max_w)
    fdf = pd.DataFrame(
        [{"vol": p["vol"], "ret": p["return"], "sharpe": p["sharpe"]} for p in front["frontier"] if p.get("vol") is not None]
    )
    fig = px.scatter(fdf, x="vol", y="ret", title="Efficient frontier (MODEL ESTIMATE)")
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Max Sharpe")
    st.write(dict(zip(names, front["max_sharpe"]["weights"].round(3))))
    st.subheader("Min vol")
    st.write(dict(zip(names, front["min_vol"]["weights"].round(3))))
    tgt_r = st.number_input("Target return", value=float(np.median(mu)))
    tgt = optimize(mu, cov, rf=rf, max_weight=max_w, target_return=tgt_r, objective="target_return")
    st.write("Target-return weights", dict(zip(names, np.round(tgt["weights"], 3))))
    groups = {u["t"]: u.get("c") or "Unknown" for u in ks}
    cap = st.number_input("Max weight per asset class", value=0.8)
    capped = apply_group_caps(names, tgt["weights"], groups, {g: cap for g in set(groups.values())})
    st.write("After asset-class cap (still not a final portfolio)", dict(zip(names, np.round(capped, 3))))
    if st.button("Apply max-Sharpe weights into portfolio workspace"):
        for t, w in zip(names, front["max_sharpe"]["weights"]):
            s.setdefault("pw", {})[t] = float(w)
        persist()
        st.success("Copied. Thesis / Laura / funding still required.")


def page_funding():
    s = S()
    st.header("FUNDING")
    st.caption("Case cash flows only. WInS simulation P&L is not added or subtracted.")
    fc = s["fc"]
    fc["r"] = st.number_input("Expected annual return", value=float(fc["r"]), format="%.3f")
    fc["sd"] = st.number_input("Volatility", value=float(fc["sd"]), format="%.3f")
    fc["inf"] = st.number_input("Inflation (for optional indexing)", value=float(fc["inf"]), format="%.3f")
    fc["rf"] = st.number_input("Risk-free (reserve PV)", value=float(fc["rf"]), format="%.3f")
    fc["idx"] = st.checkbox("Index payments to inflation (OFF by default — case payments are fixed)", value=bool(fc["idx"]))
    persist()
    rows = project_path(fc["r"], fc["inf"], fc["idx"])
    summ = path_summary(rows, fc["inf"], fc["idx"], fc["rf"])
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    c = st.columns(4)
    c[0].metric("2033 pre-payment", money(summ["balance_2033_pre_payment"]))
    c[1].metric("Reserve requirement", money(summ["reserve_requirement"]))
    c[2].metric("Total shortfall", money(summ["total_shortfall"]))
    c[3].metric("Status", summ["status"])
    st.caption(summ["label"])
    fig = px.line(pd.DataFrame(rows), x="year", y="ending", title="Ending balance path (deterministic)")
    st.plotly_chart(fig, use_container_width=True)


def page_mc():
    s = S()
    st.header("MONTE CARLO")
    fc = s["fc"]
    fc["n"] = int(st.number_input("Simulations (default 5000)", value=int(fc.get("n") or 5000), min_value=100, step=500))
    persist()
    M = simulate(n=fc["n"], mu=fc["r"], sd=fc["sd"], inflation=fc["inf"], indexed=fc["idx"], rf=fc["rf"])
    st.warning(M["label"])
    c = st.columns(4)
    c[0].metric("P(all 10 payments)", f"{M['p_all_funded']*100:.1f}%")
    c[1].metric("P(shortfall)", f"{M['p_shortfall']*100:.1f}%")
    c[2].metric("Median ending wealth", money(M["ending"]["p50"]))
    c[3].metric("P10 ending", money(M["ending"]["p10"]))
    st.write("Ending wealth percentiles", M["ending"])
    st.write("2033 reserve (pre-payment) percentiles", M["reserve_2033"])
    st.write("Facility contribution range (max(0, 2033 − PV reserve))", M["facility_contribution_range_2033"])
    st.caption("Use the 2031 team discussion to talk about this range while protecting operating commitments.")
    # histogram via another sim sample for chart
    rng = np.random.default_rng(7)
    # reuse ending percentiles only for display bar
    edf = pd.DataFrame({"pctl": list(M["ending"].keys()), "value": list(M["ending"].values())})
    st.plotly_chart(px.bar(edf, x="pctl", y="value", title="Ending wealth distribution (percentiles)"), use_container_width=True)
    st.json(M["assumptions"])


def page_trading():
    s = S()
    st.header("TRADING PLANNER")
    st.write("Virtual WInS trades only. Do not trade excessively — trades implement strategy.")
    with st.form("trade"):
        t = st.text_input("Ticker").upper()
        side = st.selectbox("Side", ["buy", "sell"])
        qty = st.number_input("Quantity", value=0.0)
        px = st.number_input("Price", value=0.0)
        thesis = st.text_input("Thesis")
        reason = st.text_input("Reason for trade")
        cat = st.text_input("Catalyst")
        hl = st.text_input("Thesis half-life")
        inv = st.text_input("Invalidation")
        risk = st.text_input("Risk")
        role = st.text_input("Laura role")
        impact = st.text_input("Expected impact")
        ev = st.text_input("Evidence")
        if st.form_submit_button("Record virtual trade") and t:
            s.setdefault("trades", []).append(
                new_trade(ticker=t, side=side, quantity=qty, price=px, thesis=thesis, reason=reason, catalyst=cat, thesis_half_life=hl, invalidation=inv, risk=risk, laura_role=role, expected_impact=impact, evidence=ev)
            )
            persist()
            st.success("Recorded (virtual)")
    if s.get("trades"):
        st.dataframe(pd.DataFrame(s["trades"]), use_container_width=True, hide_index=True)


def page_notes():
    s = S()
    st.header("TRADING NOTES")
    with st.form("note"):
        ticker = st.text_input("Ticker", key="nt").upper()
        fields = {
            "what_we_did": st.text_area("WHAT DID WE DO?"),
            "why": st.text_area("WHY?"),
            "evidence": st.text_area("WHAT EVIDENCE SUPPORTED IT?"),
            "strategy_fit": st.text_area("HOW DOES IT FIT OUR STRATEGY?"),
            "risk_accepted": st.text_area("WHAT RISK DID WE ACCEPT?"),
            "what_would_prove_wrong": st.text_area("WHAT WOULD PROVE US WRONG?"),
            "what_happened": st.text_area("WHAT HAPPENED?"),
            "thesis_evolution": st.selectbox("Thesis evolution", ["", "strengthened", "remained", "weakened"]),
            "sources": st.text_input("Sources"),
        }
        if st.form_submit_button("Save note"):
            s.setdefault("notes", []).append(new_note(ticker=ticker, **fields))
            persist()
            st.success("Saved")
    notes = s.get("notes") or []
    if notes:
        st.dataframe(pd.DataFrame(notes), use_container_width=True, hide_index=True)
        st.subheader("Analyze exactly three notes")
        idx = st.multiselect("Choose 3", list(range(len(notes))), format_func=lambda i: f"{notes[i].get('date')} {notes[i].get('ticker')}")
        if st.button("Analyze"):
            picked = [notes[i] for i in idx]
            st.json(analyze_three(picked))


def page_ips():
    s = S()
    st.header("IPS BUILDER")
    txt = build_ips(s)
    st.text_area("Editable IPS", value=txt, height=500, key="ipsbox")
    st.download_button("Download IPS.md", data=txt, file_name="Laura_Gao_IPS.md")


def page_report():
    s = S()
    D, SC, F = _funnel_and_scores()
    fc = s["fc"]
    M = simulate(n=min(int(fc["n"]), 3000), mu=fc["r"], sd=fc["sd"], inflation=fc["inf"], indexed=fc["idx"], rf=fc["rf"])
    stress = run_scenarios(fc["r"], fc["inf"], fc["idx"], fc["rf"], s["sc"])
    keep = [u for u in s["u"] if (s.get("dec") or {}).get(u["t"], {}).get("d") in ("Keep", "INVEST")]
    ctx = {
        "data_mode": data_mode(s),
        "exec_snapshot": f"P(all payments)={M['p_all_funded']:.1%} (MODEL ESTIMATE). {len(keep)} Keep/INVEST names.",
        "universe_text": f"{len(s['u'])} securities. Sample flag={s.get('sample')}.",
        "funnel_text": "\n".join(f"{x['n']}: start {x['a']} removed {x['r']} remaining {x['remaining']}" for x in F["st"]),
        "keep_text": "\n".join(
            f"{u['t']} score={SC[u['t']]['score']} decision={(s.get('dec') or {}).get(u['t'], {}).get('d')} why={(s.get('dec') or {}).get(u['t'], {}).get('why') or 'N/A'} thesis={(s.get('thesis') or {}).get(u['t'], {}).get('thesis') or 'N/A'}"
            for u in keep
        )
        or "None",
        "reject_text": "\n".join(f"{r['ticker']} @ {r['stage']}: {r['reason']}" for r in F["log"][:200]) or "None logged",
        "portfolio_text": f"Weights {s.get('pw')}",
        "risk_text": "See Risk tab. Historical stats are not forecasts.",
        "scenario_text": "\n".join(f"{r['name']}: {r['status']} shortfall={r['total_shortfall']:.0f} | {r['causal_chain']}" for r in stress),
        "funding_text": f"mu={fc['r']} sd={fc['sd']} idx={fc['idx']} P(fund)={M['p_all_funded']:.1%}",
        "reserve_text": f"PV reserve={M['reserve_requirement']:.0f}; 2033 P10={M['reserve_2033']['p10']:.0f} P50={M['reserve_2033']['p50']:.0f}",
        "facility_text": str(M["facility_contribution_range_2033"]),
        "trades_text": json.dumps(s.get("trades") or [], default=str)[:4000],
        "notes_text": json.dumps(s.get("notes") or [], default=str)[:4000],
        "research_text": f"Research rows: {len(s.get('research') or [])}",
    }
    txt = build_report(ctx)
    st.header("FINAL REPORT")
    st.text_area("Report (model-filled + TEAM INPUT flags)", value=txt, height=500)
    st.download_button("Download report.md", data=txt, file_name="WInS_final_report.md")
    st.download_button(
        "Master dataset CSV",
        data=_master_csv(s, D, SC),
        file_name="master_dataset.csv",
    )


def _master_csv(s, D, SC):
    rows = []
    for u in s["u"]:
        row = {"ticker": u["t"], "name": u.get("n"), "asset_class": u.get("c"), "score": SC[u["t"]]["score"]}
        for k, cell in D[u["t"]].items():
            if isinstance(cell, dict) and "v" in cell:
                row[k] = cell["v"]
        rows.append(row)
    return pd.DataFrame(rows).to_csv(index=False)


def page_quality():
    s = S()
    D = datapoints(s)
    Q = quality_rows(s["u"], D, s.get("src") or {})
    st.header("DATA QUALITY")
    banner(Q["all"])
    st.metric("Avg complete", f"{Q['avg']*100:.0f}%")
    st.metric("Rejected price rows", s.get("rej", 0))
    st.dataframe(pd.DataFrame(Q["rows"]), use_container_width=True, hide_index=True)
    st.caption("DEMO DATA can never reach HIGH CONFIDENCE. Missing values are N/A, never imputed.")
    if s.get("overrides"):
        st.subheader("Human override audit log")
        st.dataframe(pd.DataFrame(s["overrides"]), use_container_width=True, hide_index=True)


def page_ml():
    s = S()
    st.header("ML")
    st.write("Ridge walk-forward is preserved from the original engine. ML is **never** the investment decision.")
    if st.button("Train ridge (walk-forward)"):
        uni = [u["t"] for u in s["u"] if classify_asset(u.get("c"), u["t"]) != "bond"]
        r = walk_forward_ridge(s.get("px") or {}, uni, s["cfg"]["bench"])
        if r.get("err"):
            st.error(r["err"])
        else:
            r["demo"] = any(s.get("src", {}).get(t) == "demo" for t in uni)
            s["ml"] = r
            persist()
    m = s.get("ml")
    if m and not m.get("err"):
        st.write(m.get("rep"))
        st.caption(m.get("note"))
        st.write("Latest scores (MODEL ESTIMATE)", m.get("s"))
        if m.get("demo"):
            st.warning("Trained on DEMO DATA.")


def main():
    s = S()
    st.sidebar.title("Thesis Tension")
    st.sidebar.caption(CLIENT_NAME)
    page = st.sidebar.radio(
        "Tabs",
        [
            "HOME",
            "DATA",
            "UNIVERSE",
            "COUNTRY",
            "INDUSTRY",
            "ETF ANALYSIS",
            "FUNDAMENTALS",
            "VALUATION",
            "RISK",
            "SENTIMENT",
            "THESIS TENSION",
            "SCENARIOS",
            "PORTFOLIO",
            "MARKOWITZ",
            "FUNDING",
            "MONTE CARLO",
            "TRADING",
            "TRADING NOTES",
            "IPS",
            "FINAL REPORT",
            "DATA QUALITY",
            "ML",
        ],
    )
    st.sidebar.write("Mode:", data_mode(s))
    pages = {
        "HOME": page_home,
        "DATA": page_data,
        "UNIVERSE": page_universe,
        "COUNTRY": page_country,
        "INDUSTRY": page_industry,
        "ETF ANALYSIS": page_etf,
        "FUNDAMENTALS": page_fundamentals,
        "VALUATION": page_valuation,
        "RISK": page_risk,
        "SENTIMENT": page_sentiment,
        "THESIS TENSION": page_thesis,
        "SCENARIOS": page_scenarios,
        "PORTFOLIO": page_portfolio,
        "MARKOWITZ": page_markowitz,
        "FUNDING": page_funding,
        "MONTE CARLO": page_mc,
        "TRADING": page_trading,
        "TRADING NOTES": page_notes,
        "IPS": page_ips,
        "FINAL REPORT": page_report,
        "DATA QUALITY": page_quality,
        "ML": page_ml,
    }
    pages[page]()


if __name__ == "__main__":
    main()
