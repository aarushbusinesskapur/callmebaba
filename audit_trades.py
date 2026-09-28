import os
import sys
sys.path.append(os.path.dirname(__file__))

import pandas as pd
from run_real_test import fetch_yf_data
from src.core.backtester import Backtester
from src.strategies.session import LondonFakeoutFadeStrategy

def audit_trades():
    asset = "EURUSD=X"
    bt_fixed = Backtester(initial_capital=10000.0, fee_rate=0.001, slippage_pct=0.0005, risk_per_trade=0.02)
    
    df_1h = fetch_yf_data(asset, "1h", "700d", exclude_holdout=True)
    if df_1h.empty:
        print("No data.")
        return
        
    strat = LondonFakeoutFadeStrategy(f"FakeoutFade_{asset}", "1.0", {"lookback_n": 3, "atr_buffer": 0.25})
    
    result = bt_fixed.run(df_1h, strat)
    trades = result.get("trades", [])
    
    print("\n==================================================")
    print("MANUAL TRADE AUDIT: FIRST 5 TRADES (EUR/USD)")
    print("==================================================")
    
    for i, t in enumerate(trades[:5]):
        print(f"\n--- Trade {i+1} ---")
        print(f"Entry Time:   {t['entry_time']}")
        print(f"Exit Time:    {t['exit_time']} (Row Index)")
        print(f"Direction:    {t['direction']}")
        print(f"Entry Price:  {t['entry_price']:.5f}")
        print(f"Stop Loss:    {t['sl']:.5f}")
        print(f"Take Profit:  {t['tp']:.5f}")
        print(f"Exit Price:   {t['exit_price']:.5f}")
        print(f"Exit Reason:  {t['exit_reason']}")
        print(f"PnL:          ${t['pnl']:.2f}")

if __name__ == "__main__":
    audit_trades()
