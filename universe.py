"""WInS universe is authoritative. Never assume an external ETF is eligible."""

from __future__ import annotations

from .case import TENSION_LINE

EQ_SAMPLE = (
    "ARKK GRID FAN PAVE TAN PHO PBW IBB DGRO ESGU ICLN INDA EWW EWT ITA BBCA XLU ESGV VWO "
    "VHT VNQ VTI VT VSS VNQI MSOS IPO JEPI COWZ LQCL XLC XLP XLE XLF XLV XLI RSP ESGE EWA "
    "EWZ MCHI DSI USMV QUAL ESGD MOAT VEU VEA VGK VOO VXUS XLB XLY QQQ MTUM IWF XLK SMH "
    "VUG VGT IWD NOBL SCHD VIG VYM VTV IJH VO IJR IWM AVUV"
).split()
FI_SAMPLE = (
    "AGG JPST BSV BND BNDX FTSL HYLS IGSB FALN HYG LQD JNK VCIT VCSH SHY TLT IEF EMB SHV "
    "GOVT BIL VGSH USFR EMLC VTIP TIP MBB MUB VTEB"
).split()


def classify_asset(asset_class: str, ticker: str = "") -> str:
    a = (asset_class or "").lower()
    t = (ticker or "").upper()
    if "bond" in a or "fixed" in a:
        return "bond"
    if "etf" in a or "/" in a:
        return "etf"
    if t in FI_SAMPLE:
        return "bond"
    if t in EQ_SAMPLE:
        return "etf"
    return "stock"


def expected_metric_keys(kind: str) -> list[str]:
    mk = [
        "last_close",
        "daily_return",
        "monthly_return",
        "ann_return",
        "cagr",
        "volatility",
        "beta",
        "alpha",
        "sharpe",
        "max_drawdown",
        "correlation",
        "r_squared",
    ]
    extra = {
        "stock": ["market_cap", "pe_ratio", "dividend_yield", "eps", "profit_margin", "roe", "sector"],
        "etf": ["expense_ratio", "aum", "holdings_count", "top10_concentration", "largest_holding"],
        "bond": ["bond_yield", "bond_duration", "bond_maturity", "sec_yield"],
    }
    return mk + extra.get(kind, extra["etf"])


def sample_universe_rows() -> list[dict]:
    rows = []
    for t in EQ_SAMPLE:
        rows.append(
            {
                "t": t,
                "n": "",
                "c": "Equity ETF",
                "a": {},
                "x": {},
                "wins_approved": "UNKNOWN",
            }
        )
    for t in FI_SAMPLE:
        rows.append(
            {
                "t": t,
                "n": "",
                "c": "Fixed Income ETF",
                "a": {},
                "x": {},
                "wins_approved": "UNKNOWN",
            }
        )
    return rows


def wins_gate(sec: dict) -> dict:
    flag = sec.get("wins_approved", "UNKNOWN")
    if flag == "TRUE":
        return {"pass": True, "reason": "Listed as WInS-approved in the uploaded universe."}
    if flag == "FALSE":
        return {
            "pass": False,
            "reason": "WINS_APPROVED=FALSE. External availability does not imply WInS eligibility.",
        }
    return {
        "pass": True,
        "reason": "WINS_APPROVED=UNKNOWN — treat as unverified. Do not assume eligibility.",
        "warning": True,
    }
