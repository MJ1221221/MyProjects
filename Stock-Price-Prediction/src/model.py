from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

def build_lstm_model(input_shape):
    model = Sequential()

    model.add(LSTM(units=128, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.1))

    model.add(LSTM(units=100, return_sequences=True))
    model.add(Dropout(0.1))

    model.add(LSTM(units=64, return_sequences=True))
    model.add(Dropout(0.1))

    model.add(LSTM(units=32))
    model.add(Dropout(0.1))

    model.add(Dense(units=1))

    model.compile(optimizer='adam', loss='mean_squared_error')

    return model
