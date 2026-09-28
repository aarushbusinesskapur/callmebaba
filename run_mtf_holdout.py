import os
import sys
import pandas as pd
sys.path.append(os.path.dirname(__file__))

from src.core.backtester import Backtester
from src.strategies.mtf import MTFSqueezeStrategy

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")

def run_mtf_holdout():
    asset = "SOLUSDT"
    
    print("\n==================================================")
    print("OOS HOLDOUT VALIDATION (180 DAYS)")
    print(f"Asset: {asset}")
    print("Strategy: MTF 1H Squeeze / 4H Trend")
    print("Risk Mode: FIXED R-MULTIPLE")
    print("==================================================")
    
    cache_file = os.path.join(CACHE_DIR, f"{asset}_spot_1h_700d.csv")
    if not os.path.exists(cache_file):
        print(f"Error: Missing spot cache for {asset}")
        return
        
    df = pd.read_csv(cache_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    
    # Enforce Holdout
    max_date = df['timestamp'].max()
    cutoff_date = max_date - pd.Timedelta(days=180)
    
    # We must pass the entire DF to the strategy first so the 200-SMA can calculate correctly!
    # If we only pass the last 180 days, the 200-period MA will be NaN for the first 200 bars of the holdout!
    
    strat = MTFSqueezeStrategy(f"MTF_{asset}", "1.0", {})
    signals = strat.generate_signals(df)
    
    # Now filter the signals DataFrame to strictly the 180-day holdout period
    signals_test = signals[signals['timestamp'] >= cutoff_date].copy().reset_index(drop=True)
    
    print(f"Holdout data: {signals_test['timestamp'].min().date()} to {signals_test['timestamp'].max().date()}")
    
    bt = Backtester(initial_capital=10000.0, asset=asset, risk_per_trade=0.02)
    bt.fixed_risk = True
    bt.fee_rate = 0.001
    bt.slippage_pct = 0.0005
    bt.is_futures = False
    
    # Run backtester on the pre-generated subset
    # Wait, bt.run expects the dataframe and calls generate_signals.
    # To bypass this, we can monkey-patch or just pass df to bt.run but tell it to ignore entries before cutoff?
    # Better: modify strat.generate_signals to return the signals_test subset.
    class HoldoutStrategy(MTFSqueezeStrategy):
        def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
            # Call parent
            res = super().generate_signals(df)
            return res[res['timestamp'] >= cutoff_date].copy().reset_index(drop=True)
            
    strat_holdout = HoldoutStrategy(f"MTF_{asset}", "1.0", {})
    
    res = bt.run(df, strat_holdout)["metrics"]
    
    trades = res.get('total_trades', 0)
    print(f"\n--- Strategy: MTF 1H Squeeze / 4H Trend ({asset}) [HOLDOUT] ---")
    print(f"Trades:        {trades}")
    
    if trades > 0:
        print(f"Win Rate:      {res.get('win_rate', 0)*100:.2f}%")
        print(f"Profit Factor: {res.get('profit_factor', 0):.2f}")
        print(f"Max Drawdown:  ${res.get('max_drawdown', 0):.2f}")
        print(f"Total PnL:     ${res.get('total_pnl', 0):.2f}")
        print(f"Expectancy:    ${res.get('expectancy', 0):.2f}")

if __name__ == "__main__":
    run_mtf_holdout()
