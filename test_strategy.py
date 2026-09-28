import pandas as pd
import numpy as np
import os
import itertools
from datetime import datetime

# Economic Rationale:
# Leverage Unwinds via Volatility Breakouts.
# High positive funding means longs are overcrowded. A bearish volatility breakout traps them, leading to long liquidations.
# High negative funding means shorts are overcrowded. A bullish volatility breakout traps them, leading to short squeezes.
# 
# We test combinations of:
# - Funding threshold (percentile of recent funding rates)
# - Keltner Channel multiplier (volatility threshold)
# - Holding period (time-based exit)

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
    # Funding rate is usually 8H, forward fill to 1H
    
    df = df_spot.join(df_fund[['fundingRate']], how='left')
    df['fundingRate'] = df['fundingRate'].ffill()
    
    # Strictly filter for IN-SAMPLE
    df = df[df.index >= '2025-04-25']
    
    return df

def run_backtest(df, fund_lookback, fund_pct_upper, fund_pct_lower, kc_len, kc_mult, hold_periods):
    # Calculate indicators
    df = df.copy()
    
    # Keltner Channels
    df['tr'] = np.maximum(df['high'] - df['low'], 
               np.maximum(abs(df['high'] - df['close'].shift(1)), 
                          abs(df['low'] - df['close'].shift(1))))
    df['atr'] = df['tr'].rolling(kc_len).mean()
    df['kc_mid'] = df['close'].rolling(kc_len).mean()
    df['kc_upper'] = df['kc_mid'] + kc_mult * df['atr']
    df['kc_lower'] = df['kc_mid'] - kc_mult * df['atr']
    
    # Funding Z-score
    df['fund_mean'] = df['fundingRate'].rolling(fund_lookback).mean()
    df['fund_std'] = df['fundingRate'].rolling(fund_lookback).std()
    df['fund_z'] = (df['fundingRate'] - df['fund_mean']) / df['fund_std']
    
    df = df.dropna()
    
    # Conditions
    # Long: Funding is extremely negative AND price closes above KC Upper
    df['long_cond'] = (df['fund_z'] < fund_pct_lower) & (df['close'] > df['kc_upper']) & (df['close'].shift(1) <= df['kc_upper'].shift(1))
    
    # Short: Funding is extremely positive AND price closes below KC Lower
    df['short_cond'] = (df['fund_z'] > fund_pct_upper) & (df['close'] < df['kc_lower']) & (df['close'].shift(1) >= df['kc_lower'].shift(1))
    
    trades = []
    in_trade = 0 # 1 for long, -1 for short
    entry_price = 0
    bars_held = 0
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        if in_trade != 0:
            bars_held += 1
            if bars_held >= hold_periods:
                exit_price = row['close']
                ret = (exit_price - entry_price) / entry_price if in_trade == 1 else (entry_price - exit_price) / entry_price
                trades.append(ret)
                in_trade = 0
        
        if in_trade == 0:
            if row['long_cond']:
                in_trade = 1
                entry_price = row['close']
                bars_held = 0
            elif row['short_cond']:
                in_trade = -1
                entry_price = row['close']
                bars_held = 0
                
    return trades

def main():
    symbols = ['BTC', 'ETH', 'SOL', 'BNB']
    dfs = {sym: load_data(sym) for sym in symbols if load_data(sym) is not None}
    
    # Parameters for search
    # Funding Lookback: 30 days * 24 = 720 hours
    fund_lookbacks = [720]
    fund_pct_uppers = [1.5, 2.0]
    fund_pct_lowers = [-1.5, -2.0]
    kc_lens = [20, 50]
    kc_mults = [1.5, 2.0]
    hold_periodss = [12, 24, 48]
    
    params_list = list(itertools.product(fund_lookbacks, fund_pct_uppers, fund_pct_lowers, kc_lens, kc_mults, hold_periodss))
    
    N = 0
    results = []
    
    for params in params_list:
        N += 1
        all_trades = []
        for sym, df in dfs.items():
            trades = run_backtest(df, *params)
            all_trades.extend(trades)
            
        if len(all_trades) < 100:
            continue
            
        wins = [t for t in all_trades if t > 0]
        losses = [t for t in all_trades if t <= 0]
        
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        win_rate = len(wins) / len(all_trades)
        
        results.append({
            'N': N,
            'params': params,
            'trades': len(all_trades),
            'pf': pf,
            'win_rate': win_rate,
            'mean_ret': np.mean(all_trades)
        })
        
    print(f"Total combinations tested: {N}")
    
    valid_results = [r for r in results if r['pf'] > 1.3] # Hurdle for N=48 might be 1.4-1.5, let's see what we get
    valid_results = sorted(valid_results, key=lambda x: x['pf'], reverse=True)
    
    if not valid_results:
        print("No candidates passed the hurdle.")
    else:
        best = valid_results[0]
        print(f"BEST CANDIDATE: {best}")
        
if __name__ == "__main__":
    main()
