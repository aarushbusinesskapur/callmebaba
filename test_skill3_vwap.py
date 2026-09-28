import pandas as pd
import ccxt
import warnings
warnings.filterwarnings('ignore')

from skills.base import BacktestConfig
from skills.vwap_mean_reversion import VWAP_MeanReversion

def get_crypto_1h(symbol):
    ex = ccxt.binance()
    since = ex.parse8601('2022-01-01T00:00:00Z') # Binance has deep history
    all_ohlcv = []
    try:
        while since < ex.milliseconds():
            ohlcv = ex.fetch_ohlcv(symbol, '1h', since=since, limit=1000)
            if not ohlcv: break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 3600000
    except Exception as e:
        print("Binance fetch error:", e)
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df[~df['timestamp'].duplicated(keep='first')]
    df.set_index('timestamp', inplace=True)
    df = df.astype(float)
    return df

print("Fetching full available history (1H) for BTC/USDT from Binance...")
btc = get_crypto_1h('BTC/USDT')
print(f"Fetched {len(btc)} rows.")

skill = VWAP_MeanReversion()

cfg_is = BacktestConfig(split_ratio=0.0, max_position_pct=0.20) 
res_is = skill.backtest(btc, cfg_is)

cfg_oos = BacktestConfig(split_ratio=0.7, max_position_pct=0.20)
res_oos = skill.backtest(btc, cfg_oos)

print("\n========================================================")
print("   SKILL 3: VWAP Mean Reversion (1H CRYPTO PROXY)       ")
print("========================================================")
print("   CAVEAT: This is a CRYPTO PROXY standing in for       ")
print("   the equities intraday use case, not a validation.    ")
print("========================================================")
print(f"{'Metric':<18} | {'100% In-Sample':<16} | {'30% Out-Of-Sample':<16}")
print("-" * 56)
print(f"{'Total Trades':<18} | {res_is.total_trades:<16} | {res_oos.total_trades:<16}")
print(f"{'Win Rate':<18} | {res_is.win_rate:.2%}".ljust(21) + f" | {res_oos.win_rate:.2%}")
print(f"{'Profit Factor':<18} | {res_is.profit_factor:.2f}".ljust(21) + f" | {res_oos.profit_factor:.2f}")
print(f"{'Expectancy':<18} | {res_is.expectancy:.2f}R".ljust(21) + f" | {res_oos.expectancy:.2f}R")
print(f"{'Max Drawdown':<18} | {res_is.max_drawdown:.2%}".ljust(21) + f" | {res_oos.max_drawdown:.2%}")
print(f"{'Sharpe Ratio':<18} | {res_is.sharpe_ratio:.2f}".ljust(21) + f" | {res_oos.sharpe_ratio:.2f}")
print(f"{'Avg R':<18} | {res_is.avg_r:.2f}R".ljust(21) + f" | {res_oos.avg_r:.2f}R")
print("========================================================")

if res_oos.total_trades < 30:
    print("   FLAG: OOS Sample too thin (<30) to draw conclusions! ")

