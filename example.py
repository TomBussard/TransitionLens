"""Trace one carbon-price assumption through a synthetic equity portfolio."""
import numpy as np
import pandas as pd

from a9.backtest import simuler
from a9.portefeuilles import capi_plafonne, selection_quantile
from a9.signaux import avantage_cout_carbone


def run_example():
    random = np.random.default_rng(2026)
    size = 80
    companies = pd.Index([f"Company {i:02d}" for i in range(1, size + 1)])
    universe = pd.DataFrame({
        "industry_group": np.repeat(["Materials", "Industrials", "Utilities", "Transport"], 20),
        "INTENSITY_SCOPE_1": random.uniform(5, 150, size),
        "INTENSITY_SCOPE_2": random.uniform(2, 60, size),
        "SALES": random.uniform(1000, 12000, size),
        "EV": random.uniform(2000, 30000, size),
    }, index=companies)
    scores = avantage_cout_carbone(universe, prix_carbone=65)["rendement_avantage_carbone"]
    selected = selection_quantile(scores, 0.30)
    weights, feasible = capi_plafonne(selected, universe["EV"])
    if not feasible:
        raise ValueError("Selected universe cannot meet the portfolio weight limits.")
    dates = pd.bdate_range("2024-01-02", periods=252)
    returns = pd.DataFrame(random.normal(0.0002, 0.012, (len(dates), size)),
                           index=dates, columns=companies)
    result = simuler(weights, returns, freq="Q", cout_bps=15.0)
    return weights, result


def main():
    weights, result = run_example()
    print("Synthetic example with a carbon price of EUR 65 per tonne")
    print(f"Selected companies: {len(weights)} of 80")
    print(f"Largest initial position: {weights.max():.2%}")
    print(f"Gross simulated return: {(1 + result['rend_brut']).prod() - 1:.2%}")
    print(f"Net simulated return:   {(1 + result['rend_net']).prod() - 1:.2%}")


if __name__ == "__main__":
    main()
