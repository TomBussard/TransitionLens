"""Build long-only portfolios under the study's 5/10/40 concentration limits. With the default settings, full investment needs at least sixteen issuers."""

from __future__ import annotations

import numpy as np
import pandas as pd


def plafonner(
    w: pd.Series,
    cap: float = 0.05,
    cap_derog: float = 0.10,
    somme_max: float = 0.40,
    tol: float = 1e-12,
) -> tuple[pd.Series, bool]:
    """Redistribute excess weight until the limits are satisfied.

    The second return value flags feasibility. When there are too few issuers, the fallback is equal weight."""
    if not 0 < cap <= cap_derog <= 1 or not 0 <= somme_max <= 1:
        raise ValueError(
            "Use positive position limits and an aggregate allowance between zero and one."
        )
    weights = w.dropna().astype(float)
    if not np.isfinite(weights).all() or not weights.index.is_unique:
        raise ValueError("Supply one finite starting weight per issuer.")
    weights = weights[weights > 0]
    if weights.empty:
        return weights, False
    weights = weights / weights.sum()
    limits = pd.Series(cap, index=weights.index)
    if limits.sum() < 1 - tol:
        # A stable sort gives the same allowance to the same issuer when two weights tie.
        slots = int(np.floor((somme_max + tol) / cap_derog))
        largest = weights.sort_values(ascending=False, kind="stable").head(slots).index
        limits.loc[largest] = cap_derog
    if limits.sum() < 1 - tol:
        return pd.Series(1 / len(weights), index=weights.index), False

    # Each pass fixes at least one issuer at its cap. Redistribute the rest in the original proportions.
    result = pd.Series(0.0, index=weights.index)
    remaining = weights.index
    while len(remaining):
        free = weights.loc[remaining]
        proposed = (1 - result.sum()) * free / free.sum()
        above = proposed > limits.loc[remaining] + tol
        if not above.any():
            result.loc[remaining] = proposed
            break
        fixed = above.index[above]
        result.loc[fixed] = limits.loc[fixed]
        remaining = above.index[~above]
    meets_limits = result[result > cap + tol].sum() <= somme_max + tol
    return result, bool(meets_limits)


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
