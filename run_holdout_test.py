import os
import sys
sys.path.append(os.path.dirname(__file__))

from run_real_test import fetch_yf_data_holdout
from src.core.backtester import Backtester
from src.strategies.trend import TrendFollowingStrategy

def run_holdout_test():
    asset = "GBPUSD=X"
    
    print("\n==================================================")
    print("FINAL HOLDOUT OOS TEST: GBP/USD NAIVE CROSSOVER")
    print("Testing strictly on the unseen 180-day out-of-sample data")
    print("==================================================")
    
    df_holdout = fetch_yf_data_holdout(asset, "1h", "700d")
    if df_holdout.empty:
        return
        
    bt = Backtester(initial_capital=10000.0, asset=asset, risk_per_trade=0.02)
    strat = TrendFollowingStrategy(f"NaiveCrossover_{asset}_OOS", "1.0", {})
    
    res = bt.run(df_holdout, strat)["metrics"]
    
    trades = res.get('total_trades', 0)
    print(f"\n--- Strategy: Naive Crossover (Holdout) ---")
    print(f"Trades:        {trades}")
    
    if trades > 0:
        print(f"Win Rate:      {res.get('win_rate', 0)*100:.2f}%")
        print(f"Profit Factor: {res.get('profit_factor', 0):.2f}")
        print(f"Max Drawdown:  ${res.get('max_drawdown', 0):.2f}")
        print(f"Total PnL:     ${res.get('total_pnl', 0):.2f}")
        print(f"Expectancy:    ${res.get('expectancy', 0):.2f}")
        
        if res.get('profit_factor', 0) > 1.2:
            print(f"Status:        HOLDOUT PASSED (True Edge Confirmed)")
        else:
            print(f"Status:        HOLDOUT FAILED (False Positive / Overfit)")
    else:
        print("Status:        INCONCLUSIVE (0 Trades)")

if __name__ == "__main__":
    run_holdout_test()
