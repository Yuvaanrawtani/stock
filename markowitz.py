"""Mean-variance optimizer. A construction tool — not the final decision-maker."""

from __future__ import annotations

import numpy as np

try:
    from scipy.optimize import minimize
except Exception:  # pragma: no cover
    minimize = None


def _clean_cov(cov: np.ndarray) -> np.ndarray:
    cov = 0.5 * (cov + cov.T)
    w, v = np.linalg.eigh(cov)
    w = np.maximum(w, 1e-10)
    return (v * w) @ v.T


def optimize(
    mu: np.ndarray,
    cov: np.ndarray,
    *,
    rf: float = 0.03,
    max_weight: float = 1.0,
    min_weight: float = 0.0,
    target_return: float | None = None,
    target_vol: float | None = None,
    objective: str = "max_sharpe",
) -> dict:
    n = len(mu)
    mu = np.asarray(mu, dtype=float)
    cov = _clean_cov(np.asarray(cov, dtype=float))
    bounds = [(min_weight, max_weight)] * n
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    def port(w):
        r = float(w @ mu)
        v = float(np.sqrt(w @ cov @ w))
        return r, v

    def neg_sharpe(w):
        r, v = port(w)
        return -(r - rf) / v if v > 1e-12 else 0.0

    def vol(w):
        return port(w)[1]

    x0 = np.repeat(1.0 / n, n)
    if objective == "min_vol":
        fun = vol
    elif objective == "target_return":
        if target_return is None:
            raise ValueError("target_return required")
        cons = cons + [{"type": "eq", "fun": lambda w, t=target_return: w @ mu - t}]
        fun = vol
    elif objective == "target_risk":
        if target_vol is None:
            raise ValueError("target_vol required")
        cons = cons + [{"type": "ineq", "fun": lambda w, t=target_vol: t - vol(w)}]
        fun = lambda w: -(w @ mu)
    else:
        fun = neg_sharpe

    if minimize is None:
        w = _projected_max_sharpe(mu, cov, rf, max_weight)
        r, v = port(w)
        return {"weights": w, "return": r, "vol": v, "sharpe": (r - rf) / v if v else None, "method": "unconstrained-projection"}

    res = minimize(fun, x0, bounds=bounds, constraints=cons, method="SLSQP", options={"maxiter": 400, "ftol": 1e-9})
    w = np.clip(res.x, min_weight, max_weight)
    s = w.sum()
    w = w / s if s else x0
    r, v = port(w)
    return {
        "weights": w,
        "return": r,
        "vol": v,
        "sharpe": (r - rf) / v if v else None,
        "success": bool(res.success),
        "message": str(res.message),
        "method": "SLSQP",
        "note": "Markowitz is not the final decision-maker. Thesis, Laura role, funding, and risk constraints still apply.",
    }


def efficient_frontier(mu, cov, rf=0.03, n_points=16, max_weight=1.0):
    mu = np.asarray(mu, dtype=float)
    pts = []
    grid = np.linspace(float(mu.min()), float(mu.max()), n_points)
    for t in grid:
        try:
            pts.append(optimize(mu, cov, rf=rf, max_weight=max_weight, target_return=float(t), objective="target_return"))
        except Exception:
            continue
    minv = optimize(mu, cov, rf=rf, max_weight=max_weight, objective="min_vol")
    mx = optimize(mu, cov, rf=rf, max_weight=max_weight, objective="max_sharpe")
    return {"frontier": pts, "min_vol": minv, "max_sharpe": mx}


def apply_group_caps(tickers: list[str], weights: np.ndarray, groups: dict[str, str], caps: dict[str, float]) -> np.ndarray:
    """Renormalize if a group exceeds its cap. Soft enforcement for country/sector/asset class."""
    w = weights.copy()
    for g, cap in caps.items():
        idx = [i for i, t in enumerate(tickers) if groups.get(t) == g]
        s = w[idx].sum() if idx else 0
        if s > cap and s > 0:
            w[idx] *= cap / s
    tot = w.sum()
    return w / tot if tot else w


def _projected_max_sharpe(mu, cov, rf, max_w):
    try:
        inv = np.linalg.pinv(cov)
        excess = mu - rf
        raw = inv @ excess
        raw = np.maximum(raw, 0)
        if raw.sum() == 0:
            raw = np.ones_like(mu)
        w = raw / raw.sum()
        w = np.minimum(w, max_w)
        return w / w.sum()
    except Exception:
        return np.repeat(1.0 / len(mu), len(mu))
