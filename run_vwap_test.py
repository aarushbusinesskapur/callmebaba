import os
import sys
import pandas as pd
sys.path.append(os.path.dirname(__file__))

from src.core.backtester import Backtester
from src.strategies.vwap import DailyVWAPContinuationStrategy

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")

def run_vwap_test():
    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    
    print("\n==================================================")
    print("DAILY VWAP TREND CONTINUATION (BINANCE SPOT BASE VOLUME)")
    print("VWAP Anchor: Daily (00:00 UTC)")
    print("Entry: Breakout beyond 2 Volume-Weighted Std Dev")
    print("Exit: ATR Trailing Stop (2.0x)")
    print("Holdout Period Applied: Last 180 days excluded")
    print("Risk Mode: FIXED R-MULTIPLE (Full Sample Tracking)")
    print("==================================================")
    
    for asset in assets:
        print(f"\n##################################################")
        print(f"ASSET: {asset}")
        print(f"##################################################")
        
        cache_file = os.path.join(CACHE_DIR, f"{asset}_spot_1h_700d.csv")
        if not os.path.exists(cache_file):
            print(f"Error: Missing spot cache for {asset}")
            continue
            
        df = pd.read_csv(cache_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        # Enforce Holdout
        max_date = df['timestamp'].max()
        cutoff_date = max_date - pd.Timedelta(days=180)
        df_train = df[df['timestamp'] < cutoff_date].copy().reset_index(drop=True)
        
        print(f"Training data: {df_train['timestamp'].min().date()} to {df_train['timestamp'].max().date()}")
        
        # Spot fees (using Crypto default 0.1% taker + 0.05% slippage, since it's Spot, not Futures)
        bt = Backtester(initial_capital=10000.0, asset=asset, risk_per_trade=0.02)
        bt.fixed_risk = True # DO NOT COMPOUND. Size purely off the $10,000 base for the whole test.
        bt.fee_rate = 0.001
        bt.slippage_pct = 0.0005
        bt.is_futures = False
        
        strat = DailyVWAPContinuationStrategy(f"VWAP_Cont_{asset}", "1.0", {
            "std_multiplier": 2.0,
            "sl_atr_buffer": 0.5,
            "trailing_atr_multiplier": 2.0
        })
        
        res = bt.run(df_train, strat)["metrics"]
        
        trades = res.get('total_trades', 0)
        print(f"\n--- Strategy: VWAP Deviation Fade (2 StdDev) ---")
        print(f"Trades:        {trades}")
        
        if trades > 0:
            print(f"Win Rate:      {res.get('win_rate', 0)*100:.2f}%")
            print(f"Profit Factor: {res.get('profit_factor', 0):.2f}")
            print(f"Max Drawdown:  ${res.get('max_drawdown', 0):.2f}")
            print(f"Total PnL:     ${res.get('total_pnl', 0):.2f}")
            print(f"Expectancy:    ${res.get('expectancy', 0):.2f}")
            
            if trades < 30:
                print(f"Status:        INCONCLUSIVE (<30 trades)")
            elif res.get('profit_factor', 0) > 1.2:
                print(f"Status:        PROMOTED")
            else:
                print(f"Status:        REJECTED (Profit Factor < 1.2)")

if __name__ == "__main__":
    run_vwap_test()
