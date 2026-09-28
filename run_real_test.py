import os
import sys
sys.path.append(os.path.dirname(__file__))

import yfinance as yf
import pandas as pd
from src.strategies.trend import TrendFollowingStrategy
from src.core.backtester import Backtester
from src.analysis.research import ResearchEngine
from src.core.database import get_db_connection
import sqlite3

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_yf_data(ticker="BTC-USD", interval="1h", period="700d", exclude_holdout=True):
    cache_file = os.path.join(CACHE_DIR, f"{ticker}_{interval}_{period}.csv")
    
    if os.path.exists(cache_file):
        print(f"Loading {ticker} {interval} {period} from local cache...")
        df = pd.read_csv(cache_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    else:
        print(f"Fetching ~2 years ({period}) of {interval} data for {ticker} via yfinance...")
        df = yf.download(ticker, interval=interval, period=period, progress=False)
        if df.empty:
            print(f"Failed to fetch data for {ticker}")
            return pd.DataFrame()
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.reset_index(inplace=True)
        col_map = {'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}
        df.rename(columns=col_map, inplace=True)
        df.columns = [c.lower() for c in df.columns]
        
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].dropna()
        df.to_csv(cache_file, index=False)
        
    if exclude_holdout and not df.empty:
        max_date = df['timestamp'].max()
        cutoff_date = max_date - pd.Timedelta(days=180)
        df = df[df['timestamp'] < cutoff_date]
        print(f"Holdout enforced: Excluded last 180 days. Training data ends on {cutoff_date.date()}")
        
    return df

def fetch_yf_data_holdout(ticker="BTC-USD", interval="1h", period="700d"):
    cache_file = os.path.join(CACHE_DIR, f"{ticker}_{interval}_{period}.csv")
    
    if not os.path.exists(cache_file):
        print(f"Error: Cache file not found for holdout extraction: {cache_file}")
        return pd.DataFrame()
        
    df = pd.read_csv(cache_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    
    max_date = df['timestamp'].max()
    cutoff_date = max_date - pd.Timedelta(days=180)
    
    # Return ONLY the holdout data
    df_holdout = df[df['timestamp'] >= cutoff_date]
    print(f"Loaded HOLDOUT OOS data for {ticker}: {cutoff_date.date()} to {max_date.date()} ({len(df_holdout)} bars)")
    return df_holdout

def run_test():
    assets = ["BTC-USD", "ETH-USD", "EURUSD=X"]
    bt = Backtester(initial_capital=10000.0, fee_rate=0.001, slippage_pct=0.0005)
    
    for asset in assets:
        print(f"\n=========================================")
        print(f"Testing Asset: {asset}")
        print(f"=========================================")
        
        df = fetch_yf_data(asset, "1h", "730d")
        print(f"Fetched {len(df)} rows of actual market data (spanning multiple market regimes).")
        
        # 1. Run backtest on deep historical data
        strat = TrendFollowingStrategy(f"Trend_{asset}", "1.0", {"fast_ema": 20, "slow_ema": 50, "rsi_threshold": 70})
        res = bt.run(df, strat)
        metrics = res["metrics"]
        print("\n--- DEEP HISTORY BACKTEST RESULTS ---")
        print(f"Total Trades:  {metrics['total_trades']}")
        print(f"Win Rate:      {metrics['win_rate']*100:.2f}%")
        print(f"Expectancy:    ${metrics['expectancy']}")
        print(f"Profit Factor: {metrics['profit_factor']}")
        print(f"Max Drawdown:  ${metrics['max_drawdown']}")
        print(f"Total PnL:     ${metrics['total_pnl']}")
        print("-------------------------------------")
        
        # 2. Run Mutation Test (Research Loop)
        # Test modifying the fast EMA to 5 (making it extremely reactive, generating tons of bad signals)
        print("\nRunning Mutation Test (modifying fast_ema to 5)...")
        engine = ResearchEngine(bt, df)
        engine.run_mutation_experiment(strat, "fast_ema", 5)
        
        # 3. Retrieve from SQLite
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM experiment_journal WHERE base_strategy_id='Trend_{asset}' ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            
        if row:
            print("\n--- SQLITE EXPERIMENT JOURNAL ENTRY ---")
            print(f"ID:                  {row[0]}")
            print(f"Base Strategy ID:    {row[2]}")
            print(f"New Version:         {row[3]}")
            print(f"Mutations:           {row[4]}")
            print(f"Status:              {row[9]}")
            print(f"Reasoning:           {row[10]}")
            print("---------------------------------------\n")

if __name__ == "__main__":
    run_test()
