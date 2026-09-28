import pandas as pd
import numpy as np
import warnings
import urllib.request
from io import StringIO
warnings.filterwarnings('ignore')

from skills.base import BacktestConfig
from skills.bb_rsi_mean_reversion import BB_RSI_MeanReversion

print("Fetching AAPL daily equities data from public repo...")
url = 'https://raw.githubusercontent.com/plotly/datasets/master/finance-charts-apple.csv'
response = urllib.request.urlopen(url)
csv_data = response.read().decode('utf-8')
aapl = pd.read_csv(StringIO(csv_data))

aapl.rename(columns={'Date': 'timestamp', 'AAPL.Open': 'open', 'AAPL.High': 'high', 'AAPL.Low': 'low', 'AAPL.Close': 'close', 'AAPL.Volume': 'volume'}, inplace=True)
aapl['timestamp'] = pd.to_datetime(aapl['timestamp'])
aapl.set_index('timestamp', inplace=True)

skill = BB_RSI_MeanReversion()

cfg_is = BacktestConfig(split_ratio=0.0, max_position_pct=0.20) 
res_is = skill.backtest(aapl, cfg_is)

cfg_oos = BacktestConfig(split_ratio=0.7, max_position_pct=0.20)
res_oos = skill.backtest(aapl, cfg_oos)

print("\n========================================================")
print("   SKILL 2: BB+RSI Mean Reversion (AAPL Daily)          ")
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
