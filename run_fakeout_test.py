import os
import sys
sys.path.append(os.path.dirname(__file__))

import pandas as pd
from run_real_test import fetch_yf_data
from src.core.backtester import Backtester
from src.strategies.session import LondonFakeoutFadeStrategy

def run_fakeout_test():
    # Adding major forex pairs
    assets = ["EURUSD=X", "GBPUSD=X", "JPY=X"]
    bt_fixed = Backtester(initial_capital=10000.0, fee_rate=0.001, slippage_pct=0.0005, risk_per_trade=0.02)
    
    print("\n==================================================")
    print("LONDON FAKEOUT FADE (Judas Swing)")
    print("SL: Fakeout Extreme + 0.25 ATR | TP: Opposite Asian Range")
    print("Holdout Period Applied: Last 180 days excluded")
    print("==================================================")
    
    for asset in assets:
        df_1h = fetch_yf_data(asset, "1h", "700d", exclude_holdout=True)
        if df_1h.empty:
            continue
            
        print(f"\n--- {asset} ---")
        
        strat = LondonFakeoutFadeStrategy(f"FakeoutFade_{asset}", "1.0", {"lookback_n": 3, "atr_buffer": 0.25})
        res = bt_fixed.run(df_1h, strat)["metrics"]
        
        trades = res.get('total_trades', 0)
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
    run_fakeout_test()
