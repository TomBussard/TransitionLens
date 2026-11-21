# TransitionLens

How much does an emissions advantage matter once it is scaled by enterprise value? This public edition of a sustainable equity research project follows one carbon-price assumption through stock selection, portfolio weights and trading costs.

## The experiment

The signal compares a company's combined Scope 1 and Scope 2 emissions intensity with its industry median. The model multiplies the difference by revenue and a hypothetical carbon price, then scales it by enterprise value. The result measures sensitivity to that assumption. Its interpretation depends on the assumed carbon price and the emissions covered.

The example ranks 80 fictional companies, selects the top 30 percent, caps positions and rebalances quarterly. The backtest tracks gross and net returns separately so the effect of turnover is visible.

At EUR 65 per tonne, 24 of the 80 companies entered the portfolio and the largest starting weight was 5 percent. Over the 252 simulated trading days, the portfolio gained 8.23 percent before costs and 8.03 percent after costs. These figures describe the synthetic demonstration.

![Synthetic portfolio before and after costs, alongside its initial position weights](figures/portfolio-path.png)

## From a company to a daily return

| Stage | Calculation | Unit |
| --- | --- | --- |
| Peer comparison | Industry median intensity minus company intensity | Tonnes per EUR million of sales |
| Cost scenario | Intensity gap × sales × carbon price | EUR per year |
| Equity signal | Convert the annual cost advantage to EUR millions and divide by enterprise value | Fraction of enterprise value |
| Holding period | Let weights move with daily returns, then trade back to the targets at quarter end | Gross and net daily return |

### One company's score

Let $I_i$ be combined Scope 1 and Scope 2 intensity in tonnes per EUR million of sales, $M_g$ the median in the same industry, $S_i$ annual sales and $EV_i$ positive enterprise value, both in EUR millions. At a carbon price $p$ in EUR per tonne the model holds production fixed.

```math
A_i=\frac{(M_g-I_i)S_i p}{10^6},\qquad s_i=\frac{A_i}{EV_i}
```

In the seeded run, **Company 70** has an intensity of **68.06** against a transport-sector median of **99.29**. Applied to EUR 10,757.13 million of sales, the unrounded gap represents 335,956 tonnes. At EUR 65 per tonne that gives **EUR 21.84 million** a year, or **0.640%** of its EUR 3,412.85 million enterprise value. This is the highest score in the sample. A company above its peer median receives a negative score.

### From a score to a position

There are four industries with 20 companies each. I rank all 80 scores, take the top 30% and weight those companies by enterprise value. I redistribute excess weight among issuers with room below the 5% cap. Between quarter ends the weights drift with the simulated daily returns. At a rebalance, let $w_i^-$ be the weight after the market move and $w_i^*$ the target.

```math
\tau_t=\sum_i |w_i^*-w_i^-|,\qquad r_t^{\mathrm{net}}=r_t^{\mathrm{gross}}-0.0015\,\tau_t
```

Buying 1% and selling 1% counts as 2% traded. The first rebalance trades 6.57% of the portfolio, costing roughly **0.99 basis points**. The initial investment incurs a separate 15 basis point charge. Compounding the net daily returns gives the **8.03%** shown above. The demonstration generates stock returns independently of the emissions inputs, so the path illustrates portfolio construction and costs. [Score calculation](a9/signaux.py) · [Weight caps](a9/portefeuilles.py) · [Backtest](a9/backtest.py)

Try running the example again with zero costs. The constituents and gross return should agree with the original run, and the net path should match the gross path. Multiplying a positive carbon price by two doubles the signal in this linear scenario and preserves its ranking.

```sh
python example.py --carbon-price 65 --cost-bps 0
```

A missing daily quote carries the previous valuation. After a company's final quote its position is held in cash until the next rebalance.

## Run it

```sh
python -m pip install -r requirements.txt
python example.py
```

The random seed is fixed. Changing the carbon price, the selection threshold or the transaction cost in [the example](example.py) lets you repeat the experiment. The [research modules](a9) contain the original ranking, weighting and backtesting functions. The demonstration generates all its inputs locally.

Tom Bussard
