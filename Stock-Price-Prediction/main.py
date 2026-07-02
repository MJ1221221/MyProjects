import os
import numpy as np
import warnings
warnings.filterwarnings('ignore', category=UserWarning)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from src.data_processing import load_and_preprocess_data
from src.model import build_lstm_model
from sklearn.metrics import root_mean_squared_error

def main():
    data_path = os.path.join('data', 'AAPL.csv')
    
    print("--- Step 1: Processing Multivariate Feature Space ---")
    X_train, y_train, X_test, y_test, target_scaler, test_base_prices = load_and_preprocess_data(data_path)
    
    # Inspect shape to confirm (Window, Features) -> (100, 3)
    print(f"Training Input Shape: {X_train.shape}") 
    
    print("--- Step 2: Building 4-Layer LSTM Model ---")
    model = build_lstm_model(input_shape=(X_train.shape[1], X_train.shape[2]))
    
    print("\n--- Step 3: Training Model (Multivariate Optimization) ---")
    model.fit(X_train, y_train, epochs=20, batch_size=32, validation_split=0.1, verbose=1)
    
    print("\n--- Step 4: Evaluating Short-Horizon Performance ---")
    pred_scaled_diffs = model.predict(X_test, verbose=0)
    
    # Use our isolated target scaler to recover the true daily dollar shifts
    pred_diffs = target_scaler.inverse_transform(pred_scaled_diffs).flatten()
    
    # Cumulative dollar path reconstruction
    predicted_prices = []
    for i in range(len(pred_diffs)):
        prev_actual_price = test_base_prices[i]
        predicted_prices.append(prev_actual_price + pred_diffs[i])
        
    predicted_prices = np.array(predicted_prices)
    actual_targets = test_base_prices[1:len(predicted_prices)+1]
    
    true_rmse = root_mean_squared_error(actual_targets, predicted_prices)
    
    print(f"\n[SUCCESS] Multivariate model verification complete!")
    print(f"True Model Performance Test RMSE: {true_rmse:.2f}")

if __name__ == '__main__':
    main()