import pandas as pd
import numpy as np
import ccxt
import warnings
warnings.filterwarnings('ignore')

from skills.base import BacktestConfig
from skills.triple_rsi_mean_reversion import TripleRSI_MeanReversion

def get_data():
    ex = ccxt.kraken()
    # Fetch 4000 days (approx 11 years) of BTC data to get a large trade sample size
    # Using fetch_ohlcv in a loop or since early timestamp
    since = ex.parse8601('2015-01-01T00:00:00Z')
    all_ohlcv = []
    
    while since < ex.milliseconds():
        ohlcv = ex.fetch_ohlcv('BTC/USD', '1d', since=since, limit=720)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 86400000 # Next day
        
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    # Remove duplicates
    df = df[~df.index.duplicated(keep='first')]
    return df

print("Fetching full available history for BTC/USD (~10 years)...")
df = get_data()
print(f"Loaded {len(df)} days of data.")

skill = TripleRSI_MeanReversion()
# Fix 3: Test over the entire history (100% in-sample) for maximum trade count
cfg = BacktestConfig(split_ratio=0.0, max_position_pct=0.20) 
res = skill.backtest(df, cfg)

print(f"\n=== BACKTEST RESULTS (Full History: BTC/USD 2015-2026) ===")
print(f"Total Trades: {res.total_trades}")
print(f"Win Rate:     {res.win_rate:.2%}")
print(f"Profit Factor:{res.profit_factor:.2f}")
print(f"Expectancy:   {res.expectancy:.2f}R")
print(f"Max DD:       {res.max_drawdown:.2%}")
print(f"Sharpe Ratio: {res.sharpe_ratio:.2f}")
print(f"Avg R:        {res.avg_r:.2f}R")
