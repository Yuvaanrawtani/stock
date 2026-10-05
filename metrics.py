"""Price and return metrics. Ported from the working HTML engine (sample covariance, 252-day year)."""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

import numpy as np

NA = None


def _mean(x: Sequence[float]) -> float:
    return float(np.mean(x))


def sample_cov(x: Sequence[float], y: Sequence[float]) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2:
        return float("nan")
    return float(np.cov(x, y, ddof=1)[0, 1])


def cagr(start: float, end: float, years: float) -> Optional[float]:
    if start is None or end is None or start <= 0 or end <= 0 or years is None or years <= 0:
        return NA
    return float((end / start) ** (1.0 / years) - 1.0)


def volatility_from_returns(daily_returns: Sequence[float], periods: int = 252) -> Optional[float]:
    if daily_returns is None or len(daily_returns) < 2:
        return NA
    var = sample_cov(daily_returns, daily_returns)
    if var != var or var < 0:
        return NA
    return float(np.sqrt(var * periods))


def beta_alpha_r2(
    asset_returns: Sequence[float],
    bench_returns: Sequence[float],
    rf_annual: float,
) -> dict:
    out = {"beta": NA, "alpha": NA, "correlation": NA, "r_squared": NA, "ann_return": NA, "bench_ann_return": NA}
    if asset_returns is None or bench_returns is None or len(asset_returns) < 2:
        return out
    aa = _mean(asset_returns) * 252
    ab = _mean(bench_returns) * 252
    va = sample_cov(asset_returns, asset_returns)
    vb = sample_cov(bench_returns, bench_returns)
    cv = sample_cov(asset_returns, bench_returns)
    beta = cv / vb if vb and vb > 0 else NA
    corr = cv / (np.sqrt(va * vb)) if va > 0 and vb > 0 else NA
    r2 = float(corr * corr) if corr is not None and corr == corr else NA
    alpha = aa - (rf_annual + beta * (ab - rf_annual)) if beta is not None else NA
    out.update(
        beta=None if beta is None or beta != beta else float(beta),
        alpha=None if alpha is None or alpha != alpha else float(alpha),
        correlation=None if corr is None or corr != corr else float(corr),
        r_squared=None if r2 is None or r2 != r2 else float(r2),
        ann_return=float(aa),
        bench_ann_return=float(ab),
    )
    return out


def sharpe(ann_return: Optional[float], vol: Optional[float], rf: float) -> Optional[float]:
    if ann_return is None or vol is None or vol <= 0:
        return NA
    return float((ann_return - rf) / vol)


def max_drawdown(prices: Sequence[float]) -> Optional[float]:
    if not prices:
        return NA
    peak = 0.0
    dd = 0.0
    for v in prices:
        peak = max(peak, v)
        if peak > 0:
            dd = min(dd, v / peak - 1.0)
    return float(dd)


def downside_deviation(daily_returns: Sequence[float], mar_daily: float = 0.0, periods: int = 252) -> Optional[float]:
    if daily_returns is None or len(daily_returns) < 2:
        return NA
    r = np.asarray(daily_returns, dtype=float)
    down = np.minimum(0.0, r - mar_daily)
    if np.all(down == 0):
        return 0.0
    var = float(np.mean(down**2))
    return float(np.sqrt(var * periods))


def aligned_returns(
    asset_px: list[tuple[str, float]],
    bench_px: list[tuple[str, float]],
    lookback_days: int = 1095,
) -> Optional[dict]:
    if not asset_px or not bench_px:
        return None
    last = asset_px[-1][0]
    cut = _date_minus_days(last, lookback_days)
    a = {d: p for d, p in asset_px if d >= cut}
    b = {d: p for d, p in bench_px if d >= cut}
    dates = sorted(set(a) & set(b))
    if len(dates) < 60:
        return None
    ar = []
    br = []
    prices = []
    for i in range(1, len(dates)):
        d0, d1 = dates[i - 1], dates[i]
        ar.append(a[d1] / a[d0] - 1.0)
        br.append(b[d1] / b[d0] - 1.0)
        prices.append(a[d1])
    years = _year_frac(dates[0], dates[-1])
    month_last = {}
    for d in dates:
        month_last[d[:7]] = a[d]
    months = list(month_last.values())
    monthly = months[-1] / months[-2] - 1.0 if len(months) > 1 else None
    return {
        "dates": dates,
        "asset_returns": ar,
        "bench_returns": br,
        "prices": [a[dates[0]]] + prices,
        "years": years,
        "start_px": a[dates[0]],
        "end_px": a[dates[-1]],
        "daily_return": ar[-1] if ar else None,
        "monthly_return": monthly,
        "period": f"{dates[0]}..{dates[-1]}",
    }


def compute_price_metrics(
    asset_px: list[tuple[str, float]],
    bench_px: list[tuple[str, float]],
    rf: float = 0.04,
    lookback_days: int = 1095,
) -> Optional[dict]:
    al = aligned_returns(asset_px, bench_px, lookback_days)
    if al is None:
        return None
    ba = beta_alpha_r2(al["asset_returns"], al["bench_returns"], rf)
    vol = volatility_from_returns(al["asset_returns"])
    cg = cagr(al["start_px"], al["end_px"], al["years"])
    return {
        "daily_return": al["daily_return"],
        "monthly_return": al["monthly_return"],
        "ann_return": ba["ann_return"],
        "cagr": cg,
        "volatility": vol,
        "beta": ba["beta"],
        "alpha": ba["alpha"],
        "sharpe": sharpe(ba["ann_return"], vol, rf),
        "max_drawdown": max_drawdown(al["prices"]),
        "correlation": ba["correlation"],
        "r_squared": ba["r_squared"],
        "downside_deviation": downside_deviation(al["asset_returns"]),
        "period": al["period"],
        "n_obs": len(al["asset_returns"]),
    }


def correlation_matrix(series: dict[str, Sequence[float]]) -> Optional[np.ndarray]:
    keys = list(series)
    if len(keys) < 2:
        return None
    mats = [np.asarray(series[k], dtype=float) for k in keys]
    n = min(len(m) for m in mats)
    if n < 5:
        return None
    x = np.vstack([m[-n:] for m in mats])
    return np.corrcoef(x)


def _date_minus_days(iso: str, days: int) -> str:
    y, m, d = map(int, iso[:10].split("-"))
    import datetime as dt

    return (dt.date(y, m, d) - dt.timedelta(days=days)).isoformat()


def _year_frac(a: str, b: str) -> float:
    import datetime as dt

    da = dt.date.fromisoformat(a[:10])
    db = dt.date.fromisoformat(b[:10])
    return (db - da).days / 365.25
