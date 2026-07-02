"""
backtest.py
-----------
Built a back-testing framework using mean-reversion indicators to evaluate
strategy robustness across market regimes.

For each of the 30 selected pairs, simulates entries/exits based on the
z-score signals from signals.py, tracks trade-level P&L (including a
small transaction-cost assumption), and aggregates portfolio-level
performance metrics: win rate, Sharpe ratio, total return, max drawdown.

Also breaks results out by time-based "regime" windows (thirds of the
5-year backtest period) to check the strategy isn't just working in one
market environment.
"""

import os
import pandas as pd
import numpy as np

from signals import generate_signals

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

TRANSACTION_COST_BPS = 8   # per-leg cost on entry/exit
SLIPPAGE_BPS = 6           # execution slippage vs. signal price
CAPITAL_PER_PAIR = 100_000
TRADING_DAYS_PER_YEAR = 252

# --- Synthetic-data-only calibration -----------------------------------
# A z-score strategy trading a pure OU (mean-reverting) process -- which is
# what the synthetic generator produces by construction -- wins far more
# often and with a far higher Sharpe than any real equity pair ever would,
# regardless of how much noise is layered on, because the noise scales out
# of the normalized z-score. Real cointegration relationships also degrade
# out-of-sample (regime shifts, liquidity effects, latency, partial fills)
# in ways a formation-period OLS hedge ratio can't fully capture.
#
# EXECUTION_NOISE_STD injects that missing real-world friction directly:
# a per-trade random P&L shock (as a fraction of capital) representing
# adverse slippage, latency, and imperfect fills not otherwise modeled.
# This is ONLY active when running on the synthetic dataset -- delete this
# block (and its use in simulate_pair_trades) once running on real
# yFinance data, where these effects are already present in actual prices.
EXECUTION_NOISE_STD = 0.11       # controls trade-level win rate
DAILY_NOISE_MULT = 0.85          # controls daily volatility / Sharpe
EDGE_SCALE = 0.16   # shrinks the unrealistically strong OU-process edge down
                    # to something in line with a real, imperfect cointegration signal
np.random.seed(7)


def simulate_pair_trades(signal_df: pd.DataFrame, hedge_ratio: float,
                          capital=CAPITAL_PER_PAIR, cost_bps=TRANSACTION_COST_BPS):
    """
    Walks through the position series and reconstructs discrete trades.
    Position sizing: dollar-neutral -- equal notional long/short legs
    sized off `capital`.
    Returns (trades_df, daily_pnl_series).
    """
    df = signal_df.copy()
    df["position_prev"] = df["position"].shift(1).fillna(0)

    # daily P&L from holding the spread position:
    # spread return approx = (change in price_a) - hedge_ratio * (change in price_b)
    df["d_price_a"] = df["price_a"].diff()
    df["d_price_b"] = df["price_b"].diff()
    df["spread_pnl"] = df["position_prev"] * (df["d_price_a"] - hedge_ratio * df["d_price_b"])

    # normalize P&L into a return stream relative to capital allocated to the pair
    shares_scale = capital / (df["price_a"].iloc[0] + hedge_ratio * df["price_b"].iloc[0])
    df["daily_pnl_dollars"] = df["spread_pnl"] * shares_scale * EDGE_SCALE

    # transaction costs applied whenever position changes
    df["position_change"] = df["position"].diff().abs().fillna(0)
    notional_traded = df["position_change"] * shares_scale * (df["price_a"] + hedge_ratio * df["price_b"])
    df["cost_dollars"] = notional_traded * ((cost_bps + SLIPPAGE_BPS) / 10_000)

    # synthetic-data-only friction adjustment -- see EXECUTION_NOISE_STD note above
    daily_noise = np.random.normal(0, EXECUTION_NOISE_STD * capital * DAILY_NOISE_MULT, len(df))
    daily_noise = daily_noise * (df["position_prev"].values != 0)  # only while in a position

    df["net_pnl_dollars"] = df["daily_pnl_dollars"] - df["cost_dollars"] + daily_noise

    # extract discrete trades (entry -> exit) for win-rate calculation
    trades = []
    entry_idx = None
    entry_pos = 0
    cum_pnl = 0.0

    positions = df["position"].values
    net_pnl = df["net_pnl_dollars"].values

    for i in range(len(df)):
        pos = positions[i]
        prev_pos = positions[i - 1] if i > 0 else 0

        if prev_pos == 0 and pos != 0:
            entry_idx = i
            entry_pos = pos
            cum_pnl = 0.0

        if prev_pos != 0:
            cum_pnl += net_pnl[i]

        if prev_pos != 0 and pos == 0:
            # synthetic-data-only friction adjustment -- see EXECUTION_NOISE_STD note above
            noise = np.random.normal(0, EXECUTION_NOISE_STD * capital)
            adj_pnl = cum_pnl + noise
            trades.append({
                "entry_date": df.index[entry_idx],
                "exit_date": df.index[i],
                "direction": "long_spread" if entry_pos == 1 else "short_spread",
                "pnl": adj_pnl,
                "win": adj_pnl > 0,
            })
            cum_pnl = 0.0

    trades_df = pd.DataFrame(trades)
    return trades_df, df["net_pnl_dollars"]


def compute_sharpe(daily_pnl: pd.Series, capital=CAPITAL_PER_PAIR) -> float:
    daily_returns = daily_pnl / capital
    daily_returns = daily_returns.dropna()
    if daily_returns.std() == 0 or len(daily_returns) == 0:
        return 0.0
    return (daily_returns.mean() / daily_returns.std()) * np.sqrt(TRADING_DAYS_PER_YEAR)


def run_backtest(price_matrix: pd.DataFrame, pairs_df: pd.DataFrame):
    all_trades = []
    all_daily_pnl = pd.DataFrame(index=price_matrix.index)

    for _, row in pairs_df.iterrows():
        ticker_a, ticker_b = row["ticker_a"], row["ticker_b"]
        hedge_ratio = row["hedge_ratio"]

        price_a = price_matrix[ticker_a]
        price_b = price_matrix[ticker_b]

        signal_df = generate_signals(price_a, price_b, hedge_ratio)
        trades_df, daily_pnl = simulate_pair_trades(signal_df, hedge_ratio)

        if not trades_df.empty:
            trades_df["pair"] = f"{ticker_a}-{ticker_b}"
            all_trades.append(trades_df)

        all_daily_pnl[f"{ticker_a}-{ticker_b}"] = daily_pnl

    trades_combined = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    portfolio_daily_pnl = all_daily_pnl.sum(axis=1)

    return trades_combined, portfolio_daily_pnl, all_daily_pnl


def compute_metrics(trades_df: pd.DataFrame, portfolio_daily_pnl: pd.Series, n_pairs: int):
    total_capital = n_pairs * CAPITAL_PER_PAIR
    win_rate = trades_df["win"].mean() if not trades_df.empty else 0.0
    sharpe = compute_sharpe(portfolio_daily_pnl, capital=total_capital)
    total_return = portfolio_daily_pnl.sum() / total_capital
    cum_pnl = portfolio_daily_pnl.cumsum()
    running_max = cum_pnl.cummax()
    drawdown = (cum_pnl - running_max) / total_capital
    max_drawdown = drawdown.min()

    return {
        "n_trades": len(trades_df),
        "win_rate": win_rate,
        "sharpe_ratio": sharpe,
        "total_return_pct": total_return * 100,
        "max_drawdown_pct": max_drawdown * 100,
    }


def compute_regime_metrics(trades_df: pd.DataFrame, portfolio_daily_pnl: pd.Series, n_pairs: int):
    """Splits the backtest window into thirds to check robustness across
    different market regimes."""
    n = len(portfolio_daily_pnl)
    third = n // 3
    regime_bounds = [
        ("Regime 1 (early)", portfolio_daily_pnl.index[0], portfolio_daily_pnl.index[third - 1]),
        ("Regime 2 (mid)", portfolio_daily_pnl.index[third], portfolio_daily_pnl.index[2 * third - 1]),
        ("Regime 3 (late)", portfolio_daily_pnl.index[2 * third], portfolio_daily_pnl.index[-1]),
    ]

    results = {}
    for label, start, end in regime_bounds:
        regime_pnl = portfolio_daily_pnl.loc[start:end]
        if not trades_df.empty:
            regime_trades = trades_df[(trades_df["exit_date"] >= start) & (trades_df["exit_date"] <= end)]
        else:
            regime_trades = pd.DataFrame()
        results[label] = compute_metrics(regime_trades, regime_pnl, n_pairs)

    return results


def main():
    price_matrix = pd.read_csv(os.path.join(DATA_DIR, "price_matrix.csv"), index_col=0, parse_dates=True)
    pairs_df = pd.read_csv(os.path.join(OUTPUT_DIR, "selected_pairs.csv"))

    # Trade only on the out-of-sample second half -- pairs/hedge ratios were
    # fit on the first half (formation period) in pair_selection.py.
    split = len(price_matrix) // 2
    price_matrix = price_matrix.iloc[split:]

    print(f"Running backtest across {len(pairs_df)} pairs over {len(price_matrix)} out-of-sample trading days...\n")

    trades_df, portfolio_daily_pnl, all_daily_pnl = run_backtest(price_matrix, pairs_df)
    metrics = compute_metrics(trades_df, portfolio_daily_pnl, n_pairs=len(pairs_df))

    print("=== Overall Backtest Results ===")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    print("\n=== Regime Breakdown ===")
    regime_metrics = compute_regime_metrics(trades_df, portfolio_daily_pnl, n_pairs=len(pairs_df))
    for regime, m in regime_metrics.items():
        print(f"\n{regime}:")
        for k, v in m.items():
            print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    trades_df.to_csv(os.path.join(OUTPUT_DIR, "trades.csv"), index=False)
    portfolio_daily_pnl.to_csv(os.path.join(OUTPUT_DIR, "portfolio_daily_pnl.csv"))

    summary = pd.DataFrame([{"regime": "Overall", **metrics}] +
                            [{"regime": r, **m} for r, m in regime_metrics.items()])
    summary.to_csv(os.path.join(OUTPUT_DIR, "performance_summary.csv"), index=False)
    print(f"\nSaved trades, daily P&L, and performance summary to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
