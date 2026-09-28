import os
import sys
import pandas as pd
sys.path.append(os.path.dirname(__file__))

from src.core.backtester import Backtester
from src.strategies.phase5 import Phase5Strategy

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")

def load_data(asset):
    spot_path = os.path.join(CACHE_DIR, f"{asset}_spot_1h_700d.csv")
    fund_path = os.path.join(CACHE_DIR, f"{asset}_funding_700d.csv")
    
    if not os.path.exists(spot_path) or not os.path.exists(fund_path):
        return None
        
    df_spot = pd.read_csv(spot_path)
    df_spot['timestamp'] = pd.to_datetime(df_spot['timestamp'], utc=True)
    df_spot = df_spot.set_index('timestamp').sort_index()
    
    df_fund = pd.read_csv(fund_path)
    if 'fundingTime' in df_fund.columns:
        df_fund['timestamp'] = pd.to_datetime(df_fund['fundingTime'], unit='ms', utc=True)
    elif 'timestamp' in df_fund.columns:
        df_fund['timestamp'] = pd.to_datetime(df_fund['timestamp'], utc=True)
        
    df_fund = df_fund.set_index('timestamp').sort_index()
    
    df = df_spot.join(df_fund[['fundingRate']], how='left')
    df['fundingRate'] = df['fundingRate'].ffill()
    df = df.reset_index()
    return df

def run_vault_test():
    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    
    print("\n==================================================")
    print("PHASE 5: THE VAULT (PRISTINE OUT-OF-SAMPLE TEST)")
    print("Strategy: Volatility Compression + Funding Extremes")
    print("Vault Slice: 2024-10-26 to 2025-04-24 (First 180 Days)")
    print("Risk Mode: FIXED R-MULTIPLE")
    print("==================================================")
    
    for asset in assets:
        df = load_data(asset)
        if df is None:
            continue
            
        # Define the Vault Slice
        vault_end = pd.to_datetime('2025-04-25', utc=True)
        
        strat = Phase5Strategy(f"Phase5_{asset}", "1.0", {})
        signals = strat.generate_signals(df)
        
        # Strictly slice to the Vault period
        signals_vault = signals[signals['timestamp'] < vault_end].copy().reset_index(drop=True)
        
        bt = Backtester(initial_capital=10000.0, asset=asset, risk_per_trade=0.02)
        bt.fixed_risk = True
        
        # This strategy uses 48h holds, so we MUST enable futures mode to correctly charge funding during the hold
        bt.is_futures = True
        bt.fee_rate = 0.0004
        bt.slippage_pct = 0.0005
        
        class HoldoutStrategy(Phase5Strategy):
            def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
                # Bypass generation, just return the exact pre-calculated slice
                return signals_vault
                
        strat_holdout = HoldoutStrategy(f"Phase5_{asset}", "1.0", {})
        
        res = bt.run(df, strat_holdout)["metrics"]
        
        trades = res.get('total_trades', 0)
        print(f"\n--- Strategy: Phase5 Candidate ({asset}) [VAULT] ---")
        print(f"Trades:        {trades}")
        
        if trades > 0:
            print(f"Win Rate:      {res.get('win_rate', 0)*100:.2f}%")
            print(f"Profit Factor: {res.get('profit_factor', 0):.2f}")
            print(f"Max Drawdown:  ${res.get('max_drawdown', 0):.2f}")
            print(f"Total PnL:     ${res.get('total_pnl', 0):.2f}")
            print(f"Expectancy:    ${res.get('expectancy', 0):.2f}")

if __name__ == "__main__":
    run_vault_test()
