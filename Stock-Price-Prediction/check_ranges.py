import pandas as pd

df = pd.read_csv('data/aapl_stock_prices.csv')
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values('Date')

ranges = [
    ('2016-2017', '2016-01-01', '2017-12-31'),
    ('2017-2018', '2017-01-01', '2018-12-31'),
    ('2018-2019', '2018-01-01', '2019-12-31'),
    ('2019-2020', '2019-01-01', '2020-12-31'),
    ('2020-2021', '2020-01-01', '2021-12-31'),
    ('2021-2022', '2021-01-01', '2022-12-31'),
    ('2022-2023', '2022-01-01', '2023-12-31'),
    ('2023-2024', '2023-01-01', '2024-12-31'),
    ('2024-2025', '2024-01-01', '2025-12-31'),
    ('2025-2026', '2025-01-01', '2026-12-31'),
]

for name, start, end in ranges:
    subset = df[(df['Date'] >= start) & (df['Date'] <= end)]
    if len(subset) > 0:
        close_min = subset['Close'].min()
        close_max = subset['Close'].max()
        close_range = close_max - close_min
        print(f"{name}: ${close_min:.2f} - ${close_max:.2f} (range=${close_range:.2f}, {len(subset)} rows)")
    else:
        print(f"{name}: No data")
