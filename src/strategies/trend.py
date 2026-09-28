import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.strategies.indicators import Indicators
from src.core.signal import TargetCalculator

class TrendFollowingStrategy(BaseStrategy):
    """A real working trend-following strategy using dual EMAs, RSI, and ATR targets."""
    
    def __init__(self, strategy_id: str, version: str, parameters: dict):
        super().__init__(strategy_id, version, parameters)
        # Default params if not provided
        self.fast_ema = self.parameters.get("fast_ema", 20)
        self.slow_ema = self.parameters.get("slow_ema", 50)
        self.rsi_period = self.parameters.get("rsi_period", 14)
        self.rsi_threshold = self.parameters.get("rsi_threshold", 60)
        self.atr_period = self.parameters.get("atr_period", 14)
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # 1. Calculate Indicators
        df['fast_ema'] = Indicators.ema(df['close'], self.fast_ema)
        df['slow_ema'] = Indicators.ema(df['close'], self.slow_ema)
        df['rsi'] = Indicators.rsi(df['close'], self.rsi_period)
        
        # ATR Calculation
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(self.atr_period).mean()
        
        # 2. Logic: Trend is up (fast > slow), momentum is moderate (RSI < threshold)
        long_cond = (df['fast_ema'] > df['slow_ema']) & \
                    (df['fast_ema'].shift(1) <= df['slow_ema'].shift(1)) & \
                    (df['rsi'] < self.rsi_threshold)
                    
        df['entry_signal'] = np.where(long_cond, 1, 0)
        
        # 3. Calculate Targets
        df['sl'] = np.nan
        df['tp1'] = np.nan
        df['tp2'] = np.nan
        df['tp3'] = np.nan
        
        # Apply targets where entry signal is 1
        for idx in df[df['entry_signal'] == 1].index:
            entry_price = df.loc[idx, 'close']
            atr_val = df.loc[idx, 'atr']
            if pd.isna(atr_val): 
                atr_val = entry_price * 0.02
                
            targets = TargetCalculator.calculate_targets(entry_price, "LONG", atr=atr_val)
            df.loc[idx, 'sl'] = targets['sl']
            df.loc[idx, 'tp1'] = targets['tp1']
            df.loc[idx, 'tp2'] = targets['tp2']
            df.loc[idx, 'tp3'] = targets['tp3']
            
        return df
