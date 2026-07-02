from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

def build_lstm_model(input_shape):
    model = Sequential()
    
    # Layer 1 LSTM - Lower dropout for tighter curve tracking
    model.add(LSTM(units=50, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.05))
    
    # Layer 2 LSTM
    model.add(LSTM(units=50, return_sequences=True))
    model.add(Dropout(0.05))
    
    # Layer 3 LSTM
    model.add(LSTM(units=50, return_sequences=True))
    model.add(Dropout(0.05))
    
    # Layer 4 LSTM
    model.add(LSTM(units=50))
    model.add(Dropout(0.05))
    
    # Output Layer
    model.add(Dense(units=1))
    
    # Compile with Adam optimization
    model.compile(optimizer='adam', loss='mean_squared_error')
    
    return model