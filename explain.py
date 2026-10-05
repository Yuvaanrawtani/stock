"""What / why copy for metrics (student-facing)."""

INFO = {
    "sharpe": "What: excess return per unit of volatility. Formula: (ann. return − risk-free) ÷ volatility. Why: compares funds with different risk. Not a buy signal.",
    "volatility": "What: annualized standard deviation of returns. Why: Laura needs cash on fixed dates — bumpier paths raise shortfall risk.",
    "beta": "What: sensitivity to the benchmark (cov ÷ benchmark variance). Why: shows market dependence.",
    "alpha": "What: return beyond what beta explains (Jensen). Why: noisy; not a thesis.",
    "max_drawdown": "What: worst peak-to-trough fall in the sample. Why: a picture of historical pain, not a forecast.",
    "cagr": "What: (end/start)^(1/years) − 1. Why: past growth speed; says nothing certain about the future.",
    "r_squared": "What: squared correlation vs the benchmark. Why: how much of the move was 'the market'.",
    "correlation": "What: co-movement of returns. Why: diversification math.",
    "pe": "What: price / earnings. Why: valuation shorthand. High is not automatically bad.",
    "pb": "What: price / book. Why: useful for asset-heavy firms; weak for asset-light compounders.",
    "ps": "What: price / sales. Why: used when earnings are noisy.",
    "peg": "What: P/E divided by growth %. Why: crude growth-adjusted multiple.",
    "piotroski": "What: 0–9 financial-strength signals. Why: company quality — never copied onto an ETF as 'ETF F-score = 7'.",
    "beneish": "What: earnings-manipulation screen. Why: risk flag, not a court verdict.",
    "altman": "What: manufacturing distress screen. Why: not for banks or bond ETFs.",
    "sgr": "What: ROE × retention. Why: compares actual growth with internally fundable growth.",
}
