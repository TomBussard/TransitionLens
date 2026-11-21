"""Backtest a long-only EUR portfolio. Weights drift between rebalances. Turnover counts buys and sells, and unquoted holdings transfer to cash after their last observation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def dates_rebal(index: pd.DatetimeIndex, freq: str) -> set:
    if freq == "BH":
        return set()
    per = index.to_period("Q" if freq == "Q" else "Y")
    fins = pd.Series(index, index=index).groupby(per).max()
    return set(fins.iloc[:-1])  # There is no following holding period after the last date.


def simuler(
    cibles: pd.Series,
    r: pd.DataFrame,
    freq: str = "Q",
    cout_bps: float = 15.0,
    frais_annuels: float = 0.0,
    cout_initial: bool = True,
) -> dict:
    """Calculate daily gross and net returns and turnover at each rebalance.

    Rows in the returns table are dates. An occasional missing quote carries the last price forward."""
    cibles = cibles[cibles > 0]
    titres = [t for t in cibles.index if t in r.columns]
    if r.index.empty or not titres:
        raise ValueError(
            "Supply at least one date and one positively weighted asset with a return column."
        )
    cibles = cibles[titres] / cibles[titres].sum()
    R = r[titres]
    # After the final quote, keep the position in cash until the next rebalance.
    derniere = R.apply(lambda s: s.last_valid_index())
    rb = dates_rebal(R.index, freq)
    c = cout_bps / 1e4
    w = cibles.copy()
    cash = 0.0
    rot = {}
    if cout_initial:
        rot[R.index[0] - pd.Timedelta(days=1)] = 1.0
    brut, net = [], []
    for t in R.index:
        rt = R.loc[t]
        actifs = [k for k in w.index if derniere[k] is not None and t <= derniere[k]]
        sortis = [k for k in w.index if k not in actifs and w[k] != 0]
        for k in sortis:
            cash += w[k]
            w[k] = 0.0
        g = rt.reindex(w.index).fillna(0.0)  # Local market holidays carry a zero daily return.
        port = float((w * g).sum())  # Cash earns zero in this example.
        tot = float(w.sum() + cash)
        rp = port / tot
        brut.append(rp)
        w = w * (1 + g)
        if t in rb:
            vivants = [k for k in cibles.index if derniere[k] is not None and derniere[k] > t]
            cib = cibles[vivants] / cibles[vivants].sum()
            tot = float(w.sum() + cash)
            w_now = (w / tot).reindex(cib.index).fillna(0.0)
            # Reinvesting cash is already included on the buy side.
            delta = (cib - w_now).abs().sum() + (w / tot).drop(
                index=cib.index, errors="ignore"
            ).abs().sum()
            rot[t] = float(delta)
            w = cib.reindex(w.index).fillna(0.0) * tot
            # If every holding has stopped trading, the proceeds stay in cash.
            cash = 0.0 if len(vivants) else tot
            cout = delta * c
        else:
            cout = 0.0
        net.append(rp - cout - frais_annuels / 252.0)
    rot_s = pd.Series(rot, dtype=float)
    out = {"rend_brut": pd.Series(brut, index=R.index), "rotation": rot_s}
    rn = pd.Series(net, index=R.index)
    if cout_initial:
        rn.iloc[0] -= c * 1.0
    out["rend_net"] = rn
    return out


def hebdo(r: pd.Series) -> pd.Series:
    return (1 + r).resample("W-FRI").prod() - 1


def mensuel(r: pd.Series) -> pd.Series:
    return (1 + r).resample("ME").prod() - 1
