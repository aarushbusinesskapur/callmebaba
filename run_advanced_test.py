import os
import sys
sys.path.append(os.path.dirname(__file__))

import pandas as pd
from run_real_test import fetch_yf_data
from src.core.backtester import Backtester
from src.strategies.squeeze import VolatilitySqueezeStrategy, FailedBreakoutFadeStrategy

def run_advanced_tests():
    assets = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "EURUSD=X"]
    
    bt_fixed = Backtester(initial_capital=10000.0, fee_rate=0.001, slippage_pct=0.0005, risk_per_trade=0.02)
    
    # --- TEST 1: 4H VOLATILITY SQUEEZE BREAKOUT ---
    print("\n==================================================")
    print("TEST 1: 4H VOLATILITY SQUEEZE (Trend Continuation)")
    print("==================================================")
    for asset in assets:
        df_1h = fetch_yf_data(asset, "1h", "700d")
        if df_1h.empty:
            continue
            
        # Resample to 4H
        df_1h.set_index('timestamp', inplace=True)
        df_4h = df_1h.resample('4h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        df_4h.reset_index(inplace=True)
        
        strat = VolatilitySqueezeStrategy(f"Squeeze4H_{asset}", "1.0", {})
        res = bt_fixed.run(df_4h, strat)["metrics"]
        
        print(f"\n--- {asset} (4H) ---")
        print(f"Trades:        {res.get('total_trades', 0)}")
        if res.get('total_trades', 0) > 0:
            print(f"Win Rate:      {res.get('win_rate', 0)*100:.2f}%")
            print(f"Profit Factor: {res.get('profit_factor', 0)}")
            print(f"Max Drawdown:  ${res.get('max_drawdown', 0):.2f}")
            print(f"Expectancy:    ${res.get('expectancy', 0):.2f}")
            if res.get('total_trades', 0) < 30:
                print(f"Status:        INCONCLUSIVE (<30 trades)")
            else:
                print(f"Status:        PROMOTED" if res.get('profit_factor', 0) > 1.0 else "Status:        REJECTED")

    # --- TEST 2: 1H FAILED BREAKOUT FADE ---
    print("\n==================================================")
    print("TEST 2: 1H FAILED BREAKOUT FADE (Mean Reversion)")
    print("==================================================")
    for asset in assets:
        df_1h = fetch_yf_data(asset, "1h", "700d")
        if df_1h.empty:
            continue
            
        strat_fade = FailedBreakoutFadeStrategy(f"Fade1H_{asset}", "1.0", {"lookback_n": 4})
        res = bt_fixed.run(df_1h, strat_fade)["metrics"]
        
        print(f"\n--- {asset} (1H) ---")
        print(f"Trades:        {res.get('total_trades', 0)}")
        if res.get('total_trades', 0) > 0:
            print(f"Win Rate:      {res.get('win_rate', 0)*100:.2f}%")
            print(f"Profit Factor: {res.get('profit_factor', 0)}")
            print(f"Max Drawdown:  ${res.get('max_drawdown', 0):.2f}")
            print(f"Expectancy:    ${res.get('expectancy', 0):.2f}")
            if res.get('total_trades', 0) < 30:
                print(f"Status:        INCONCLUSIVE (<30 trades)")
            else:
                print(f"Status:        PROMOTED" if res.get('profit_factor', 0) > 1.0 else "Status:        REJECTED")
        print("-----------------------------------------")

if __name__ == "__main__":
    run_advanced_tests()
