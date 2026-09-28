import pandas as pd
import numpy as np
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

from skills.base import BacktestConfig
from skills.triple_rsi_mean_reversion import TripleRSI_MeanReversion

print("Fetching full available history for SPY (~25 years)...")
spy = yf.download("SPY", start="2000-01-01", end="2026-01-01", progress=False)

if isinstance(spy.columns, pd.MultiIndex):
    spy.columns = spy.columns.get_level_values(0)

# YFinance returns Date as index, let's normalize to our format
spy.reset_index(inplace=True)
spy.rename(columns={'Date': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
spy.set_index('timestamp', inplace=True)

skill = TripleRSI_MeanReversion()

# 1. Full In-Sample
cfg_in_sample = BacktestConfig(split_ratio=0.0, max_position_pct=0.20) 
res_is = skill.backtest(spy, cfg_in_sample)

# 2. Walk-Forward Out-of-Sample (70/30 split)
cfg_oos = BacktestConfig(split_ratio=0.7, max_position_pct=0.20)
res_oos = skill.backtest(spy, cfg_oos)

print("\n========================================================")
print("   SKILL 1: TripleRSI Mean Reversion (SPY Daily)        ")
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
