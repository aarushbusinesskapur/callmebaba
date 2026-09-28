import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy

class BollingerMeanReversionStrategy(BaseStrategy):
    """
    Bollinger Bands Mean Reversion.
    Enters Long when price crosses below Lower Band.
    Enters Short when price crosses above Upper Band.
    Exits at the Mean (20-period SMA).
    """
    
    def __init__(self, strategy_id: str, version: str, parameters: dict):
        super().__init__(strategy_id, version, parameters)
        self.period = self.parameters.get("period", 20)
        self.std_dev = self.parameters.get("std_dev", 2.0)
        self.sl_atr_buffer = self.parameters.get("sl_atr_buffer", 1.0)
        
        self.parameters["use_trailing_stop"] = False
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df['sma'] = df['close'].rolling(self.period).mean()
        df['std'] = df['close'].rolling(self.period).std()
        
        df['upper_band'] = df['sma'] + (df['std'] * self.std_dev)
        df['lower_band'] = df['sma'] - (df['std'] * self.std_dev)
        
        long_cond = (df['close'] < df['lower_band']) & (df['close'].shift(1) >= df['lower_band'].shift(1))
        short_cond = (df['close'] > df['upper_band']) & (df['close'].shift(1) <= df['upper_band'].shift(1))
        
        df['entry_signal'] = np.select([long_cond, short_cond], [1, -1], default=0)
        
        df['atr'] = (df['high'] - df['low']).rolling(14).mean().bfill()
        
        df['sl'] = np.where(df['entry_signal'] == 1, 
                            df['lower_band'] - (df['atr'] * self.sl_atr_buffer),
                   np.where(df['entry_signal'] == -1, 
                            df['upper_band'] + (df['atr'] * self.sl_atr_buffer), 
                            np.nan))
                            
        df['sl'] = df['sl'].ffill()
        df['dynamic_tp'] = df['sma']
        
        return df
