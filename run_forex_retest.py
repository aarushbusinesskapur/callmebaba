import os
import sys
sys.path.append(os.path.dirname(__file__))

import pandas as pd
from run_real_test import fetch_yf_data
from src.core.backtester import Backtester
from src.strategies.trend import TrendFollowingStrategy
from src.strategies.squeeze import VolatilitySqueezeStrategy
from src.strategies.session import SessionOpenMomentumStrategy, LondonFakeoutFadeStrategy

def run_forex_retest():
    assets = ["EURUSD=X", "GBPUSD=X", "JPY=X"]
    
    print("\n==================================================")
    print("FOREX RETEST: CORRECTED INSTITUTIONAL SPREADS")
    print("Holdout Period Applied: Last 180 days excluded")
    print("==================================================")
    
    strategies = [
        ("Naive Crossover", TrendFollowingStrategy, {}),
        ("Volatility Breakout", VolatilitySqueezeStrategy, {}),
        ("Session Momentum", SessionOpenMomentumStrategy, {"rr_ratio": 1.5}),
        ("London Fakeout Fade", LondonFakeoutFadeStrategy, {"lookback_n": 3, "atr_buffer": 0.25})
    ]
    
    for asset in assets:
        print(f"\n##################################################")
        print(f"ASSET: {asset}")
        print(f"##################################################")
        
        df = fetch_yf_data(asset, "1h", "700d", exclude_holdout=True)
        if df.empty:
            continue
            
        bt = Backtester(initial_capital=10000.0, asset=asset, risk_per_trade=0.02)
        
        for name, StratClass, params in strategies:
            print(f"\n--- Strategy: {name} ---")
            strat = StratClass(f"{name.replace(' ', '_')}_{asset}", "1.0", params)
            res = bt.run(df, strat)["metrics"]
            
            trades = res.get('total_trades', 0)
            print(f"Trades:        {trades}")
            
            if trades > 0:
                print(f"Win Rate:      {res.get('win_rate', 0)*100:.2f}%")
                print(f"Profit Factor: {res.get('profit_factor', 0):.2f}")
                print(f"Max Drawdown:  ${res.get('max_drawdown', 0):.2f}")
                print(f"Total PnL:     ${res.get('total_pnl', 0):.2f}")
                
                if trades < 30:
                    print(f"Status:        INCONCLUSIVE (<30 trades)")
                elif res.get('profit_factor', 0) > 1.2:
                    print(f"Status:        PROMOTED")
                else:
                    print(f"Status:        REJECTED (Profit Factor < 1.2)")

if __name__ == "__main__":
    run_forex_retest()
