import pandas as pd
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

from skills.base import BacktestConfig
from skills.triple_rsi_mean_reversion import TripleRSI_MeanReversion
from skills.bb_rsi_mean_reversion import BB_RSI_MeanReversion
from skills.vwap_mean_reversion import VWAP_MeanReversion

def prep_yf_data(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.reset_index(inplace=True)
    
    time_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
    df.rename(columns={time_col: 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
    
    # Handle timezone and naive datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df.set_index('timestamp', inplace=True)
    
    # Forward fill any NaNs in price data that yfinance sometimes leaves for thinly traded hours
    df = df.ffill().dropna()
    return df.astype(float)

print("Fetching Equities Data...")
spy_1d = yf.download('SPY', period='25y', progress=False)
spy_1d = prep_yf_data(spy_1d)

qqq_1h = yf.download('QQQ', interval='1h', period='720d', progress=False)
qqq_1h = prep_yf_data(qqq_1h)

cfg_is = BacktestConfig(split_ratio=0.0, max_position_pct=0.20)
cfg_oos = BacktestConfig(split_ratio=0.7, max_position_pct=0.20)

def print_results(title, skill, df, is_1h=False):
    res_is = skill.backtest(df, cfg_is)
    res_oos = skill.backtest(df, cfg_oos)
    
    # Correct Sharpe for timeframe
    if is_1h:
        # roughly 1752 trading hours in a year (252 days * 7 hours)
        res_is.sharpe_ratio = (res_is.equity_curve.pct_change().mean() / res_is.equity_curve.pct_change().std()) * (1752**0.5) if len(res_is.equity_curve) > 2 and res_is.equity_curve.pct_change().std() != 0 else 0
        res_oos.sharpe_ratio = (res_oos.equity_curve.pct_change().mean() / res_oos.equity_curve.pct_change().std()) * (1752**0.5) if len(res_oos.equity_curve) > 2 and res_oos.equity_curve.pct_change().std() != 0 else 0
    else:
        res_is.sharpe_ratio = (res_is.equity_curve.pct_change().mean() / res_is.equity_curve.pct_change().std()) * (252**0.5) if len(res_is.equity_curve) > 2 and res_is.equity_curve.pct_change().std() != 0 else 0
        res_oos.sharpe_ratio = (res_oos.equity_curve.pct_change().mean() / res_oos.equity_curve.pct_change().std()) * (252**0.5) if len(res_oos.equity_curve) > 2 and res_oos.equity_curve.pct_change().std() != 0 else 0

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
    print("========================================================\n")

print_results("SKILL 1: TripleRSI Mean Reversion (SPY 1d)", TripleRSI_MeanReversion(), spy_1d)
print_results("SKILL 2: BB+RSI Mean Reversion (SPY 1d)", BB_RSI_MeanReversion(), spy_1d)

skill3 = VWAP_MeanReversion()
# VWAP requires specific 1H data
print_results("SKILL 3: VWAP Mean Reversion (QQQ 1h, ~2 yrs)", skill3, qqq_1h, is_1h=True)

