"""Étape B — signaux, calculés uniquement avec l'information disponible à la date de décision.

Conventions :
  * Les multiples sont inversés en rendements (E/P, B/P, S/P, CF/P) : un rendement élevé = titre « bon marché ».
    Les bénéfices négatifs restent négatifs dans E/P (aucune exclusion implicite, aucun zéro imputé).
  * Les comparaisons se font en rangs centiles À L'INTÉRIEUR du groupe d'industrie (repli : secteur GICS
    si le groupe compte moins de `taille_min` observations), pour neutraliser les différences sectorielles.
  * Un score composite est une moyenne de rangs centiles ; la moyenne ignore les composantes manquantes
    mais exige au moins `min_comp` composantes disponibles.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def winsor(s: pd.Series, p: float = 0.01) -> pd.Series:
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def rang_pairs(u: pd.DataFrame, x: pd.Series, taille_min: int = 8) -> pd.Series:
    """Rang centile (0-1] dans le groupe d'industrie, repli sur le secteur GICS."""
    d = pd.DataFrame({"x": x, "g": u["industry_group"], "s": u["gics_sector_name"]})
    n_g = d.groupby("g")["x"].transform(lambda v: v.notna().sum())
    r_g = d.groupby("g")["x"].rank(pct=True)
    r_s = d.groupby("s")["x"].rank(pct=True)
    return r_g.where(n_g >= taille_min, r_s)


def composite(rangs: pd.DataFrame, min_comp: int = 3) -> pd.Series:
    n = rangs.notna().sum(axis=1)
    return rangs.mean(axis=1).where(n >= min_comp)


def valorisation(u: pd.DataFrame) -> pd.DataFrame:
    """Rendements de valorisation au 31/12/2024 (fichier imposé) et score Value relatif aux pairs."""
    v = pd.DataFrame(index=u.index)
    v["EP"] = u["Net margin"] / (100.0 * u["PS ratio"])         # E/P reconstitué (couvre les pertes)
    v["BP"] = 1.0 / u["PB ratio"].where(u["PB ratio"] > 0)
    v["SP"] = 1.0 / u["PS ratio"].where(u["PS ratio"] > 0)
    v["CFP"] = 1.0 / u["PCF ratio"].where(u["PCF ratio"] > 0)
    v["FCFY"] = u["FCF yield"] / 100.0
    v["SALES_EV"] = u["SALES"] / u["EV"].where(u["EV"] > 0)
    rangs = pd.DataFrame({k: rang_pairs(u, v[k]) for k in ["EP", "BP", "SP", "CFP", "FCFY"]})
    v["score_value"] = composite(rangs, 3)
    for k in rangs:
        v[f"rg_{k}"] = rangs[k]
    return v


def qualite(u: pd.DataFrame) -> pd.DataFrame:
    q = pd.DataFrame(index=u.index)
    q["ROIC"] = u["ROIC"]
    q["ROE"] = u["ROE"]
    q["MARGE_NETTE"] = u["Net margin"]
    q["MARGE_BRUTE"] = u["Gross margin"]
    q["DETTE_ACTIFS"] = u["Debt assets"]
    rangs = pd.DataFrame({
        "ROIC": rang_pairs(u, u["ROIC"]), "ROE": rang_pairs(u, u["ROE"]),
        "MARGE_NETTE": rang_pairs(u, u["Net margin"]), "LEVIER_INV": rang_pairs(u, -u["Debt assets"]),
    })
    q["score_qualite"] = composite(rangs, 3)
    return q


def vert(u: pd.DataFrame) -> pd.DataFrame:
    """Indicateurs environnementaux NON agrégés + un score composite documenté (rangs)."""
    g = pd.DataFrame(index=u.index)
    g["CT"] = u["CT_TOTAL_MAX_REV"] / 100.0
    g["TAX_EST"] = u["EST_EU_TAXONOMY_MAX_REV"] / 100.0
    g["INTENSITE_S12"] = u["INTENSITY_SCOPE_1"] + u["INTENSITY_SCOPE_2"]
    g["rg_efficacite_carbone"] = rang_pairs(u, -g["INTENSITE_S12"])     # 1 = moins intensif du groupe
    g["PILIER_E"] = u["ENVIRONMENTAL_PILLAR_SCORE"]
    # Score vert composite (classement des titres déjà éligibles uniquement) :
    # moyenne des rangs centiles univers de la part CT et de l'efficacité carbone intra-groupe (poids égaux).
    g["score_vert"] = pd.concat([g["CT"].rank(pct=True), g["rg_efficacite_carbone"]], axis=1).mean(axis=1)
    return g


def avantage_cout_carbone(u: pd.DataFrame, prix_carbone: float = 65.0) -> pd.DataFrame:
    """Méthode C (approximation) : coût carbone évité vs la médiane des pairs, rapporté à l'EV.

    avantage (M EUR/an) = (intensité médiane des pairs - intensité propre) [tCO2e/M EUR] x CA [M EUR] x prix [EUR/t] / 1e6
    Hypothèses fortes : toutes les émissions scopes 1+2 seraient tarifées au prix indiqué, sans quotas gratuits,
    à production inchangée. Potentiel théorique, PAS un bénéfice réalisé ni une économie documentée.
    """
    i = u["INTENSITY_SCOPE_1"] + u["INTENSITY_SCOPE_2"]
    med = i.groupby(u["industry_group"]).transform("median")
    tonnes_evitees = (med - i) * u["SALES"]                  # tCO2e/an (M EUR x t/M EUR)
    avantage_meur = tonnes_evitees * prix_carbone / 1e6       # M EUR/an
    out = pd.DataFrame({"tonnes_evitees_vs_pairs": tonnes_evitees, "avantage_carbone_MEUR": avantage_meur,
                        "rendement_avantage_carbone": avantage_meur / u["EV"].where(u["EV"] > 0)}, index=u.index)
    return out


def momentum_12_1(r_m: pd.DataFrame, date: str) -> pd.Series:
    """Rendement cumulé de t-12 à t-1 mois (mois t exclu), à partir de rendements mensuels."""
    r = r_m.loc[:pd.Timestamp(date)]
    fen = r.iloc[-12:-1]
    ok = fen.notna().sum() >= 10
    return ((1 + fen).prod() - 1).where(ok)
