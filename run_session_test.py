import os
import sys
sys.path.append(os.path.dirname(__file__))

import pandas as pd
from run_real_test import fetch_yf_data
from src.core.backtester import Backtester
from src.strategies.session import SessionOpenMomentumStrategy

def run_session_test():
    assets = ["EURUSD=X", "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"]
    bt_fixed = Backtester(initial_capital=10000.0, fee_rate=0.001, slippage_pct=0.0005, risk_per_trade=0.02)
    
    print("\n==================================================")
    print("SESSION OPEN MOMENTUM (Asian Range Breakout)")
    print("SL: Opposite Asian Range | TP: 1.5 R:R")
    print("==================================================")
    
    for asset in assets:
        # Load from cache (will not hit yfinance since 700d data is cached)
        df_1h = fetch_yf_data(asset, "1h", "700d")
        if df_1h.empty:
            continue
            
        print(f"\n--- {asset} ---")
        
        strat = SessionOpenMomentumStrategy(f"SessionMom_{asset}", "1.0", {"rr_ratio": 1.5})
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
    run_session_test()
