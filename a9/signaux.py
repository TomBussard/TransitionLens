"""Signals use the observations available on the decision date. Valuation multiples are expressed as yields and a negative earnings yield stays negative. Industry percentile ranks make firms with different business models easier to compare."""

from __future__ import annotations

import numpy as np
import pandas as pd


def winsor(s: pd.Series, p: float = 0.01) -> pd.Series:
    lo, hi = s.quantile(p), s.quantile(1 - p)
    return s.clip(lo, hi)


def rang_pairs(u: pd.DataFrame, x: pd.Series, taille_min: int = 8) -> pd.Series:
    """Rank each stock against its industry peers, falling back to its sector for small groups."""
    d = pd.DataFrame({"x": x, "g": u["industry_group"], "s": u["gics_sector_name"]})
    n_g = d.groupby("g")["x"].transform(lambda v: v.notna().sum())
    r_g = d.groupby("g")["x"].rank(pct=True)
    r_s = d.groupby("s")["x"].rank(pct=True)
    return r_g.where(n_g >= taille_min, r_s)


def composite(rangs: pd.DataFrame, min_comp: int = 3) -> pd.Series:
    n = rangs.notna().sum(axis=1)
    return rangs.mean(axis=1).where(n >= min_comp)


def valorisation(u: pd.DataFrame) -> pd.DataFrame:
    """Calculate valuation yields and a peer-relative value score from the dated input snapshot."""
    v = pd.DataFrame(index=u.index)
    v["EP"] = u["Net margin"] / (
        100.0 * u["PS ratio"]
    )  # Net margin keeps loss-making firms in the earnings yield.
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
    rangs = pd.DataFrame(
        {
            "ROIC": rang_pairs(u, u["ROIC"]),
            "ROE": rang_pairs(u, u["ROE"]),
            "MARGE_NETTE": rang_pairs(u, u["Net margin"]),
            "LEVIER_INV": rang_pairs(u, -u["Debt assets"]),
        }
    )
    q["score_qualite"] = composite(rangs, 3)
    return q


def vert(u: pd.DataFrame) -> pd.DataFrame:
    """Return the separate environmental measures alongside their equal-weight percentile score."""
    g = pd.DataFrame(index=u.index)
    g["CT"] = u["CT_TOTAL_MAX_REV"] / 100.0
    g["TAX_EST"] = u["EST_EU_TAXONOMY_MAX_REV"] / 100.0
    g["INTENSITE_S12"] = u["INTENSITY_SCOPE_1"] + u["INTENSITY_SCOPE_2"]
    g["rg_efficacite_carbone"] = rang_pairs(
        u, -g["INTENSITE_S12"]
    )  # The least carbon-intensive peer receives the highest rank.
    g["PILIER_E"] = u["ENVIRONMENTAL_PILLAR_SCORE"]
    # Give clean-tech revenue and carbon efficiency the same weight.

    g["score_vert"] = pd.concat([g["CT"].rank(pct=True), g["rg_efficacite_carbone"]], axis=1).mean(
        axis=1
    )
    return g


def avantage_cout_carbone(u: pd.DataFrame, prix_carbone: float = 65.0) -> pd.DataFrame:
    """Estimate the annual cost difference from a company's industry median.

    The scenario prices all Scope 1 and Scope 2 emissions and holds production fixed.
    Revenue and enterprise value are in millions of euros. The result is a modelled sensitivity."""
    i = u["INTENSITY_SCOPE_1"] + u["INTENSITY_SCOPE_2"]
    med = i.groupby(u["industry_group"]).transform("median")
    tonnes_evitees = (med - i) * u["SALES"]  # Tonnes per year
    avantage_meur = tonnes_evitees * prix_carbone / 1e6  # Millions of euros per year
    out = pd.DataFrame(
        {
            "tonnes_evitees_vs_pairs": tonnes_evitees,
            "avantage_carbone_MEUR": avantage_meur,
            "rendement_avantage_carbone": avantage_meur / u["EV"].where(u["EV"] > 0),
        },
        index=u.index,
    )
    return out


def momentum_12_1(r_m: pd.DataFrame, date: str) -> pd.Series:
    """Compound monthly returns over the prior window, leaving out the most recent month."""
    r = r_m.loc[: pd.Timestamp(date)]
    fen = r.iloc[-12:-1]
    ok = fen.notna().sum() >= 10
    return ((1 + fen).prod() - 1).where(ok)
