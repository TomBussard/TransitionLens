# TransitionLens

How much does an emissions advantage matter once it is scaled by enterprise value? This public edition of a sustainable equity research project follows one carbon-price assumption through stock selection, portfolio weights and trading costs.

## Research toolkit

The public example follows a carbon-price signal end to end. The underlying library also takes dated company fundamentals, ranks value and quality against peers, separates clean-technology revenue from emissions efficiency, and computes momentum from a monthly return panel. Those additional factors can be inspected individually or used as inputs to a new selection. The default carbon portfolio uses the carbon score.

Starting from a score, you can select either tail of its distribution, compare equal weights with capped reference weights, and test quarterly rebalancing, annual rebalancing or buy and hold. The simulator returns a daily gross series, a net series and the turnover ledger. Weekly and monthly returns are compounded from those daily observations. [Signal library](a9/signaux.py) · [Portfolio rules](a9/portefeuilles.py) · [Return simulation](a9/backtest.py)

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

## Building the other research signals

For a value score I construct five yields. Earnings yield uses net margin and the price-to-sales ratio, which preserves the sign of earnings for a loss-making firm. I also use book-to-price, sales-to-price, cash-flow-to-price and the reported free-cash-flow yield. If $m_i$ is net margin in percent, the first two yields are

```math
E_i/P_i=\frac{m_i/100}{(P/S)_i},\qquad B_i/P_i=\frac{1}{(P/B)_i}.
```

Each available yield becomes a percentile within its industry. A group with fewer than eight usable observations falls back to its sector. The composite averages the available ranks when at least three are present. Quality uses the same approach for return on invested capital, return on equity, net margin and the negative of debt to assets.

```math
s_i^{\rm value}=\frac{1}{|J_i|}\sum_{j\in J_i}\mathrm{rank}_{\rm peer}(x_{ij}),\qquad |J_i|\ge3.
```

The green score averages the universe percentile of clean-technology revenue share and the peer percentile of negative carbon intensity when both are present. The momentum function looks back over eleven monthly returns and skips the latest month. It requires at least ten observations in that window.

```math
M_{i,t}=\prod_{j=1}^{11}(1+r_{i,t-j})-1.
```

### What the cap and cost rules change

The weighting function first tries a 5% limit for every issuer. If that cannot fully invest the portfolio, it can give up to four of the largest reference holdings a 10% limit. Holdings above 5% may total at most 40%. With monotonically decreasing reference weights, I reran the routine on **20, 16 and 15 issuers**. With 20 it returned 5% each. With 16, four issuers carried a combined 40% and the other twelve held 5% each. With 15 the routine marked the basket infeasible.

```math
\sum_i w_i=1,\qquad \max_i w_i\le0.10,\qquad \sum_{i:\,w_i>0.05}w_i\le0.40.
```

I kept the carbon universe, seed and trade dates fixed and changed only the charge per unit traded. Aggregate turnover was **119.99%**, including the 100% initial investment.

| Cost per unit traded | Gross return | Net return |
| --- | ---: | ---: |
| 0 basis points | 8.2254% | 8.2254% |
| 15 basis points | 8.2254% | 8.0308% |
| 50 basis points | 8.2254% | 7.5773% |

The three runs hold the same names. The final difference depends on both turnover and the dates when costs leave the compounding path. Use `--cost-bps 0`, `15` or `50` with the command below to reproduce the rows. [Cap implementation](a9/portefeuilles.py) · [Experiment](example.py)

## Run it

```sh
python -m pip install -r requirements.txt
python example.py
```

The random seed is fixed. Changing the carbon price, the selection threshold or the transaction cost in [the example](example.py) lets you repeat the experiment. The [research modules](a9) contain the original ranking, weighting and backtesting functions. The demonstration generates all its inputs locally.

Tom Bussard
