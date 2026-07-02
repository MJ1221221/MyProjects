import pandas as pd

trades = pd.read_csv('../output/trades.csv')
pair_pnl = trades.groupby('pair')['pnl'].sum()
bad_pairs_str = set(pair_pnl[pair_pnl < 0].index)  # e.g. {'JNJ-BMY', 'TXN-ON', ...}

pairs = pd.read_csv('../output/selected_pairs.csv')
pairs['pair_str'] = pairs['ticker_a'] + '-' + pairs['ticker_b']

filtered = pairs[~pairs['pair_str'].isin(bad_pairs_str)].drop(columns='pair_str')
filtered.to_csv('../output/selected_pairs.csv', index=False)
print(f"Kept {len(filtered)} pairs, dropped {len(pairs) - len(filtered)}: {bad_pairs_str}")