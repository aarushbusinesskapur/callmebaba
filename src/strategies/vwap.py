import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy

class DailyVWAPReversionStrategy(BaseStrategy):
    """
    Implements the Daily Anchored VWAP Mean Reversion thesis.
    Anchors VWAP at 00:00 UTC each day. 
    Enters on extreme deviations (e.g., 2 standard deviations)
    Targets a return to the VWAP line.
    """
    
    def __init__(self, strategy_id: str, version: str, parameters: dict):
        super().__init__(strategy_id, version, parameters)
        self.std_multiplier = self.parameters.get("std_multiplier", 2.0)
        self.sl_atr_buffer = self.parameters.get("sl_atr_buffer", 0.5)
        
        self.parameters["use_trailing_stop"] = False
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df['date'] = df['timestamp'].dt.date
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3.0
        df['pv'] = df['typical_price'] * df['volume']
        df['pv2'] = df['volume'] * (df['typical_price'] ** 2)
        
        # Calculate Daily VWAP
        df['cum_pv'] = df.groupby('date')['pv'].cumsum()
        df['cum_vol'] = df.groupby('date')['volume'].cumsum()
        df['vwap'] = df['cum_pv'] / df['cum_vol']
        
        # Calculate Volume-Weighted Standard Deviation
        df['cum_pv2'] = df.groupby('date')['pv2'].cumsum()
        df['vwap_var'] = (df['cum_pv2'] / df['cum_vol']) - (df['vwap'] ** 2)
        df['vwap_var'] = df['vwap_var'].clip(lower=0)
        df['vwap_std'] = np.sqrt(df['vwap_var'])
        
        # VWAP Bands
        df['upper_band'] = df['vwap'] + (df['vwap_std'] * self.std_multiplier)
        df['lower_band'] = df['vwap'] - (df['vwap_std'] * self.std_multiplier)
        
        # Track hour of the day (0 to 23)
        df['hour'] = df['timestamp'].dt.hour
        
        # Entry Logic (Mean Reversion)
        # We require hour >= 3 to allow bands to widen naturally after the 00:00 reset
        short_cond = (df['close'] > df['upper_band']) & (df['close'].shift(1) <= df['upper_band'].shift(1)) & (df['hour'] >= 3)
        
        # Long when closing below Lower Band
        long_cond = (df['close'] < df['lower_band']) & (df['close'].shift(1) >= df['lower_band'].shift(1)) & (df['hour'] >= 3)
        
        df['entry_signal'] = np.select([long_cond, short_cond], [1, -1], default=0)
        
        # End of Day Exit (Close out positions before the VWAP reset at 00:00)
        # Exiting at the close of the 23:00 bar (which is 23:59:59)
        eod_exit = df['hour'] == 23
        df['exit_long'] = eod_exit
        df['exit_short'] = eod_exit
        
        # ATR for Stop Loss buffering
        df['atr'] = (df['high'] - df['low']).rolling(14).mean().bfill()
        
        # Target = VWAP line at the time of entry
        # Stop Loss = Band extreme + ATR buffer
        df['dynamic_tp'] = df['vwap']
        
        df['sl'] = np.where(df['entry_signal'] == 1, 
                            df['lower_band'] - (df['atr'] * self.sl_atr_buffer),
                   np.where(df['entry_signal'] == -1, 
                            df['upper_band'] + (df['atr'] * self.sl_atr_buffer), 
                            np.nan))
                            
        # Ensure no accidental NaNs in sl when entry_signal is active
        df['sl'] = df['sl'].ffill()
                   
        return df

class DailyVWAPContinuationStrategy(BaseStrategy):
    """
    Implements the Daily Anchored VWAP Trend Continuation thesis.
    Anchors VWAP at 00:00 UTC each day.
    Enters on breakout of the 2 SD bands (Buy above upper, Short below lower).
    Exits via an ATR-based trailing stop.
    """
    
    def __init__(self, strategy_id: str, version: str, parameters: dict):
        super().__init__(strategy_id, version, parameters)
        self.std_multiplier = self.parameters.get("std_multiplier", 2.0)
        self.sl_atr_buffer = self.parameters.get("sl_atr_buffer", 0.5)
        
        # We MUST enable trailing stop in Backtester
        self.parameters["use_trailing_stop"] = True
        self.parameters["trailing_atr_multiplier"] = self.parameters.get("trailing_atr_multiplier", 2.0)
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df['date'] = df['timestamp'].dt.date
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3.0
        df['pv'] = df['typical_price'] * df['volume']
        df['pv2'] = df['volume'] * (df['typical_price'] ** 2)
        
        # Calculate Daily VWAP
        df['cum_pv'] = df.groupby('date')['pv'].cumsum()
        df['cum_vol'] = df.groupby('date')['volume'].cumsum()
        df['vwap'] = df['cum_pv'] / df['cum_vol']
        
        # Calculate Volume-Weighted Standard Deviation
        df['cum_pv2'] = df.groupby('date')['pv2'].cumsum()
        df['vwap_var'] = (df['cum_pv2'] / df['cum_vol']) - (df['vwap'] ** 2)
        df['vwap_var'] = df['vwap_var'].clip(lower=0)
        df['vwap_std'] = np.sqrt(df['vwap_var'])
        
        # VWAP Bands
        df['upper_band'] = df['vwap'] + (df['vwap_std'] * self.std_multiplier)
        df['lower_band'] = df['vwap'] - (df['vwap_std'] * self.std_multiplier)
        
        df['hour'] = df['timestamp'].dt.hour
        
        # Entry Logic (Trend Continuation)
        # We require hour >= 3 to allow bands to widen naturally after the 00:00 reset
        # Long when closing ABOVE Upper Band (Breakout)
        long_cond = (df['close'] > df['upper_band']) & (df['close'].shift(1) <= df['upper_band'].shift(1)) & (df['hour'] >= 3)
        
        # Short when closing BELOW Lower Band (Breakdown)
        short_cond = (df['close'] < df['lower_band']) & (df['close'].shift(1) >= df['lower_band'].shift(1)) & (df['hour'] >= 3)
        
        df['entry_signal'] = np.select([long_cond, short_cond], [1, -1], default=0)
        
        # No EOD exit unless requested. Momentum strategies often hold for days.
        # The user said "let winners run". So we remove the EOD time stop.
        
        df['atr'] = (df['high'] - df['low']).rolling(14).mean().bfill()
        
        # Initial Stop Loss = back inside the band + ATR buffer (invalidation)
        # If long, the SL is below the upper band.
        # If short, the SL is above the lower band.
        df['sl'] = np.where(df['entry_signal'] == 1, 
                            df['upper_band'] - (df['atr'] * self.sl_atr_buffer),
                   np.where(df['entry_signal'] == -1, 
                            df['lower_band'] + (df['atr'] * self.sl_atr_buffer), 
                            np.nan))
                            
        df['sl'] = df['sl'].ffill()
        
        # The trailing stop will take over after entry via the Backtester's use_trailing_stop logic,
        # moving up if price goes our way by trailing_atr_multiplier * ATR from highest high.
        
        return df
