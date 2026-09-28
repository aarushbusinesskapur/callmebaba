import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy

class SessionOpenMomentumStrategy(BaseStrategy):
    """
    Implements the Session Open Momentum Thesis.
    Thesis: The Asian session (00:00-08:00 UTC) establishes a consolidation range.
    A breakout of this range during the high-liquidity London open (08:00-10:00 UTC) 
    or NY open (13:00-15:00 UTC) tends to inaugurate a directional trend for the day.
    """
    
    def __init__(self, strategy_id: str, version: str, parameters: dict):
        super().__init__(strategy_id, version, parameters)
        self.rr_ratio = self.parameters.get("rr_ratio", 1.5)
        self.parameters["use_trailing_stop"] = False
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Ensure timestamp is datetime and timezone aware (UTC)
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
        df['hour'] = df['timestamp'].dt.hour
        df['date'] = df['timestamp'].dt.date
        
        # 1. Define the Asian Session Range (00:00 to 07:59 UTC)
        # For 1H bars, hours 0, 1, 2, 3, 4, 5, 6, 7 represent the Asian session
        asian_mask = df['hour'].isin([0, 1, 2, 3, 4, 5, 6, 7])
        asian_session = df[asian_mask]
        
        asian_ranges = asian_session.groupby('date').agg({
            'high': 'max',
            'low': 'min'
        }).rename(columns={'high': 'asian_high', 'low': 'asian_low'})
        
        # Merge back to original dataframe
        df = df.drop(columns=['asian_high', 'asian_low'], errors='ignore')
        df = df.merge(asian_ranges, on='date', how='left')
        
        # 2. Define the Entry Windows (London: 8,9 and NY: 13,14)
        entry_window_mask = df['hour'].isin([8, 9, 13, 14])
        
        # 3. Trigger Condition (Breakout)
        long_breakout = entry_window_mask & (df['close'] > df['asian_high'])
        short_breakout = entry_window_mask & (df['close'] < df['asian_low'])
        
        # Only take the FIRST signal of the day to avoid overtrading a choppy range
        # We can do this by marking the first breakout
        # But our backtester naturally prevents re-entry if `in_position` is true.
        # We will just pass the signals directly.
        df['entry_signal'] = np.select([long_breakout, short_breakout], [1, -1], default=0)
        
        # 4. Define Stop Loss and Take Profit
        # SL: Opposite side of the Asian Range
        df['sl'] = np.where(df['entry_signal'] == 1, df['asian_low'],
                   np.where(df['entry_signal'] == -1, df['asian_high'], np.nan))
                   
        # Protect against NaN SL or 0-width ranges (can happen if data is flat)
        valid_sl = (df['sl'].notna()) & (df['sl'] != df['close'])
        df['entry_signal'] = np.where(valid_sl, df['entry_signal'], 0)
        
        # TP: Fixed R:R target
        risk = abs(df['close'] - df['sl'])
        df['tp2'] = np.where(df['entry_signal'] == 1, df['close'] + (risk * self.rr_ratio),
                    np.where(df['entry_signal'] == -1, df['close'] - (risk * self.rr_ratio), np.nan))
                    
        return df

class LondonFakeoutFadeStrategy(BaseStrategy):
    """
    Implements the London/NY Fakeout Fade (Judas Swing) Thesis.
    Thesis: Breakouts of the Asian range during London/NY opens are often liquidity sweeps.
    If a breakout occurs but reverses back inside the Asian range within N bars,
    we fade it targeting the opposite side of the range.
    """
    
    def __init__(self, strategy_id: str, version: str, parameters: dict):
        super().__init__(strategy_id, version, parameters)
        self.lookback_n = self.parameters.get("lookback_n", 3)
        self.atr_buffer = self.parameters.get("atr_buffer", 0.25)
        self.parameters["use_trailing_stop"] = False
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
        df['hour'] = df['timestamp'].dt.hour
        df['date'] = df['timestamp'].dt.date
        df['atr'] = df['high'] - df['low'] # Approximation, real ATR should use Indicators, but this works for 1H buffer
        
        asian_mask = df['hour'].isin([0, 1, 2, 3, 4, 5, 6, 7])
        asian_ranges = df[asian_mask].groupby('date').agg({
            'high': 'max', 'low': 'min'
        }).rename(columns={'high': 'asian_high', 'low': 'asian_low'})
        
        df = df.drop(columns=['asian_high', 'asian_low'], errors='ignore')
        df = df.merge(asian_ranges, on='date', how='left')
        
        entry_window_mask = df['hour'].isin([8, 9, 13, 14])
        
        long_breakout = entry_window_mask & (df['close'] > df['asian_high'])
        short_breakout = entry_window_mask & (df['close'] < df['asian_low'])
        
        recent_long_bo = long_breakout.shift(1).fillna(False).astype(int).rolling(self.lookback_n).sum() > 0
        recent_short_bo = short_breakout.shift(1).fillna(False).astype(int).rolling(self.lookback_n).sum() > 0
        
        # Failed Long Breakout (Fakeout high) -> Enter SHORT
        # Must have had a long breakout recently, and current close is back BELOW the Asian High
        fell_back_in = (df['close'].shift(1) > df['asian_high'].shift(1)) & (df['close'] < df['asian_high'])
        failed_long = recent_long_bo & fell_back_in
        
        # Failed Short Breakout (Fakeout low) -> Enter LONG
        climbed_back_in = (df['close'].shift(1) < df['asian_low'].shift(1)) & (df['close'] > df['asian_low'])
        failed_short = recent_short_bo & climbed_back_in
        
        df['entry_signal'] = np.select([failed_short, failed_long], [1, -1], default=0)
        
        # Stop Loss: Fakeout extreme + buffer
        lowest_low_n = df['low'].rolling(self.lookback_n).min()
        highest_high_n = df['high'].rolling(self.lookback_n).max()
        
        df['sl'] = np.where(df['entry_signal'] == 1, lowest_low_n - (self.atr_buffer * df['atr']),
                   np.where(df['entry_signal'] == -1, highest_high_n + (self.atr_buffer * df['atr']), np.nan))
                   
        valid_sl = (df['sl'].notna()) & (df['sl'] != df['close'])
        df['entry_signal'] = np.where(valid_sl, df['entry_signal'], 0)
        
        # Target: Opposite side of the Asian Range
        df['tp2'] = np.where(df['entry_signal'] == 1, df['asian_high'],
                    np.where(df['entry_signal'] == -1, df['asian_low'], np.nan))
                    
        return df
