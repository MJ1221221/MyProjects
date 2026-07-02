import pandas as pd

trades = pd.read_csv('../output/trades.csv')
wins = trades[trades['win']]
losses = trades[~trades['win']]

print('n wins:', len(wins), 'n losses:', len(losses))
print('avg win:', wins['pnl'].mean())
print('avg loss:', losses['pnl'].mean())
print('total win $:', wins['pnl'].sum())
print('total loss $:', losses['pnl'].sum())
print('biggest loss:', trades['pnl'].min())
print('biggest win:', trades['pnl'].max())