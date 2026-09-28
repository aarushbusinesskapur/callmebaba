import pandas as pd
import urllib.request
import io
import warnings
import numpy as np
warnings.filterwarnings('ignore')

from skills.base import BacktestConfig
from skills.triple_rsi_mean_reversion import TripleRSI_MeanReversion
from skills.bb_rsi_mean_reversion import BB_RSI_MeanReversion
from skills.vwap_mean_reversion import VWAP_MeanReversion
from skills.opening_range_breakout_pro import OpeningRangeBreakout_Pro

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
qqq_1h = get_twelvedata('QQQ', '1h')
qqq_15m = get_twelvedata('QQQ', '15min')

cfg_is = BacktestConfig(split_ratio=0.0, max_position_pct=0.20)
cfg_oos = BacktestConfig(split_ratio=0.7, max_position_pct=0.20)

def print_results(title, skill, df, bars_per_year):
    res_is = skill.backtest(df, cfg_is)
    res_oos = skill.backtest(df, cfg_oos)
    
    if len(res_is.equity_curve) > 2 and res_is.equity_curve.pct_change().std() != 0:
        res_is.sharpe_ratio = (res_is.equity_curve.pct_change().mean() / res_is.equity_curve.pct_change().std()) * np.sqrt(bars_per_year)
    if len(res_oos.equity_curve) > 2 and res_oos.equity_curve.pct_change().std() != 0:
        res_oos.sharpe_ratio = (res_oos.equity_curve.pct_change().mean() / res_oos.equity_curve.pct_change().std()) * np.sqrt(bars_per_year)
        
    print(f"\n========================================================")
    print(f"   {title}")
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

print_results("SKILL 1: TripleRSI Mean Reversion (SPY 1d, 5000d)", TripleRSI_MeanReversion(), spy_1d, 252)
print_results("SKILL 2: BB+RSI Mean Reversion (SPY 1d, 5000d)", BB_RSI_MeanReversion(), spy_1d, 252)
print_results("SKILL 3: VWAP Mean Reversion (QQQ 1h, 5000h)", VWAP_MeanReversion(), qqq_1h, 1764)

# ORB Pro needs 15m or 30m intraday data
print_results("SKILL 4: ORB Pro (QQQ 15m, 5000 bars)", OpeningRangeBreakout_Pro(market_open_time="09:30"), qqq_15m, 6720)

