import os
import sys
sys.path.append(os.path.dirname(__file__))

import pandas as pd
from run_real_test import fetch_yf_data
from src.core.backtester import Backtester
from src.strategies.squeeze import VolatilitySqueezeStrategy

def run_squeeze_test():
    assets = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "EURUSD=X"]
    
    print("\n==================================================")
    print("VOLATILITY SQUEEZE STRATEGY BACKTEST (2 Years 1H)")
    print("Account: $10,000 | Risk: 2% per trade")
    print("Exit Logic: 2.0x ATR Trailing Stop (Chandelier Exit)")
    print("==================================================")
    
    # Using fixed 2% risk of $10,000 account per trade
    bt = Backtester(initial_capital=10000.0, fee_rate=0.001, slippage_pct=0.0005, risk_per_trade=0.02)
    
    for asset in assets:
        df = fetch_yf_data(asset, "1h", "700d")
        if df.empty:
            continue
            
        strat = VolatilitySqueezeStrategy(f"Squeeze_{asset}", "1.0", {
            "bb_period": 20, "bb_std": 2.0, 
            "kc_period": 20, "kc_atr_period": 14, "kc_mult": 1.5,
            "vol_period": 20, "vol_mult": 1.5,
            "use_trailing_stop": True,
            "trailing_atr_multiplier": 2.0
        })
        
        res = bt.run(df, strat)["metrics"]
        
        print(f"\n--- {asset} ---")
        print(f"Trades:        {res.get('total_trades', 0)}")
        
        if res.get('total_trades', 0) > 0:
            print(f"Win Rate:      {res.get('win_rate', 0)*100:.2f}%")
            print(f"Profit Factor: {res.get('profit_factor', 0)}")
            print(f"Max Drawdown:  ${res.get('max_drawdown', 0):.2f}")
            print(f"Total PnL:     ${res.get('total_pnl', 0):.2f}")
            print(f"Expectancy:    ${res.get('expectancy', 0):.2f}")
            if res.get('total_trades', 0) < 30:
                print(f"Status:        INCONCLUSIVE (<30 trades)")
            elif res.get('profit_factor', 0) < 1.0:
                print(f"Status:        REJECTED (Profit Factor < 1.0)")
            else:
                print(f"Status:        PROMOTED")
        print("-----------------------------------------")

if __name__ == "__main__":
    run_squeeze_test()
