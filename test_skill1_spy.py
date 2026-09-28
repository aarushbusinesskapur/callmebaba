import pandas as pd
import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import yfinance as yf
except ImportError:
    install('yfinance')
    import yfinance as yf

from skills.base import BacktestConfig
from skills.triple_rsi_mean_reversion import TripleRSI_MeanReversion

print("Fetching full available history for SPY...")
spy = yf.download("SPY", start="2000-01-01", end="2026-01-01", progress=False)
spy.reset_index(inplace=True)
spy.rename(columns={'Date': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
if isinstance(spy.columns, pd.MultiIndex):
    spy.columns = spy.columns.get_level_values(0)

# Set index
spy.set_index('timestamp', inplace=True)

skill = TripleRSI_MeanReversion()
# Test over the entire history 100% in sample just for metric demonstration of long history
cfg = BacktestConfig(split_ratio=0.0, max_position_pct=0.20) 
res = skill.backtest(spy, cfg)

print(f"\n=== BACKTEST RESULTS (Full History: SPY 2000-2026) ===")
print(f"Total Trades: {res.total_trades}")
print(f"Win Rate:     {res.win_rate:.2%}")
print(f"Profit Factor:{res.profit_factor:.2f}")
print(f"Expectancy:   {res.expectancy:.2f}R")
print(f"Max DD:       {res.max_drawdown:.2%}")
print(f"Sharpe Ratio: {res.sharpe_ratio:.2f}")
print(f"Avg R:        {res.avg_r:.2f}R")
