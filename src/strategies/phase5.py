import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy

class Phase5Strategy(BaseStrategy):
    """
    Phase 5 AI Candidate: Volatility Compression + Funding Rate Extremes.
    Entry: Breakout of compressed BBs when Funding Z-Score is extreme.
    Exit: 48-hour time stop.
    """
    
    def __init__(self, strategy_id: str, version: str, parameters: dict):
        super().__init__(strategy_id, version, parameters)
        self.fund_lookback = self.parameters.get("fund_lookback", 720)
        self.fund_pct_upper = self.parameters.get("fund_pct_upper", 1.0)
        self.fund_pct_lower = self.parameters.get("fund_pct_lower", -1.5)
        self.bb_len = self.parameters.get("bb_len", 20)
        self.bb_mult = self.parameters.get("bb_mult", 1.5)
        self.hold_periods = self.parameters.get("hold_periods", 48)
        
        # Disable trailing stop to respect the AI's pure 48-hour hold logic
        self.parameters["use_trailing_stop"] = False
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Merge Funding Rate if not present
        # In run script we must ensure fundingRate is in the DF!
        if 'fundingRate' not in df.columns:
            # Fallback if somehow not joined, though the runner will join it
            df['fundingRate'] = 0.0
            
        # Bollinger Bands
        df['bb_mid'] = df['close'].rolling(self.bb_len).mean()
        df['bb_std'] = df['close'].rolling(self.bb_len).std()
        df['bb_upper'] = df['bb_mid'] + self.bb_mult * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - self.bb_mult * df['bb_std']
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
        df['bb_width_pct'] = df['bb_width'].rolling(100).rank(pct=True)
        
        # Funding Z-score
        df['fund_mean'] = df['fundingRate'].rolling(self.fund_lookback).mean()
        df['fund_std'] = df['fundingRate'].rolling(self.fund_lookback).std()
        df['fund_z'] = (df['fundingRate'] - df['fund_mean']) / df['fund_std']
        
        was_compressed = df['bb_width_pct'].shift(1) < 0.2
        
        long_cond = (df['fund_z'] < self.fund_pct_lower) & (df['close'] > df['bb_upper']) & (df['close'].shift(1) <= df['bb_upper'].shift(1)) & was_compressed
        short_cond = (df['fund_z'] > self.fund_pct_upper) & (df['close'] < df['bb_lower']) & (df['close'].shift(1) >= df['bb_lower'].shift(1)) & was_compressed
        
        df['entry_signal'] = np.select([long_cond, short_cond], [1, -1], default=0)
        
        # Need a wide catastrophe SL for position sizing mathematically
        df['tr'] = np.maximum(df['high'] - df['low'], 
                              np.maximum(abs(df['high'] - df['close'].shift()), 
                                         abs(df['low'] - df['close'].shift())))
        df['atr'] = df['tr'].rolling(14).mean()
        
        df['sl'] = np.where(df['entry_signal'] == 1, 
                            df['close'] - (df['atr'] * 3.0),
                   np.where(df['entry_signal'] == -1, 
                            df['close'] + (df['atr'] * 3.0), 
                            np.nan))
                            
        df['sl'] = df['sl'].ffill()
        df['time_stop_bars'] = self.hold_periods
        
        # --- INSTRUMENTATION START ---
        target_time = pd.to_datetime('2025-04-05 12:00:00+00:00')
        mask = df['timestamp'] == target_time
        if mask.any():
            idx = df[mask].index[0]
            
            print(f"\n--- INSTRUMENTATION TRACE: PHASE 5 SIGNAL LOGIC ---")
            print(f"Target Timestamp Evaluated: {df.loc[idx, 'timestamp']}")
            
            # Funding Rate Z-Score components
            fund_window = df.loc[idx - self.fund_lookback + 1 : idx, 'fundingRate']
            print(f"\n[Funding Z-Score Calculation]")
            print(f"Funding Rate at Current Bar: {df.loc[idx, 'fundingRate']:.8f}")
            print(f"Lookback Window Size:        {len(fund_window)} periods")
            print(f"Window Start Timestamp:      {df.loc[idx - self.fund_lookback + 1, 'timestamp']}")
            print(f"Window End Timestamp:        {df.loc[idx, 'timestamp']}")
            print(f"Calculated Mean:             {df.loc[idx, 'fund_mean']:.8f}")
            print(f"Calculated Std Dev:          {df.loc[idx, 'fund_std']:.8f}")
            print(f"Final Z-Score:               {df.loc[idx, 'fund_z']:.4f}")
            
            # BB Width Percentile components
            bb_window = df.loc[idx - 100 + 1 : idx, 'bb_width']
            print(f"\n[BB-Width Percentile Calculation]")
            print(f"BB Width at Current Bar:     {df.loc[idx, 'bb_width']:.6f}")
            print(f"Lookback Window Size:        {len(bb_window)} periods")
            print(f"Window Start Timestamp:      {df.loc[idx - 100 + 1, 'timestamp']}")
            print(f"Window End Timestamp:        {df.loc[idx, 'timestamp']}")
            print(f"Current Value Rank in Win:   {df.loc[idx, 'bb_width_pct']:.4f}")
            print(f"Was Compressed (Prev Bar):   {df.loc[idx-1, 'bb_width_pct'] < 0.2} (Rank: {df.loc[idx-1, 'bb_width_pct']:.4f})")
            
            # Triggers
            print(f"\n[Signal Triggers]")
            print(f"Close Price:                 {df.loc[idx, 'close']}")
            print(f"BB Lower Band:               {df.loc[idx, 'bb_lower']:.2f}")
            print(f"Prev Close Price:            {df.loc[idx-1, 'close']}")
            print(f"Prev BB Lower Band:          {df.loc[idx-1, 'bb_lower']:.2f}")
            print(f"Entry Signal Generated:      {df.loc[idx, 'entry_signal']}")
            print(f"---------------------------------------------------\n")
        # --- INSTRUMENTATION END ---
        
        return df
