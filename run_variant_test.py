import os
import sys
sys.path.append(os.path.dirname(__file__))

import pandas as pd
from run_real_test import fetch_yf_data
from src.core.backtester import Backtester
from src.strategies.squeeze import FailedBreakoutFadeStrategy

def run_variant_tests():
    assets = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"]
    bt_fixed = Backtester(initial_capital=10000.0, fee_rate=0.001, slippage_pct=0.0005, risk_per_trade=0.02)
    
    print("\n==================================================")
    print("ISOLATING R:R ON FAILED BREAKOUT FADE STRATEGY")
    print("==================================================")
    
    for asset in assets:
        df_1h = fetch_yf_data(asset, "1h", "700d")
        if df_1h.empty:
            continue
            
        print(f"\n--- {asset} ---")
        
        # Variant A: Tighter Stop, SMA Target
        strat_A = FailedBreakoutFadeStrategy(f"Fade_VarA_{asset}", "1.0", {
            "lookback_n": 4, "sl_type": "tight", "tp_type": "sma"
        })
        res_A = bt_fixed.run(df_1h, strat_A)["metrics"]
        
        # Variant B: Extreme Stop, Fixed 1.5:1 Target
        strat_B = FailedBreakoutFadeStrategy(f"Fade_VarB_{asset}", "1.0", {
            "lookback_n": 4, "sl_type": "extreme", "tp_type": "fixed_rr", "rr_ratio": 1.5
        })
        res_B = bt_fixed.run(df_1h, strat_B)["metrics"]
        
        # Variant C: Tight Stop, Fixed 1.5:1 Target
        strat_C = FailedBreakoutFadeStrategy(f"Fade_VarC_{asset}", "1.0", {
            "lookback_n": 4, "sl_type": "tight", "tp_type": "fixed_rr", "rr_ratio": 1.5
        })
        res_C = bt_fixed.run(df_1h, strat_C)["metrics"]
        
        print(f"[VARIANT A (Tight SL + SMA Target)]")
        print(f"Trades: {res_A.get('total_trades', 0)} | Win Rate: {res_A.get('win_rate', 0)*100:.2f}% | PF: {res_A.get('profit_factor', 0):.2f}")
        
        print(f"[VARIANT B (Extreme SL + Fixed 1.5 R:R)]")
        print(f"Trades: {res_B.get('total_trades', 0)} | Win Rate: {res_B.get('win_rate', 0)*100:.2f}% | PF: {res_B.get('profit_factor', 0):.2f}")
        
        print(f"[VARIANT C (Tight SL + Fixed 1.5 R:R)]")
        print(f"Trades: {res_C.get('total_trades', 0)} | Win Rate: {res_C.get('win_rate', 0)*100:.2f}% | PF: {res_C.get('profit_factor', 0):.2f}")
        
if __name__ == "__main__":
    run_variant_tests()
