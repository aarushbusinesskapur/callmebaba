import os
import sys
sys.path.append(os.path.dirname(__file__))

import pandas as pd
import numpy as np
from run_real_test import fetch_yf_data
from src.analysis.regime import RegimeClassifier
from src.core.backtester import Backtester
from src.strategies.trend import TrendFollowingStrategy

class ADXFilteredTrendStrategy(TrendFollowingStrategy):
    """
    Applies the rewritten Phase 4 ADX RegimeClassifier logic independently.
    """
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = super().generate_signals(df)
        
        # Calculate independent regime
        df_reg = RegimeClassifier.vectorize_regime(df)
        
        # Valid regime: Only take trades when market is explicitly TRENDING (ADX > 25)
        # We also want to avoid trading right in the middle of a dead volatility squeeze
        valid_regime = (df_reg['regime_state'] == 'TRENDING') & (~df_reg['squeeze_on'])
        
        # Mute the entry signal if the regime is invalid
        df['entry_signal'] = np.where(valid_regime & (df['entry_signal'] == 1), 1, 0)
        
        return df

class RelaxedADXFilteredTrendStrategy(TrendFollowingStrategy):
    """
    Applies the RegimeClassifier logic but lowers ADX threshold to 20 
    to try and achieve statistical significance (>30 trades).
    """
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = super().generate_signals(df)
        df_reg = RegimeClassifier.vectorize_regime(df)
        
        # Valid regime: ADX > 20 and not in a squeeze
        valid_regime = (df_reg['adx'] > 20) & (~df_reg['squeeze_on'])
        
        # Mute the entry signal if the regime is invalid
        df['entry_signal'] = np.where(valid_regime & (df['entry_signal'] == 1), 1, 0)
        return df

def run_analysis():
    # 5 diverse assets
    assets = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "EURUSD=X"]
    
    print("\n==================================================")
    print("REGIME-FILTERED BACKTEST COMPARISON (2 Years 1H)")
    print("Account: $10,000 | Risk: 2% per trade")
    print("==================================================")
    
    bt = Backtester(initial_capital=10000.0, fee_rate=0.001, slippage_pct=0.0005, risk_per_trade=0.02)
    
    for asset in assets:
        print(f"\n--- Backtesting {asset} ---")
        df = fetch_yf_data(asset, "1h", "700d")
        if df.empty:
            continue
            
        naive_strat = TrendFollowingStrategy(f"Naive_{asset}", "1.0", {"fast_ema": 20, "slow_ema": 50, "rsi_threshold": 70})
        naive_res = bt.run(df, naive_strat)["metrics"]
        
        strict_strat = ADXFilteredTrendStrategy(f"Strict_{asset}", "1.0", {"fast_ema": 20, "slow_ema": 50, "rsi_threshold": 70})
        strict_res = bt.run(df, strict_strat)["metrics"]
        
        relaxed_strat = RelaxedADXFilteredTrendStrategy(f"Relaxed_{asset}", "1.0", {"fast_ema": 20, "slow_ema": 50, "rsi_threshold": 70})
        relaxed_res = bt.run(df, relaxed_strat)["metrics"]
        
        print(f"[NAIVE] Trades: {naive_res.get('total_trades', 0)} | Win Rate: {naive_res.get('win_rate', 0)*100:.2f}% | PF: {naive_res.get('profit_factor', 0)} | DD: ${naive_res.get('max_drawdown', 0)}")
        print(f"[STRICT ADX>25] Trades: {strict_res.get('total_trades', 0)} | Win Rate: {strict_res.get('win_rate', 0)*100:.2f}% | PF: {strict_res.get('profit_factor', 0)} | DD: ${strict_res.get('max_drawdown', 0)}")
        print(f"[RELAXED ADX>20] Trades: {relaxed_res.get('total_trades', 0)} | Win Rate: {relaxed_res.get('win_rate', 0)*100:.2f}% | PF: {relaxed_res.get('profit_factor', 0)} | DD: ${relaxed_res.get('max_drawdown', 0)}")
        print("-----------------------------------------")

if __name__ == "__main__":
    run_analysis()
