"""
generate_synthetic_data.py
---------------------------
DEV/TEST ONLY. This sandbox environment cannot reach Yahoo Finance's servers
(network egress is restricted), so this script generates a synthetic-but-
realistic price dataset with the SAME schema data_pipeline.py produces, so
the rest of the pipeline (pair_selection, signals, backtest) can be built
and validated end-to-end.

On a normal machine, run `src/data_pipeline.py` instead to pull real
yFinance data -- the rest of the pipeline is identical either way.

Method: simulate correlated random walks per sector, then deliberately
construct several genuinely cointegrated pairs within each sector by
generating one "leader" series and building "follower" series as the
leader plus a stationary (mean-reverting) spread -- which is exactly what
cointegration means. Also include some non-cointegrated names as noise so
pair selection has real filtering to do.
"""

import os
import numpy as np
import pandas as pd

np.random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
N_DAYS = 252 * 5  # 5 years of trading days

UNIVERSE = {
    "Financials": ["JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "COF"],
    "Energy":     ["XOM", "CVX", "COP", "SLB", "EOG", "PSX", "VLO", "MPC", "OXY", "HES"],
    "Tech":       ["AAPL", "MSFT", "NVDA", "AMD", "INTC", "QCOM", "TXN", "AVGO", "MU", "ADI"],
    "Retail":     ["WMT", "TGT", "COST", "HD", "LOW", "TJX", "ROST", "KR", "DG", "BBY"],
}

START_PRICES = {
    "JPM": 140, "BAC": 35, "WFC": 45, "C": 55, "GS": 350, "MS": 90, "USB": 45, "PNC": 150, "TFC": 40, "COF": 120,
    "XOM": 100, "CVX": 155, "COP": 105, "SLB": 45, "EOG": 120, "PSX": 115, "VLO": 130, "MPC": 145, "OXY": 60, "HES": 140,
    "AAPL": 175, "MSFT": 340, "NVDA": 450, "AMD": 110, "INTC": 35, "QCOM": 130, "TXN": 175, "AVGO": 900, "MU": 80, "ADI": 190,
    "WMT": 65, "TGT": 140, "COST": 550, "HD": 330, "LOW": 220, "TJX": 90, "ROST": 120, "KR": 45, "DG": 130, "BBY": 75,
}


def simulate_leader(start_price, n_days, daily_vol=0.015, drift=0.0002):
    """Random walk (geometric brownian motion) for a sector 'leader' stock."""
    returns = np.random.normal(drift, daily_vol, n_days)
    prices = start_price * np.exp(np.cumsum(returns))
    return prices


def simulate_cointegrated_follower(leader_prices, start_price, hedge_ratio=1.0,
                                    spread_vol=0.09, mean_reversion_speed=0.015,
                                    regime_break_prob=0.008, idiosyncratic_vol=0.022):
    """
    Builds a follower series cointegrated with the leader by construction,
    but with added noise and occasional temporary "regime breaks" so the
    relationship isn't perfectly clean -- more like a real equity pair.
    """
    n_days = len(leader_prices)
    log_leader = np.log(leader_prices)

    spread = np.zeros(n_days)
    spread[0] = 0
    regime_shock = 0.0
    for t in range(1, n_days):
        shock = np.random.normal(0, spread_vol)
        if np.random.rand() < regime_break_prob:
            regime_shock = np.random.normal(0, 0.08)
        regime_shock *= 0.9
        spread[t] = spread[t - 1] - mean_reversion_speed * spread[t - 1] + shock + regime_shock

    idio_noise = np.cumsum(np.random.normal(0, idiosyncratic_vol, n_days)) * 0.15

    # Real-world cointegration relationships aren't static -- the true hedge
    # ratio drifts slowly over time. A static hedge ratio fit on a formation
    # period will therefore be slightly stale by the trading period, which
    # is exactly what happens in live pairs trading.
    drift_path = np.cumsum(np.random.normal(0, 0.0006, n_days))
    time_varying_hedge = hedge_ratio + drift_path

    log_follower = np.log(start_price) + time_varying_hedge * (log_leader - log_leader[0]) + spread + idio_noise
    return np.exp(log_follower)


def simulate_independent(start_price, n_days, daily_vol=0.018, drift=0.0001):
    """Plain random walk with no relationship to anything -- acts as noise
    so pair selection must actually filter, not just pass everything."""
    returns = np.random.normal(drift, daily_vol, n_days)
    return start_price * np.exp(np.cumsum(returns))


def generate_universe():
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=N_DAYS)
    all_series = {}

    for sector, tickers in UNIVERSE.items():
        # first ticker in each sector is the "leader"
        leader_ticker = tickers[0]
        leader_prices = simulate_leader(START_PRICES[leader_ticker], N_DAYS)
        all_series[leader_ticker] = leader_prices

        # ~60% of remaining tickers are genuinely cointegrated with leader
        remaining = tickers[1:]
        n_cointegrated = int(len(remaining) * 0.6)
        cointegrated_tickers = remaining[:n_cointegrated]
        noise_tickers = remaining[n_cointegrated:]

        for ticker in cointegrated_tickers:
            hedge_ratio = np.random.uniform(0.6, 1.4)
            mrs = np.random.uniform(0.04, 0.12)  # mean reversion speed
            prices = simulate_cointegrated_follower(
                leader_prices, START_PRICES[ticker],
                hedge_ratio=hedge_ratio, mean_reversion_speed=mrs
            )
            all_series[ticker] = prices

        for ticker in noise_tickers:
            prices = simulate_independent(START_PRICES[ticker], N_DAYS)
            all_series[ticker] = prices

    matrix = pd.DataFrame(all_series, index=dates)
    return matrix


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Generating {N_DAYS} days of synthetic price data for {sum(len(v) for v in UNIVERSE.values())} tickers...")
    matrix = generate_universe()

    for ticker in matrix.columns:
        df = pd.DataFrame({
            "close": matrix[ticker],
            "volume": np.random.randint(1_000_000, 20_000_000, len(matrix)),
        }, index=matrix.index)
        df.to_csv(os.path.join(DATA_DIR, f"{ticker}.csv"))

    matrix.to_csv(os.path.join(DATA_DIR, "price_matrix.csv"))
    print(f"Saved {matrix.shape[1]} tickers x {matrix.shape[0]} days to {DATA_DIR}")
    print("NOTE: this is synthetic data for local pipeline development only.")
    print("Run src/data_pipeline.py on a machine with normal network access for real yFinance data.")


if __name__ == "__main__":
    main()
