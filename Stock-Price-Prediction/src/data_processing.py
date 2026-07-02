import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

def load_and_preprocess_data(filepath, window_size=100, train_split=0.8):
    df = pd.read_csv(filepath)
    
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
    
    if df['Close/Last'].dtype == 'object':
        df['Close/Last'] = df['Close/Last'].astype(str).str.replace('$', '').str.strip()
    df['Close/Last'] = df['Close/Last'].astype(float)
    
    # Filter for the modern timeline to ensure range consistency
    df = df[df['Date'] >= '2022-01-01'].reset_index(drop=True)
    data = df['Close/Last'].values.reshape(-1, 1)
    
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)
    
    X, y = [], []
    for i in range(window_size, len(scaled_data)):
        X.append(scaled_data[i-window_size:i, 0])
        y.append(scaled_data[i, 0])
        
    X, y = np.array(X), np.array(y)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))
    
    # Clean chronological time series split (80% train, 20% test)
    split_idx = int(len(X) * train_split)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    return X_train, y_train, X_test, y_test, scaler