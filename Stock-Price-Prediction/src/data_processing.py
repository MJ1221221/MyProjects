import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

def load_and_preprocess_data(filepath, window_size=100, train_split=0.8):
    df = pd.read_csv(filepath)
    
    # Standard chronological sorting
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        
    # Clean Kaggle markdown/whitespace headers
    df.columns = df.columns.str.replace('#', '').str.strip()
    
    # Modern filter (2021 onwards)
    df = df[df['Date'] >= '2021-01-01'].reset_index(drop=True)
    
    # --- Feature Engineering ---
    # 1. Target Signal: Daily Price Changes
    raw_prices = df['Close'].astype(float).values
    price_diffs = np.diff(raw_prices).reshape(-1, 1)
    
    # 2. Volatility Signal: High minus Low (aligned to match the diff length)
    daily_range = (df['High'].astype(float) - df['Low'].astype(float)).values[1:].reshape(-1, 1)
    
    # 3. Volume Signal: Market activity momentum
    volume = df['Volume'].astype(float).values[1:].reshape(-1, 1)
    
    # --- Dual Scaler Strategy ---
    target_scaler = MinMaxScaler(feature_range=(-1, 1))
    feature_scaler = MinMaxScaler(feature_range=(0, 1))
    
    scaled_targets = target_scaler.fit_transform(price_diffs)
    scaled_ranges = feature_scaler.fit_transform(daily_range)
    scaled_volumes = feature_scaler.fit_transform(volume)
    
    # Merge into a single 3-dimensional multi-feature array
    # Column 0: Close Diff, Column 1: Daily Range, Column 2: Volume
    dataset = np.hstack((scaled_targets, scaled_ranges, scaled_volumes))
    
    X, y = [], []
    for i in range(window_size, len(dataset)):
        # Lookback window takes all 3 features
        X.append(dataset[i-window_size:i, :])
        # Target layer only predicts the next Close Price Diff (Column 0)
        y.append(dataset[i, 0])
        
    X, y = np.array(X), np.array(y)
    
    # Chronological time series boundary split
    split_idx = int(len(X) * train_split)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # Basis tracker to reconstruct absolute dollar prices at runtime
    test_base_prices = raw_prices[window_size + split_idx:]
    
    return X_train, y_train, X_test, y_test, target_scaler, test_base_prices