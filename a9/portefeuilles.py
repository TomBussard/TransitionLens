"""Construction des portefeuilles candidats et pondérations.

Ratio de diversification OPCVM (art. R214-21 CMF / directive OPCVM art. 52) : 5 % par émetteur,
porté à 10 % à condition que la somme des lignes > 5 % n'excède pas 40 %. Conséquence : un
portefeuille entièrement investi en actions exige au moins 16 émetteurs (4 x 10 % + 12 x 5 %).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def plafonner(w: pd.Series, cap: float = 0.05, cap_derog: float = 0.10, somme_max: float = 0.40,
              tol: float = 1e-12) -> tuple[pd.Series, bool]:
    """Pondérations respectant 5/10/40 par redistribution proportionnelle itérative.

    Renvoie (pondérations, conforme). Si n < 16, la conformité est impossible à pleine exposition :
    on applique un plafond uniforme 1/n et conforme = False (signalé, jamais masqué).
    """
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
    # 16 <= n < 20 : quatre lignes au plus à 10 %, le reste à 5 %
    k = int(np.floor(somme_max / cap_derog))
    if k * cap_derog + (n - k) * cap >= 1 - tol:
        # Tri STABLE : à poids égaux, l'ordre d'entrée décide (univers trié par poids MSCI décroissant :
        # les plus grandes capitalisations, plus liquides, reçoivent les lignes à 10 %). Déterministe.
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
    ids = list(dict.fromkeys(ids))  # déduplication (une société n'est jamais comptée deux fois)
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
