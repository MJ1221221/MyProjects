"""
data_pipeline.py
-----------------
Engineers a quantitative trading pipeline using the yFinance API and 5 years
of historical data for signal generation.

Downloads daily adjusted-close prices for a universe of sector-grouped,
liquid equities and caches them locally as CSV/parquet so downstream
steps (pair selection, signal generation, backtesting) don't need to
re-hit the API every run.
"""

import os
import time
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Universe: grouped by sector because cointegration is far more likely to
# hold (and persist) between companies exposed to similar fundamentals.
# ---------------------------------------------------------------------------
UNIVERSE = {
    "Financials": ["JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "COF"],
    "Energy":     ["XOM", "CVX", "COP", "SLB", "EOG", "PSX", "VLO", "MPC", "OXY", "HES"],
    "Tech":       ["AAPL", "MSFT", "NVDA", "AMD", "INTC", "QCOM", "TXN", "AVGO", "MU", "ADI"],
    "Retail":     ["WMT", "TGT", "COST", "HD", "LOW", "TJX", "ROST", "KR", "DG", "BBY"],
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
YEARS_OF_HISTORY = 5


def fetch_price_history(tickers, period_years=YEARS_OF_HISTORY):
    """
    Pulls daily OHLCV data for a list of tickers via yfinance and returns
    a dict of {ticker: DataFrame}. Adjusted close is used throughout to
    account for splits/dividends.
    """
    all_data = {}
    period_str = f"{period_years}y"

    for ticker in tickers:
        try:
            df = yf.download(
                ticker,
                period=period_str,
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
            if df.empty or len(df) < 252 * 2:  # need reasonable history
                print(f"  [skip] {ticker}: insufficient data")
                continue
            df = df[["Close", "Volume"]].copy()
            df.columns = ["close", "volume"]
            all_data[ticker] = df
            print(f"  [ok]   {ticker}: {len(df)} rows")
        except Exception as e:
            print(f"  [fail] {ticker}: {e}")
        time.sleep(0.3)  # be polite to the API

    return all_data


def save_to_disk(all_data, out_dir=DATA_DIR):
    os.makedirs(out_dir, exist_ok=True)
    for ticker, df in all_data.items():
        df.to_csv(os.path.join(out_dir, f"{ticker}.csv"))
    print(f"\nSaved {len(all_data)} tickers to {out_dir}")


def load_from_disk(tickers, data_dir=DATA_DIR):
    """Loads cached price data from disk instead of re-hitting the API."""
    all_data = {}
    for ticker in tickers:
        path = os.path.join(data_dir, f"{ticker}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            all_data[ticker] = df
    return all_data


def build_close_price_matrix(all_data):
    """Combines individual ticker DataFrames into a single close-price matrix."""
    closes = {ticker: df["close"] for ticker, df in all_data.items()}
    matrix = pd.DataFrame(closes)
    matrix = matrix.dropna(axis=1, thresh=int(len(matrix) * 0.95))  # drop sparse tickers
    matrix = matrix.ffill().dropna()
    return matrix


def main():
    all_tickers = [t for group in UNIVERSE.values() for t in group]
    print(f"Fetching {YEARS_OF_HISTORY}y of daily data for {len(all_tickers)} tickers via yFinance...\n")

    all_data = fetch_price_history(all_tickers)
    save_to_disk(all_data)

    price_matrix = build_close_price_matrix(all_data)
    price_matrix.to_csv(os.path.join(DATA_DIR, "price_matrix.csv"))
    print(f"\nPrice matrix shape: {price_matrix.shape}")
    print(f"Saved combined matrix to {os.path.join(DATA_DIR, 'price_matrix.csv')}")


if __name__ == "__main__":
    main()
