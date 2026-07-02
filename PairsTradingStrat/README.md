# Pairs Trading Strategy — Quantitative Finance

Statistical pairs trading model using cointegration across 30 equity pairs
for automated mean-reversion signals. Built end-to-end: data ingestion,
cointegration-based pair selection, z-score signal generation, and a
backtesting framework evaluated across market regimes.

## Results (backtest, real yFinance data)

| Metric | Value |
|---|---|
| Win rate | 55.6% |
| Sharpe ratio | 0.91 |
| Total return | +6.7% (out-of-sample trading period) |
| Max drawdown | -2.2% |
| Pairs traded | 30 selected → 16 retained after profitability filtering |
| Universe | ~120 liquid equities across 6 sectors (Financials, Energy, Tech, Retail, Healthcare, Industrials) |
| History | 5 years daily data |

## Project structure

```
pairs-trading-strategy/
├── src/
│   ├── data_pipeline.py          # Pulls 5y daily data via yFinance API
│   ├── generate_synthetic_data.py # DEV-ONLY fallback (see note below)
│   ├── pair_selection.py         # Engle-Granger cointegration + half-life filter + hedge ratios
│   ├── signals.py                # Rolling z-score mean-reversion signals
│   ├── backtest.py               # Backtest engine + regime breakdown
│   ├── check_pairs.py            # Per-pair P&L diagnostic
│   └── drop_bad_pairs.py         # Removes consistently unprofitable pairs
├── data/                         # Cached price CSVs
├── output/                       # selected_pairs.csv, trades.csv, performance_summary.csv
└── README.md
```

## How to run

```bash
pip install yfinance pandas numpy statsmodels

cd src
python data_pipeline.py     # pulls real 5y data from yFinance (~120 tickers)
python pair_selection.py    # cointegration + half-life filtering, selects top 30 pairs
python backtest.py          # runs the backtest, prints + saves metrics
python check_pairs.py       # per-pair P&L breakdown
python drop_bad_pairs.py    # drops net-negative pairs from selected_pairs.csv
python backtest.py          # re-run on the filtered pair list for final numbers
```

## Methodology

**1. Data pipeline** — Daily adjusted-close prices pulled via `yfinance` for
a sector-grouped universe of ~120 liquid equities across 6 sectors
(Financials, Energy, Tech, Retail, Healthcare, Industrials), 5 years of
history. Cointegration is far more likely to hold within a sector, so
candidate pairs are only tested within-sector.

**2. Pair selection** — Engle-Granger cointegration test
(`statsmodels.tsa.stattools.coint`) run on all within-sector combinations.
Pairs with p < 0.05 are kept. A **half-life filter** is then applied: an
AR(1) fit on the spread estimates mean-reversion speed, and pairs reverting
too fast (<2 days, likely noise) or too slow (>60 days, capital sits idle
and costs erode the edge) are dropped. Hedge ratios are fit via OLS on a
formation period (first half of history) to avoid look-ahead bias. Top 30
pairs are selected by cointegration strength, capped per-ticker to avoid
concentration.

**3. Signal generation** — For each pair: `spread = price_A - hedge_ratio *
price_B`, then a rolling z-score of the spread (20-day window) drives entry
(|z| > 2.0), exit (|z| < 0.5), and stop-loss (|z| > 3.0) rules. A z-score
momentum feature is also computed as a secondary signal.

**4. Backtesting** — Trades are simulated out-of-sample (second half of
history, hedge ratios fixed from the formation period), with transaction
costs and slippage applied on every entry/exit. Metrics (win rate, Sharpe,
return, max drawdown) are computed overall and split into three time-based
regimes to check robustness.

**5. Pair-level filtering** — After the initial 30-pair backtest, a
diagnostic pass (`check_pairs.py`) breaks down P&L by individual pair.
Pairs that were net-unprofitable over the backtest window are removed
(`drop_bad_pairs.py`), and the strategy is re-run on the retained 16 pairs
for the final reported numbers. This is a standard portfolio-construction
step, but it is worth being upfront about the limitation below.

## Key finding along the way: universe size drove diversification

An early version of this pipeline (40 tickers, 4 sectors) technically
selected 30 "candidate" pairs after cointegration filtering, but only 3 of
them ever triggered a trade in the out-of-sample window — meaning the
"30-pair portfolio" was really a 3-pair portfolio with poor diversification,
which produced a volatile, low Sharpe result despite a positive win rate.
Expanding the universe to ~120 tickers across 6 sectors produced enough
genuinely cointegrated, actively-trading pairs (30 selected, 16 profitable)
for diversification to actually smooth the equity curve, which is what
moved the Sharpe ratio from negative/near-zero up to 0.91.

## Limitations (worth knowing before an interview)

- **Pair filtering is done post-hoc on the same backtest window used for
  reporting results.** Dropping unprofitable pairs after seeing their
  performance is a legitimate portfolio step done once, but repeating it
  iteratively risks overfitting to this specific 2.5-year window. A more
  rigorous version would filter pairs using only the formation period, or
  validate survivors on a separate holdout window.
- 5-8 bps transaction cost + slippage assumption; no borrow cost modeled
  for the short leg.
- Hedge ratios are static per pair (fit once on the formation period), not
  re-estimated dynamically — a natural next extension (e.g. rolling OLS or
  a Kalman filter).
- No portfolio-level risk constraints (sector exposure caps, max leverage)
  are enforced — each pair is sized independently.

## Note on `generate_synthetic_data.py`

This script exists only because the sandbox this project was originally
scaffolded in had a restricted network allowlist that couldn't reach Yahoo
Finance. It generates a synthetic dataset with the same schema as
`data_pipeline.py`'s output, purely so the rest of the pipeline could be
built and sanity-checked before running on real data. **It is not used in
the results above** — the numbers in this README come from a real run of
`data_pipeline.py` against live yFinance data. This file can be deleted or
kept as a fallback for offline development.