import pandas as pd
import numpy as np
import os

# ECONOMIC RATIONALE:
# "Volatility Compression Aligning with Funding Rate Extremes"
# 1. We identify periods of extreme volatility compression (Bollinger Band Width in the bottom 20th percentile of the last 100 periods).
# 2. We identify market positioning extremes using the 8H Funding Rate Z-Score (lookback 720 hours).
# 3. If volatility is compressed and funding is heavily skewed long (Z-Score > 1.0), longs are overcrowded and complacent. A sudden bearish break (close below lower Bollinger Band) traps them, triggering a liquidation cascade. We enter SHORT.
# 4. If volatility is compressed and funding is heavily skewed short (Z-Score < -1.5), shorts are overcrowded. A sudden bullish break (close above upper Bollinger Band) traps them, triggering a short squeeze. We enter LONG.
# 5. We hold the position for a fixed 48 hours to capture the resulting momentum.

def load_data(symbol):
    spot_path = f"data_cache/{symbol}USDT_spot_1h_700d.csv"
    fund_path = f"data_cache/{symbol}USDT_funding_700d.csv"
    
    if not os.path.exists(spot_path) or not os.path.exists(fund_path):
        return None
        
    df_spot = pd.read_csv(spot_path)
    df_spot['timestamp'] = pd.to_datetime(df_spot['timestamp'])
    df_spot = df_spot.set_index('timestamp').sort_index()
    
    df_fund = pd.read_csv(fund_path)
    if 'fundingTime' in df_fund.columns:
        df_fund['timestamp'] = pd.to_datetime(df_fund['fundingTime'], unit='ms')
    elif 'timestamp' in df_fund.columns:
        df_fund['timestamp'] = pd.to_datetime(df_fund['timestamp'])
        
    df_fund = df_fund.set_index('timestamp').sort_index()
    
    df = df_spot.join(df_fund[['fundingRate']], how='left')
    df['fundingRate'] = df['fundingRate'].ffill()
    
    # In-Sample filter
    df = df[df.index >= '2025-04-25']
    
    return df

def run_strategy(df):
    fund_lookback = 720
    fund_pct_upper = 1.0
    fund_pct_lower = -1.5
    bb_len = 20
    bb_mult = 1.5
    hold_periods = 48
    
    df = df.copy()
    
    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(bb_len).mean()
    df['bb_std'] = df['close'].rolling(bb_len).std()
    df['bb_upper'] = df['bb_mid'] + bb_mult * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - bb_mult * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    
    # BB Width Percentile
    df['bb_width_pct'] = df['bb_width'].rolling(100).rank(pct=True)
    
    # Funding Z-score
    df['fund_mean'] = df['fundingRate'].rolling(fund_lookback).mean()
    df['fund_std'] = df['fundingRate'].rolling(fund_lookback).std()
    df['fund_z'] = (df['fundingRate'] - df['fund_mean']) / df['fund_std']
    
    # Volatility expansion from compression
    # We require that yesterday's width was compressed, and today we break out
    was_compressed = df['bb_width_pct'].shift(1) < 0.2
    
    df['long_cond'] = (df['fund_z'] < fund_pct_lower) & (df['close'] > df['bb_upper']) & (df['close'].shift(1) <= df['bb_upper'].shift(1)) & was_compressed
    df['short_cond'] = (df['fund_z'] > fund_pct_upper) & (df['close'] < df['bb_lower']) & (df['close'].shift(1) >= df['bb_lower'].shift(1)) & was_compressed
    
    df['ret_long'] = df['close'].shift(-hold_periods) / df['close'] - 1
    df['ret_short'] = 1 - df['close'].shift(-hold_periods) / df['close']
    
    long_trades = df.loc[df['long_cond'], 'ret_long'].dropna().tolist()
    short_trades = df.loc[df['short_cond'], 'ret_short'].dropna().tolist()
    
    return long_trades + short_trades

def main():
    symbols = ['BTC', 'ETH', 'SOL', 'BNB']
    dfs = {sym: load_data(sym) for sym in symbols if load_data(sym) is not None}
    
    all_trades = []
    for sym, df in dfs.items():
        trades = run_strategy(df)
        all_trades.extend(trades)
        
    wins = [t for t in all_trades if t > 0]
    losses = [t for t in all_trades if t <= 0]
    
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0
    
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    win_rate = len(wins) / len(all_trades)
    
    print(f"Final Candidate Performance:")
    print(f"Trades: {len(all_trades)}")
    print(f"Profit Factor: {pf:.4f}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Mean Return: {np.mean(all_trades):.4%}")

if __name__ == "__main__":
    main()
