import pandas as pd
import urllib.request
import io
import warnings
import numpy as np
warnings.filterwarnings('ignore')

from skills.base import BacktestConfig
from skills.high_probability_confluence import HighProbability_Confluence

API_KEY = "7873877dad9f4f7fb1750fa5ef5eaa86"

def get_twelvedata(symbol, interval, outputsize=5000):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={API_KEY}&outputsize={outputsize}&format=csv"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req)
    df = pd.read_csv(io.StringIO(res.read().decode('utf-8')), sep=';')
    df.rename(columns={'datetime': 'timestamp'}, inplace=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df.sort_index().astype(float)

spy_1d = get_twelvedata('SPY', '1day')

cfg_is = BacktestConfig(split_ratio=0.0, max_position_pct=0.20)
cfg_oos = BacktestConfig(split_ratio=0.7, max_position_pct=0.20)

skill5 = HighProbability_Confluence()

res_is = skill5.backtest(spy_1d, cfg_is)
res_oos = skill5.backtest(spy_1d, cfg_oos)

def sharpe(curve):
    if len(curve) > 2 and curve.pct_change().std() != 0:
        return (curve.pct_change().mean() / curve.pct_change().std()) * np.sqrt(252)
    return 0.0

print(f"\n========================================================")
print(f"   SKILL 5: Confluence >= 70 (SPY 1d, 5000d)")
print("========================================================")
print(f"{'Metric':<18} | {'100% In-Sample':<16} | {'30% Out-Of-Sample':<16}")
print("-" * 56)
print(f"{'Total Trades':<18} | {res_is.total_trades:<16} | {res_oos.total_trades:<16}")
print(f"{'Win Rate':<18} | {res_is.win_rate:.2%}".ljust(21) + f" | {res_oos.win_rate:.2%}")
print(f"{'Profit Factor':<18} | {res_is.profit_factor:.2f}".ljust(21) + f" | {res_oos.profit_factor:.2f}")
print(f"{'Expectancy':<18} | {res_is.expectancy:.2f}R".ljust(21) + f" | {res_oos.expectancy:.2f}R")
print(f"{'Max Drawdown':<18} | {res_is.max_drawdown:.2%}".ljust(21) + f" | {res_oos.max_drawdown:.2%}")
print(f"{'Sharpe Ratio':<18} | {sharpe(res_is.equity_curve):.2f}".ljust(21) + f" | {sharpe(res_oos.equity_curve):.2f}")
print(f"{'Avg R':<18} | {res_is.avg_r:.2f}R".ljust(21) + f" | {res_oos.avg_r:.2f}R")
print("========================================================")
