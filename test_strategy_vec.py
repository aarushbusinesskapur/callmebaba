import pandas as pd
import numpy as np
import os
import itertools
from datetime import datetime

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
    
    df = df[df.index >= '2025-04-25']
    
    return df

def run_backtest_vectorized(df, fund_lookback, fund_pct_upper, fund_pct_lower, kc_len, kc_mult, hold_periods):
    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(kc_len).mean()
    df['bb_std'] = df['close'].rolling(kc_len).std()
    df['bb_upper'] = df['bb_mid'] + kc_mult * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - kc_mult * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    
    # BB Width Percentile
    df['bb_width_pct'] = df['bb_width'].rolling(100).rank(pct=True)
    
    df['fund_mean'] = df['fundingRate'].rolling(fund_lookback).mean()
    df['fund_std'] = df['fundingRate'].rolling(fund_lookback).std()
    df['fund_z'] = (df['fundingRate'] - df['fund_mean']) / df['fund_std']
    
    # Volatility expansion from compression
    is_expanding = df['bb_width_pct'] > 0.5
    was_compressed = df['bb_width_pct'].shift(1) < 0.2
    
    # LONG: Funding is negative (shorts crowded), volatility expands upwards
    df['long_cond'] = (df['fund_z'] < fund_pct_lower) & (df['close'] > df['bb_upper']) & (df['close'].shift(1) <= df['bb_upper'].shift(1)) & was_compressed
    
    # SHORT: Funding is positive (longs crowded), volatility expands downwards
    df['short_cond'] = (df['fund_z'] > fund_pct_upper) & (df['close'] < df['bb_lower']) & (df['close'].shift(1) >= df['bb_lower'].shift(1)) & was_compressed
    
    # Forward looking returns
    df['ret_long'] = df['close'].shift(-hold_periods) / df['close'] - 1
    df['ret_short'] = 1 - df['close'].shift(-hold_periods) / df['close']
    
    long_trades = df.loc[df['long_cond'], 'ret_long'].dropna().tolist()
    short_trades = df.loc[df['short_cond'], 'ret_short'].dropna().tolist()
    
    # To mimic non-overlapping, we could filter, but for parameter search this gives a good proxy
    # In reality, non-overlapping is better but this is much faster.
    
    return long_trades + short_trades

def main():
    symbols = ['BTC', 'ETH', 'SOL', 'BNB']
    dfs = {sym: load_data(sym) for sym in symbols if load_data(sym) is not None}
    
    fund_lookbacks = [360, 720]
    fund_pct_uppers = [1.0, 1.5]
    fund_pct_lowers = [-1.0, -1.5]
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
            trades = run_backtest_vectorized(df, *params)
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
    
    valid_results = [r for r in results if r['pf'] > 1.3]
    valid_results = sorted(valid_results, key=lambda x: x['pf'], reverse=True)
    
    if not valid_results:
        print("No candidates passed the hurdle.")
        for r in sorted(results, key=lambda x: x['pf'], reverse=True)[:5]:
            print(f"Top: PF {r['pf']:.2f}, Trades {r['trades']}, Params: {r['params']}")
    else:
        best = valid_results[0]
        print(f"BEST CANDIDATE: {best}")
        
if __name__ == "__main__":
    main()
