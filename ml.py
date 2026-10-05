"""Ridge (ported from the HTML engine) plus optional sklearn models. ML is never an investment decision."""

from __future__ import annotations

from typing import Optional

import numpy as np

from .metrics import sample_cov
from .provenance import utc_now


def ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float = 10.0) -> np.ndarray:
    n = x.shape[1]
    a = x.T @ x + alpha * np.eye(n)
    b = x.T @ y
    return np.linalg.solve(a, b)


def rank_ic(pred: np.ndarray, actual: np.ndarray) -> float:
    def rank(a):
        o = np.argsort(a)
        r = np.empty_like(o, dtype=float)
        r[o] = np.arange(len(a))
        return r

    x, y = rank(pred), rank(actual)
    c = sample_cov(x, y)
    return float(c / np.sqrt(sample_cov(x, x) * sample_cov(y, y)))


def summarize_ic(ic: list[float], spread: list[float]) -> dict:
    ic = [x for x in ic if x == x]
    n = len(ic)
    if n < 6:
        return {"n": n, "verdict": "INSUFFICIENT DATA"}
    mu = float(np.mean(ic))
    sd = float(np.sqrt(sample_cov(ic, ic)))
    t = mu / (sd / np.sqrt(n) + 1e-12)
    hit = float(np.mean([1 if x > 0 else 0 for x in ic]))
    return {
        "n": n,
        "ic": round(mu, 3),
        "t": round(t, 2),
        "hit": f"{hit*100:.0f}%",
        "sp": f"{float(np.mean(spread))*100:.2f}%",
        "verdict": "SIGNAL (t≥2)" if t >= 2 else "NO SIGNIFICANT EDGE (t<2)",
    }


def walk_forward_ridge(px: dict, universe: list[str], bench: str = "SPY") -> dict:
    """Monthly walk-forward on price features. Port of the original HTML ridge model."""
    if bench not in px or len(px[bench]) < 60:
        return {"err": "Need benchmark prices plus securities with prices."}
    B = px[bench]
    D = [d for d, _ in B]
    bp = np.array([p for _, p in B], dtype=float)
    uni = [t for t in universe if t != bench and t in px]
    if len(uni) < 6:
        return {"err": "Need benchmark prices plus at least 6 securities with prices."}

    P = {}
    for t in uni:
        m = dict(px[t])
        last = None
        arr = []
        for d in D:
            if d in m:
                last = m[d]
            arr.append(last)
        P[t] = arr

    me = [i for i in range(len(D)) if i == len(D) - 1 or D[i + 1][:7] != D[i][:7]]
    if len(me) < 24:
        return {"err": "Need about 3 years of daily prices."}

    by: dict[int, list] = {}
    for k in range(12, len(me)):
        i = me[k]
        if i - 126 < 0:
            continue
        rb = bp[i - 125 : i + 1] / bp[i - 126 : i] - 1
        vb = sample_cov(rb, rb)
        cr = []
        for t in uni:
            a = np.array(P[t], dtype=float)
            if a[me[k - 12]] is None or np.isnan(a[me[k - 12]]) or np.isnan(a[i - 126]):
                continue
            r = a[i - 125 : i + 1] / a[i - 126 : i] - 1
            def f(j):
                return a[i] / a[me[k - j]] - 1

            w = a[i - 125 : i + 1]
            pk = np.maximum.accumulate(w)
            dd = float(np.min(w / pk - 1))
            y = None
            if k + 1 < len(me):
                y = (a[me[k + 1]] / a[i] - 1) - (bp[me[k + 1]] / bp[i] - 1)
            cr.append(
                {
                    "k": k,
                    "t": t,
                    "x": [
                        f(1),
                        f(3),
                        f(6),
                        f(12),
                        float(np.sqrt(sample_cov(r[-63:], r[-63:]) * 252)) if len(r) >= 63 else 0.0,
                        float(sample_cov(r, rb) / vb) if vb else 0.0,
                        dd,
                        f(3) - (bp[i] / bp[me[k - 3]] - 1),
                        float(a[i] / pk[-1] - 1),
                    ],
                    "y": y,
                }
            )
        if len(cr) < 6:
            continue
        x = np.array([c["x"] for c in cr], dtype=float)
        mu = x.mean(axis=0)
        sd = x.std(axis=0, ddof=1) + 1e-9
        x = (x - mu) / sd
        ys = [c["y"] for c in cr]
        if ys[0] is not None:
            ym = np.mean([y for y in ys if y is not None])
            for c, yv, row in zip(cr, ys, x):
                c["x"] = row.tolist()
                if yv is not None:
                    c["y"] = yv - ym
        else:
            for c, row in zip(cr, x):
                c["x"] = row.tolist()
        by.setdefault(k, []).extend(cr)

    ks = sorted(by)
    ok = [k for k in ks if by[k] and by[k][0]["y"] is not None]
    R = {"ridge": {"ic": [], "sp": []}, "baseline_mom6": {"ic": [], "sp": []}}
    for k in ok[15:]:
        te = by[k]
        tr = [r for j in ok if j < k for r in by[j]]
        if len(tr) < 10:
            continue
        X = np.array([r["x"] for r in tr], dtype=float)
        y = np.array([r["y"] for r in tr], dtype=float)
        w = ridge_fit(X, y, 10.0)
        yte = np.array([r["y"] for r in te], dtype=float)
        pred = np.array([np.dot(w, r["x"]) for r in te])
        mom = np.array([r["x"][2] for r in te])
        for name, s in (("ridge", pred), ("baseline_mom6", mom)):
            R[name]["ic"].append(rank_ic(s, yte))
            o = np.argsort(s)
            q = max(1, len(te) // 3)
            R[name]["sp"].append(float(yte[o[-q:]].mean() - yte[o[:q]].mean()))

    last_k = ks[-1]
    tr_all = [r for k in ok for r in by[k]]
    w = ridge_fit(np.array([r["x"] for r in tr_all]), np.array([r["y"] for r in tr_all]), 10.0)
    sc = {}
    for r in by.get(last_k, []):
        if r["y"] is None:
            sc[r["t"]] = float(np.dot(w, r["x"]))
    return {
        "s": sc,
        "at": utc_now(),
        "date": D[-1],
        "rep": {
            "ridge": summarize_ic(R["ridge"]["ic"], R["ridge"]["sp"]),
            "baseline_mom6": summarize_ic(R["baseline_mom6"]["ic"], R["baseline_mom6"]["sp"]),
        },
        "features": [
            "1m ret",
            "3m ret",
            "6m ret",
            "12m ret",
            "vol",
            "beta",
            "drawdown",
            "3m relative",
            "distance-to-peak",
        ],
        "note": "ML rankings are not investment decisions. If verdict is NO SIGNIFICANT EDGE, do not manufacture a signal.",
    }


def optional_sklearn_walkforward(X_list, y_list):
    """If sklearn is installed, compare Ridge/Lasso/RF/GB. LSTM/DNN omitted: too little data to validate honestly."""
    try:
        from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
        from sklearn.linear_model import Lasso, Ridge
    except Exception:
        return {"available": False, "reason": "sklearn not installed"}

    models = {
        "Ridge": Ridge(alpha=10.0),
        "Lasso": Lasso(alpha=0.1),
        "RandomForest": RandomForestRegressor(n_estimators=80, max_depth=3, random_state=0),
        "GradientBoosting": GradientBoostingRegressor(n_estimators=80, max_depth=2, random_state=0),
    }
    # X_list/y_list are time-ordered folds
    out = {}
    for name, model in models.items():
        ics = []
        for i in range(5, len(X_list)):
            Xtr = np.vstack(X_list[:i])
            ytr = np.concatenate(y_list[:i])
            model.fit(Xtr, ytr)
            pred = model.predict(X_list[i])
            ics.append(rank_ic(pred, y_list[i]))
        out[name] = summarize_ic(ics, [0.0] * len(ics))
    out["lstm_dnn"] = {
        "verdict": "NOT IMPLEMENTED",
        "reason": "Sequence DL is not honestly validatable on this sample; omitted rather than faked.",
    }
    return {"available": True, "rep": out}
