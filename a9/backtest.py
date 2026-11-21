"""Moteur de simulation quotidien, long-only, en EUR.

* Pondérations cibles fixées à la date de constitution (signaux disponibles à cette date uniquement).
* Entre deux rééquilibrages, les poids dérivent avec les prix (achat-conservation).
* Rééquilibrage (fin de trimestre « Q » ou fin d'année « A ») : retour aux poids cibles parmi les titres
  encore cotés ; rotation = somme |delta w| (achats + ventes) ; coût = rotation x coût unitaire.
* Titre radié en cours de période (série interrompue) : la ligne est conservée en liquidités à rendement nul
  jusqu'au rééquilibrage suivant (hypothèse prudente, documentée ; pas de prime d'OPA imputée).
* Frais de gestion : prélèvement quotidien au prorata (taux annuel / 252) pour la version nette.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def dates_rebal(index: pd.DatetimeIndex, freq: str) -> set:
    if freq == "BH":
        return set()
    per = index.to_period("Q" if freq == "Q" else "Y")
    fins = pd.Series(index, index=index).groupby(per).max()
    return set(fins.iloc[:-1])  # le dernier jour de l'échantillon n'est pas un rééquilibrage


def simuler(cibles: pd.Series, r: pd.DataFrame, freq: str = "Q", cout_bps: float = 15.0,
            frais_annuels: float = 0.0, cout_initial: bool = True) -> dict:
    """Simule un portefeuille. `r` : rendements quotidiens (dates x titres), NaN = pas de cotation.

    Renvoie dict(rend_brut, rend_net, rotation (par rééquilibrage), poids_fin).
    """
    cibles = cibles[cibles > 0]
    titres = [t for t in cibles.index if t in r.columns]
    cibles = cibles[titres] / cibles[titres].sum()
    R = r[titres]
    # dernière date cotée par titre (au-delà : radié)
    derniere = R.apply(lambda s: s.last_valid_index())
    rb = dates_rebal(R.index, freq)
    c = cout_bps / 1e4
    w = cibles.copy()
    cash = 0.0
    rot = {}
    if cout_initial:
        rot[R.index[0] - pd.Timedelta(days=1)] = 1.0
    brut, net = [], []
    valeur_cout = 1.0
    for t in R.index:
        rt = R.loc[t]
        actifs = [k for k in w.index if derniere[k] is not None and t <= derniere[k]]
        sortis = [k for k in w.index if k not in actifs and w[k] != 0]
        for k in sortis:  # radiation : passage en liquidités
            cash += w[k]
            w[k] = 0.0
        g = rt.reindex(w.index).fillna(0.0)  # jour férié local (prix reportés) => rendement nul
        port = float((w * g).sum())  # rendement du jour (le cash rapporte 0)
        tot = float(w.sum() + cash)
        rp = port / tot
        brut.append(rp)
        w = w * (1 + g)
        if t in rb:
            vivants = [k for k in cibles.index if derniere[k] is not None and derniere[k] > t]
            cib = cibles[vivants] / cibles[vivants].sum()
            tot = float(w.sum() + cash)
            w_now = (w / tot).reindex(cib.index).fillna(0.0)
            # achats + ventes ; le redéploiement des liquidités est déjà compté dans les achats
            delta = (cib - w_now).abs().sum() + (w / tot).drop(index=cib.index, errors="ignore").abs().sum()
            rot[t] = float(delta)
            w = cib.reindex(w.index).fillna(0.0) * tot
            cash = 0.0
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
