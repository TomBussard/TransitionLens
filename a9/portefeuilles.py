"""Build long-only portfolios under the study's 5/10/40 concentration limits. With the default settings, full investment needs at least sixteen issuers."""
from __future__ import annotations

import numpy as np
import pandas as pd


def plafonner(w: pd.Series, cap: float = 0.05, cap_derog: float = 0.10, somme_max: float = 0.40,
              tol: float = 1e-12) -> tuple[pd.Series, bool]:
    """Redistribute excess weight until the limits are satisfied.

    The second return value flags feasibility. When there are too few issuers, the fallback is equal weight."""
    w = w[w > 0].astype(float)
    w = w / w.sum()
    n = len(w)
    if n == 0:
        return w, False
    if n * cap >= 1 - tol:
        for _ in range(200):
            exc = (w - cap).clip(lower=0)
            if exc.sum() <= tol:
                break
            w = w.clip(upper=cap)
            libres = w < cap - tol
            w[libres] += exc.sum() * w[libres] / w[libres].sum()
        return w / w.sum(), bool((w <= cap + 1e-9).all())
    # With fewer than 20 names, some positions need the higher limit.
    k = int(np.floor(somme_max / cap_derog))
    if k * cap_derog + (n - k) * cap >= 1 - tol:
        # Keep incoming order when two reference weights tie.

        ordre = w.sort_values(ascending=False, kind="stable").index
        plafonds = pd.Series(cap, index=w.index)
        plafonds[ordre[:k]] = cap_derog
        for _ in range(200):
            exc = (w - plafonds).clip(lower=0)
            if exc.sum() <= tol:
                break
            w = np.minimum(w, plafonds)
            libres = w < plafonds - tol
            w[libres] += exc.sum() * w[libres] / w[libres].sum()
        w = w / w.sum()
        conf = bool((w <= plafonds + 1e-9).all() and w[w > cap + 1e-9].sum() <= somme_max + 1e-9)
        return w, conf
    return pd.Series(1.0 / n, index=w.index), False


def equipondere(ids) -> pd.Series:
    ids = list(dict.fromkeys(ids))  # Count each company once.
    return pd.Series(1.0 / len(ids), index=ids) if ids else pd.Series(dtype=float)


def capi_plafonne(ids, poids_ref: pd.Series) -> tuple[pd.Series, bool]:
    ids = list(dict.fromkeys(ids))
    return plafonner(poids_ref.reindex(ids).dropna())


def selection_quantile(score: pd.Series, q: float, haut: bool = True) -> list:
    s = score.dropna()
    if s.empty:
        return []
    seuil = s.quantile(1 - q) if haut else s.quantile(q)
    return s.index[s >= seuil].tolist() if haut else s.index[s <= seuil].tolist()
