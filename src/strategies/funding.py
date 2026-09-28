import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy

class FundingRateReversionStrategy(BaseStrategy):
    """
    Implements the Funding Rate Mean Reversion thesis.
    When funding rates reach extreme percentiles (e.g. >95th percentile),
    it implies retail is extremely over-leveraged in one direction.
    We fade this sentiment and hold for a multi-day horizon (e.g., 72 hours)
    to allow the liquidation cascade or mean reversion to play out.
    """
    
    def __init__(self, strategy_id: str, version: str, parameters: dict):
        super().__init__(strategy_id, version, parameters)
        self.lookback_days = self.parameters.get("lookback_days", 90)
        self.upper_percentile = self.parameters.get("upper_percentile", 0.95)
        self.lower_percentile = self.parameters.get("lower_percentile", 0.05)
        self.hold_hours = self.parameters.get("hold_hours", 72)
        
        self.parameters["use_trailing_stop"] = False
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        if 'fundingRate' not in df.columns:
            print("Error: fundingRate column missing from data.")
            df['entry_signal'] = 0
            return df
            
        # We need to rank the funding rate relative to its last 90 days.
        rolling_window = self.lookback_days * 24
        
        # Calculate percentiles dynamically
        df['fr_upper'] = df['fundingRate'].rolling(rolling_window).quantile(self.upper_percentile)
        df['fr_lower'] = df['fundingRate'].rolling(rolling_window).quantile(self.lower_percentile)
        
        # Dynamic Exit thresholds (e.g. 70th and 30th percentiles)
        df['fr_exit_upper'] = df['fundingRate'].rolling(rolling_window).quantile(0.70)
        df['fr_exit_lower'] = df['fundingRate'].rolling(rolling_window).quantile(0.30)
        
        # Entry Logic
        # Extreme Long leverage -> Enter SHORT
        short_cond = (df['fundingRate'] > df['fr_upper']) & (df['fundingRate'].shift(1) <= df['fr_upper'].shift(1))
        
        # Extreme Short leverage -> Enter LONG
        long_cond = (df['fundingRate'] < df['fr_lower']) & (df['fundingRate'].shift(1) >= df['fr_lower'].shift(1))
        
        df['entry_signal'] = np.select([long_cond, short_cond], [1, -1], default=0)
        
        # Dynamic Exit Logic
        # If we are SHORT, exit when funding rate drops below 70th percentile
        df['exit_short'] = df['fundingRate'] < df['fr_exit_upper']
        # If we are LONG, exit when funding rate rises above 30th percentile
        df['exit_long'] = df['fundingRate'] > df['fr_exit_lower']
        
        # Stop Loss: Extreme wide (just to prevent total wipeout)
        df['atr'] = (df['high'] - df['low']).rolling(14).mean()
        df['sl'] = np.where(df['entry_signal'] == 1, df['close'] - (df['atr'] * 10),
                   np.where(df['entry_signal'] == -1, df['close'] + (df['atr'] * 10), np.nan))
                   
        df['tp2'] = 0 
        df['time_stop_bars'] = 120 # 5 days maximum hold
        
        return df
