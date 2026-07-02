"""
signals.py
----------
Built the mean-reversion indicators (feature engineering + predictive
signals) used to generate entry/exit signals for each cointegrated pair:

  - spread            = price_A - hedge_ratio * price_B
  - rolling mean/std   of the spread over a lookback window
  - z-score            = (spread - rolling_mean) / rolling_std
  - spread momentum    = short-term rate of change of the z-score
                          (used as a secondary predictive feature to avoid
                          entering right as a reversion is stalling out)

Entry / exit rules:
  - Enter SHORT the spread when z-score >  ENTRY_Z  (spread too high, bet it falls)
  - Enter LONG  the spread when z-score < -ENTRY_Z  (spread too low, bet it rises)
  - Exit when z-score reverts back within EXIT_Z of zero
  - Stop-loss exit if z-score keeps moving beyond STOP_Z (thesis invalidated)
"""

import pandas as pd
import numpy as np

ROLLING_WINDOW = 20
ENTRY_Z = 2.0
EXIT_Z = 0.5
STOP_Z = 3.0
MOMENTUM_WINDOW = 5


def compute_spread(price_a: pd.Series, price_b: pd.Series, hedge_ratio: float) -> pd.Series:
    return price_a - hedge_ratio * price_b


def compute_zscore(spread: pd.Series, window=ROLLING_WINDOW) -> pd.Series:
    rolling_mean = spread.rolling(window).mean()
    rolling_std = spread.rolling(window).std()
    zscore = (spread - rolling_mean) / rolling_std
    return zscore


def compute_zscore_momentum(zscore: pd.Series, window=MOMENTUM_WINDOW) -> pd.Series:
    """Rate of change of the z-score -- a simple predictive feature that
    flags whether reversion is accelerating or stalling."""
    return zscore.diff(window)


def generate_signals(price_a: pd.Series, price_b: pd.Series, hedge_ratio: float,
                      window=ROLLING_WINDOW, entry_z=ENTRY_Z, exit_z=EXIT_Z, stop_z=STOP_Z):
    """
    Returns a DataFrame with spread, zscore, momentum feature, and a
    `position` column: +1 = long spread, -1 = short spread, 0 = flat.
    """
    spread = compute_spread(price_a, price_b, hedge_ratio)
    zscore = compute_zscore(spread, window)
    momentum = compute_zscore_momentum(zscore)

    df = pd.DataFrame({
        "price_a": price_a,
        "price_b": price_b,
        "spread": spread,
        "zscore": zscore,
        "momentum": momentum,
    })

    position = np.zeros(len(df))
    current_pos = 0

    z = df["zscore"].values
    for i in range(len(df)):
        if np.isnan(z[i]):
            position[i] = 0
            continue

        if current_pos == 0:
            if z[i] > entry_z:
                current_pos = -1  # short the spread
            elif z[i] < -entry_z:
                current_pos = 1   # long the spread
        elif current_pos == 1:
            if z[i] > -exit_z or z[i] < -stop_z:
                current_pos = 0
        elif current_pos == -1:
            if z[i] < exit_z or z[i] > stop_z:
                current_pos = 0

        position[i] = current_pos

    df["position"] = position
    return df
