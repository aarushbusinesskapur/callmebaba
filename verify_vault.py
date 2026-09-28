import os
import pandas as pd
import sys
sys.path.append(os.path.dirname(__file__))

from run_phase5_vault import load_data
from src.strategies.phase5 import Phase5Strategy
from src.core.backtester import Backtester

def generate_vault_trade_log():
    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    all_trades = []
    
    for asset in assets:
        df = load_data(asset)
        if df is None:
            continue
            
        vault_end = pd.to_datetime('2025-04-25', utc=True)
        strat = Phase5Strategy(f"Phase5_{asset}", "1.0", {})
        signals = strat.generate_signals(df)
        signals_vault = signals[signals['timestamp'] < vault_end].copy().reset_index(drop=True)
        
        bt = Backtester(initial_capital=10000.0, asset=asset, risk_per_trade=0.02)
        bt.fixed_risk = True
        bt.is_futures = True
        bt.fee_rate = 0.0004
        bt.slippage_pct = 0.0005
        
        class HoldoutStrategy(Phase5Strategy):
            def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
                return signals_vault
                
        res = bt.run(df, HoldoutStrategy(f"Phase5_{asset}", "1.0", {}))
        
        for t in res.get("trades", []):
            t['asset'] = asset
            all_trades.append(t)
            
    # Sort by entry time
    all_trades.sort(key=lambda x: x['entry_time'])
    
    with open("vault_trades_raw.txt", "w") as f:
        f.write("RAW VAULT TRADE LOG (PHASE 5)\n")
        f.write("=========================================\n")
        f.write(f"Total Trades: {len(all_trades)}\n\n")
        
        for i, t in enumerate(all_trades):
            f.write(f"Trade {i+1}:\n")
            f.write(f"  Asset:      {t['asset']}\n")
            f.write(f"  Entry Time: {t['entry_time']}\n")
            f.write(f"  Direction:  {t['direction']}\n")
            f.write(f"  PnL:        ${t['pnl']:.2f}\n")
            f.write("-" * 40 + "\n")
            
    print("Wrote vault_trades_raw.txt")

if __name__ == "__main__":
    generate_vault_trade_log()
