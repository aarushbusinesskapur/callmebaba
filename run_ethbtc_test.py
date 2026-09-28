import os
import sys
import pandas as pd
sys.path.append(os.path.dirname(__file__))

from src.core.backtester import Backtester
from src.strategies.pairs import BollingerMeanReversionStrategy

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")

def run_ethbtc_test():
    asset = "ETHBTC"
    
    print("\n==================================================")
    print("RELATIVE VALUE: ETH/BTC PAIRS MEAN REVERSION")
    print("Timeframe: 1H")
    print("Entry: Bollinger Bands (20, 2 StdDev)")
    print("Exit: TP = 20-SMA | SL = Band + 1.0 ATR")
    print("Holdout Period Applied: Last 180 days excluded")
    print("Risk Mode: FIXED R-MULTIPLE (Full Sample Tracking)")
    print("==================================================")
    
    cache_file = os.path.join(CACHE_DIR, f"{asset}_spot_1h_700d.csv")
    if not os.path.exists(cache_file):
        print(f"Error: Missing spot cache for {asset}")
        return
        
    df = pd.read_csv(cache_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    
    # Enforce Holdout
    max_date = df['timestamp'].max()
    cutoff_date = max_date - pd.Timedelta(days=180)
    df_train = df[df['timestamp'] < cutoff_date].copy().reset_index(drop=True)
    
    print(f"Training data: {df_train['timestamp'].min().date()} to {df_train['timestamp'].max().date()}")
    
    bt = Backtester(initial_capital=10000.0, asset=asset, risk_per_trade=0.02)
    bt.fixed_risk = True 
    bt.fee_rate = 0.001
    bt.slippage_pct = 0.0005
    bt.is_futures = False
    
    strat = BollingerMeanReversionStrategy(f"BB_Pairs_{asset}", "1.0", {})
    
    res = bt.run(df_train, strat)["metrics"]
    
    trades = res.get('total_trades', 0)
    print(f"\n--- Strategy: Bollinger Mean Reversion ({asset}) ---")
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
    run_ethbtc_test()
