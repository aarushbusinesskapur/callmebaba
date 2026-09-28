import os
import sys
sys.path.append(os.path.dirname(__file__))

import numpy as np
import pandas as pd
from src.strategies.trend import TrendFollowingStrategy
from src.strategies.indicators import Indicators
from src.core.backtester import Backtester
from run_real_test import fetch_yf_data

class RegimeFilteredTrendStrategy(TrendFollowingStrategy):
    """
    Applies the actual Phase 4 RegimeClassifier logic independently to filter signals.
    """
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = super().generate_signals(df)
        
        # 1. Independent Phase 4 Regime Calculation (Vectorized)
        sma20 = Indicators.sma(df['close'], 20)
        sma50 = Indicators.sma(df['close'], 50)
        returns = df['close'].pct_change()
        volatility = returns.rolling(20).std()
        
        is_strong_uptrend = (df['close'] > sma20) & (sma20 > sma50)
        is_weak_uptrend = (df['close'] > sma50) & ~is_strong_uptrend
        is_strong_downtrend = (df['close'] < sma20) & (sma20 < sma50)
        is_weak_downtrend = (df['close'] < sma50) & ~is_strong_downtrend
        
        is_sideways = ~(is_strong_uptrend | is_weak_uptrend | is_strong_downtrend | is_weak_downtrend)
        
        # Regime filter rule: Only take long trends if the regime is NOT sideways/ranging
        # and NOT in a strong downtrend. 
        valid_regime = ~is_sideways & ~is_strong_downtrend
        
        # Mute the entry signal if the regime is invalid
        df['entry_signal'] = np.where(valid_regime & (df['entry_signal'] == 1), 1, 0)
        
        return df

def run_comparison():
    assets = ["BTC-USD", "ETH-USD"]
    bt = Backtester(initial_capital=10000.0, fee_rate=0.001, slippage_pct=0.0005)
    
    for asset in assets:
        print(f"\n=========================================")
        print(f"Asset: {asset} (2 Years of 1H Data)")
        print(f"=========================================")
        
        df = fetch_yf_data(asset, "1h", "730d")
        
        # 1. Naive Strategy
        naive_strat = TrendFollowingStrategy(f"Naive_{asset}", "1.0", {"fast_ema": 20, "slow_ema": 50, "rsi_threshold": 70})
        naive_res = bt.run(df, naive_strat)["metrics"]
        
        # 2. Regime Filtered Strategy
        filtered_strat = RegimeFilteredTrendStrategy(f"Filtered_{asset}", "1.0", {"fast_ema": 20, "slow_ema": 50, "rsi_threshold": 70})
        filtered_res = bt.run(df, filtered_strat)["metrics"]
        
        print("\n[NAIVE CROSSOVER] (No Regime Filter)")
        print(f"Trades:        {naive_res['total_trades']}")
        print(f"Win Rate:      {naive_res['win_rate']*100:.2f}%")
        print(f"Expectancy:    ${naive_res['expectancy']}")
        print(f"Profit Factor: {naive_res['profit_factor']}")
        print(f"Max Drawdown:  ${naive_res['max_drawdown']}")
        
        print("\n[REGIME FILTERED] (Phase 4 Logic Applied)")
        print(f"Trades:        {filtered_res['total_trades']}")
        print(f"Win Rate:      {filtered_res['win_rate']*100:.2f}%")
        print(f"Expectancy:    ${filtered_res['expectancy']}")
        print(f"Profit Factor: {filtered_res['profit_factor']}")
        print(f"Max Drawdown:  ${filtered_res['max_drawdown']}")
        print("-----------------------------------------")

if __name__ == "__main__":
    run_comparison()
