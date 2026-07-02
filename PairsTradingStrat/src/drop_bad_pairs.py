import pandas as pd

pairs = pd.read_csv('../output/selected_pairs.csv')
bad_pairs = {('WMT', 'DG'), ('WMT', 'TJX'), ('TXN', 'AVGO'), ('COP', 'EOG')}

pairs['pair_tuple'] = list(zip(pairs['ticker_a'], pairs['ticker_b']))
filtered = pairs[~pairs['pair_tuple'].isin(bad_pairs)].drop(columns='pair_tuple')
filtered.to_csv('../output/selected_pairs.csv', index=False)
print(f"Kept {len(filtered)} pairs, dropped {len(pairs) - len(filtered)}")