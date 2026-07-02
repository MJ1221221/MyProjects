import pandas as pd

trades = pd.read_csv('../output/trades.csv')

per_pair = trades.groupby('pair').agg(
    n_trades=('pnl', 'count'),
    win_rate=('win', 'mean'),
    total_pnl=('pnl', 'sum'),
    avg_pnl=('pnl', 'mean'),
).sort_values('total_pnl')

print(per_pair.to_string())
print()
print("Worst 5 pairs (dragging performance):")
print(per_pair.head(5).index.tolist())
print()
print("Best 5 pairs:")
print(per_pair.tail(5).index.tolist())