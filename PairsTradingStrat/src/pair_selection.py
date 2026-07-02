"""
pair_selection.py
------------------
Developed a statistical pairs trading model using co-integration across
30 equity pairs for automated mean-reversion signals.

Runs the Engle-Granger cointegration test on all within-sector ticker
combinations, filters by p-value, and selects the top pairs (target: 30)
ranked by cointegration strength. Also computes the OLS hedge ratio used
downstream to build the spread series for each pair.
"""

import os
import itertools
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import coint
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

# Same sector grouping as the data pipeline -- cointegration tests are only
# run within sectors, since cross-sector pairs rarely share a stable
# long-run equilibrium relationship.
SECTORS = {
    "Financials": ["JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "COF"],
    "Energy":     ["XOM", "CVX", "COP", "SLB", "EOG", "PSX", "VLO", "MPC", "OXY", "HES"],
    "Tech":       ["AAPL", "MSFT", "NVDA", "AMD", "INTC", "QCOM", "TXN", "AVGO", "MU", "ADI"],
    "Retail":     ["WMT", "TGT", "COST", "HD", "LOW", "TJX", "ROST", "KR", "DG", "BBY"],
}

PVALUE_THRESHOLD = 0.05
TARGET_N_PAIRS = 30


def compute_hedge_ratio(price_a: pd.Series, price_b: pd.Series) -> float:
    """OLS regression of price_a on price_b -> hedge ratio (beta)."""
    x = add_constant(price_b.values)
    model = OLS(price_a.values, x).fit()
    return model.params[1]


def test_pair_cointegration(price_a: pd.Series, price_b: pd.Series):
    """Runs Engle-Granger cointegration test, returns (t_stat, p_value)."""
    score, pvalue, _ = coint(price_a, price_b)
    return score, pvalue


def find_cointegrated_pairs(price_matrix: pd.DataFrame, sectors: dict,
                             pvalue_threshold=PVALUE_THRESHOLD):
    """
    Tests all within-sector ticker combinations for cointegration.
    Returns a DataFrame of candidate pairs sorted by p-value (strongest
    cointegration first).
    """
    results = []

    for sector, tickers in sectors.items():
        available = [t for t in tickers if t in price_matrix.columns]
        for ticker_a, ticker_b in itertools.combinations(available, 2):
            series_a = price_matrix[ticker_a]
            series_b = price_matrix[ticker_b]

            try:
                score, pvalue = test_pair_cointegration(series_a, series_b)
            except Exception:
                continue

            if pvalue < pvalue_threshold:
                hedge_ratio = compute_hedge_ratio(series_a, series_b)
                spread = series_a - hedge_ratio * series_b
                results.append({
                    "sector": sector,
                    "ticker_a": ticker_a,
                    "ticker_b": ticker_b,
                    "coint_score": score,
                    "pvalue": pvalue,
                    "hedge_ratio": hedge_ratio,
                    "spread_mean": spread.mean(),
                    "spread_std": spread.std(),
                })
                print(f"  [pair] {ticker_a}-{ticker_b} ({sector}): p={pvalue:.4f}, hedge_ratio={hedge_ratio:.3f}")

    df = pd.DataFrame(results)
    if df.empty:
        return df
    return df.sort_values("pvalue").reset_index(drop=True)


def select_top_pairs(candidates: pd.DataFrame, n=TARGET_N_PAIRS):
    """
    Selects the top-N pairs by cointegration strength, capping how many
    pairs share the same ticker so the portfolio isn't overly concentrated
    in a couple of names.
    """
    selected = []
    ticker_usage = {}
    max_uses_per_ticker = 4

    for _, row in candidates.iterrows():
        if len(selected) >= n:
            break
        a, b = row["ticker_a"], row["ticker_b"]
        if ticker_usage.get(a, 0) >= max_uses_per_ticker or ticker_usage.get(b, 0) >= max_uses_per_ticker:
            continue
        selected.append(row)
        ticker_usage[a] = ticker_usage.get(a, 0) + 1
        ticker_usage[b] = ticker_usage.get(b, 0) + 1

    return pd.DataFrame(selected).reset_index(drop=True)


def main():
    price_matrix = pd.read_csv(os.path.join(DATA_DIR, "price_matrix.csv"), index_col=0, parse_dates=True)
    print(f"Loaded price matrix: {price_matrix.shape}")

    # Use only the first half of history (the "formation period") to test
    # cointegration and fit hedge ratios -- the second half is left as an
    # out-of-sample trading period. This avoids look-ahead bias that would
    # come from fitting the hedge ratio on the same data being traded.
    split = len(price_matrix) // 2
    formation_data = price_matrix.iloc[:split]
    print(f"Formation period: {formation_data.index[0].date()} to {formation_data.index[-1].date()} ({len(formation_data)} days)")
    print(f"Testing within-sector pairs for cointegration (p < {PVALUE_THRESHOLD})...\n")

    candidates = find_cointegrated_pairs(formation_data, SECTORS)
    print(f"\nFound {len(candidates)} cointegrated candidate pairs.")

    top_pairs = select_top_pairs(candidates, n=TARGET_N_PAIRS)
    print(f"Selected top {len(top_pairs)} pairs for the strategy.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "selected_pairs.csv")
    top_pairs.to_csv(out_path, index=False)
    print(f"Saved selected pairs to {out_path}")


if __name__ == "__main__":
    main()
