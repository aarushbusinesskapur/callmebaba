import os
import sys
sys.path.append(os.path.dirname(__file__))

import pandas as pd
from run_real_test import fetch_yf_data
from src.core.backtester import Backtester
from src.strategies.funding import FundingRateReversionStrategy

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")

def run_funding_test():
    assets = [
        ("BTC-USD", "BTCUSDT"), 
        ("ETH-USD", "ETHUSDT"),
        ("SOL-USD", "SOLUSDT"),
        ("BNB-USD", "BNBUSDT")
    ]
    
    print("\n==================================================")
    print("FUNDING RATE MEAN REVERSION (PERPETUAL FUTURES)")
    print("Holding Horizon: Dynamic Exit (Reversion) or Max 120 Hours")
    print("Fees: 0.04% Taker | Slippage: 0.05% | Funding Paid/Received")
    print("Holdout Period Applied: Last 180 days excluded")
    print("==================================================")
    
    for yf_ticker, binance_ticker in assets:
        print(f"\n##################################################")
        print(f"ASSET: {yf_ticker} (Funding: {binance_ticker})")
        print(f"##################################################")
        
        # Load 1H OHLCV (Holdout Excluded)
        df_spot = fetch_yf_data(yf_ticker, "1h", "700d", exclude_holdout=True)
        if df_spot.empty:
            continue
            
        # Load Funding Rates
        funding_cache = os.path.join(CACHE_DIR, f"{binance_ticker}_funding_700d.csv")
        if not os.path.exists(funding_cache):
            print(f"Funding data for {binance_ticker} not found.")
            continue
            
        df_funding = pd.read_csv(funding_cache)
        df_funding['fundingTime'] = pd.to_datetime(df_funding['fundingTime'], format='ISO8601', utc=True)
        
        # Merge Spot and Funding
        df = pd.merge(df_spot, df_funding, left_on='timestamp', right_on='fundingTime', how='left')
        df['fundingRate'] = df['fundingRate'].ffill()
        df.drop(columns=['fundingTime'], inplace=True, errors='ignore')
        
        # Drop rows where funding rate is still NaN (start of dataset)
        df = df.dropna(subset=['fundingRate']).reset_index(drop=True)
        
        # Initialize Backtester
        # yf_ticker lacks "=X", so it will correctly trigger Binance Perp Costs in the Backtester
        bt = Backtester(initial_capital=10000.0, asset=yf_ticker, risk_per_trade=0.02)
        
        # Run Strategy
        strat = FundingRateReversionStrategy(f"FundingRev_{yf_ticker}", "1.0", {
            "lookback_days": 90,
            "upper_percentile": 0.95,
            "lower_percentile": 0.05,
            "hold_hours": 72
        })
        
        res = bt.run(df, strat)["metrics"]
        
        trades = res.get('total_trades', 0)
        print(f"\n--- Strategy: 95th Percentile Funding Fade (Dynamic Exit) ---")
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
    run_funding_test()
