import pandas as pd
import ccxt
from skills.base import BacktestConfig
from skills.bb_rsi_mean_reversion import BB_RSI_MeanReversion
import warnings
warnings.filterwarnings('ignore')

def get_crypto(symbol):
    ex = ccxt.kraken()
    since = ex.parse8601('2020-01-01T00:00:00Z')
    all_ohlcv = []
    try:
        while since < ex.milliseconds():
            ohlcv = ex.fetch_ohlcv(symbol, '1d', since=since, limit=720)
            if not ohlcv: break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 86400000
    except:
        pass
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df[~df['timestamp'].duplicated(keep='first')]
    df.set_index('timestamp', inplace=True)
    return df

skill = BB_RSI_MeanReversion()
symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'LINK/USD', 'DOGE/USD']

print(f"{'Asset':<10} | {'Trades':<8} | {'Win Rate':<10} | {'Profit Factor':<14} | {'Expectancy'}")
print("-" * 65)

for sym in symbols:
    df = get_crypto(sym)
    if len(df) < 200: continue
    
    cfg = BacktestConfig(split_ratio=0.0, max_position_pct=0.20)
    res = skill.backtest(df, cfg)
    
    wr_str = f"{res.win_rate:.2%}"
    pf_str = f"{res.profit_factor:.2f}"
    exp_str = f"{res.expectancy:.2f}R"
    print(f"{sym:<10} | {res.total_trades:<8} | {wr_str:<10} | {pf_str:<14} | {exp_str}")
