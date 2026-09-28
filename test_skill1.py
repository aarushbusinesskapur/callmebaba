import pandas as pd
import numpy as np
import ccxt
import warnings
warnings.filterwarnings('ignore')

from skills.base import BacktestConfig
from skills.triple_rsi_mean_reversion import TripleRSI_MeanReversion

def get_data():
    ex = ccxt.kraken()
    ohlcv = ex.fetch_ohlcv('BTC/USD', '1d', limit=1000)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

df = get_data()
skill = TripleRSI_MeanReversion()

cfg = BacktestConfig(split_ratio=0.7)
res = skill.backtest(df, cfg)

print(f"=== BACKTEST RESULTS (Walk-Forward Out-Of-Sample) ===")
print(f"Total Trades: {res.total_trades}")
print(f"Win Rate:     {res.win_rate:.2%}")
print(f"Profit Factor:{res.profit_factor:.2f}")
print(f"Expectancy:   {res.expectancy:.2f}R")
print(f"Max DD:       {res.max_drawdown:.2%}")
print(f"Sharpe Ratio: {res.sharpe_ratio:.2f}")
print(f"Avg R:        {res.avg_r:.2f}R")

# Find a subset of data that triggers a signal for the sample output
df_prep = skill._prep_data(df)
for i in range(200, len(df_prep)):
    last = df_prep.iloc[i]
    if (last['close'] > last['sma_200']) and (last['rsi_14'] < 40) and (last['rsi_7'] < 30) and (last['rsi_2'] < 10):
        sig = skill.generate_signal(df.iloc[:i+1])
        print("\n=== SAMPLE SIGNAL OUTPUT ===")
        print(f"Date: {df.index[i]}")
        print(f"Signal: {sig.signal} (Confidence: {sig.confidence:.1f}/100)")
        print(f"Reason: {sig.reason}")
        print(f"Stop Price: ")
        break
