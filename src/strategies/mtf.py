import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy

class MTFSqueezeStrategy(BaseStrategy):
    """
    Multi-Timeframe Confirmation Strategy.
    Entry: 1H Volatility Squeeze Breakout.
    Filter: 4H 200-period Simple Moving Average (Trend Alignment).
    Exit: 2.0x ATR Trailing Stop.
    """
    
    def __init__(self, strategy_id: str, version: str, parameters: dict):
        super().__init__(strategy_id, version, parameters)
        self.bb_period = self.parameters.get("bb_period", 20)
        self.bb_std = self.parameters.get("bb_std", 2.0)
        self.kc_period = self.parameters.get("kc_period", 20)
        self.kc_mult = self.parameters.get("kc_mult", 1.5)
        
        self.mtf_period = self.parameters.get("mtf_period", 200) # 4H 200-SMA
        
        self.parameters["use_trailing_stop"] = True
        self.parameters["trailing_atr_multiplier"] = self.parameters.get("trailing_atr_multiplier", 2.0)
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # 1. Calculate Higher Timeframe Filter (4H)
        # Resample 1H to 4H
        df.set_index('timestamp', inplace=True)
        df_4h = df.resample('4h').agg({'close': 'last'})
        
        # 200-SMA on 4H
        df_4h['htf_sma'] = df_4h['close'].rolling(self.mtf_period).mean()
        
        # Shift HTF by 1 bar to prevent lookahead bias (we can only use the 4H SMA after the 4H bar closes)
        df_4h['htf_sma'] = df_4h['htf_sma'].shift(1)
        
        # Rejoin to 1H timeframe and forward fill
        df = df.join(df_4h[['htf_sma']], how='left')
        df['htf_sma'] = df['htf_sma'].ffill()
        df.reset_index(inplace=True)
        
        # 2. Calculate 1H Squeeze Logic
        df['sma'] = df['close'].rolling(self.bb_period).mean()
        df['std'] = df['close'].rolling(self.bb_period).std()
        df['upper_bb'] = df['sma'] + (df['std'] * self.bb_std)
        df['lower_bb'] = df['sma'] - (df['std'] * self.bb_std)
        
        df['tr'] = np.maximum(df['high'] - df['low'], 
                              np.maximum(abs(df['high'] - df['close'].shift()), 
                                         abs(df['low'] - df['close'].shift())))
        df['atr'] = df['tr'].rolling(self.kc_period).mean()
        df['upper_kc'] = df['sma'] + (df['atr'] * self.kc_mult)
        df['lower_kc'] = df['sma'] - (df['atr'] * self.kc_mult)
        
        # Squeeze condition: BB is entirely inside KC
        df['squeeze_on'] = (df['lower_bb'] > df['lower_kc']) & (df['upper_bb'] < df['upper_kc'])
        df['squeeze_off'] = (df['lower_bb'] < df['lower_kc']) & (df['upper_bb'] > df['upper_kc'])
        
        # Has the squeeze just fired?
        squeeze_fired = (~df['squeeze_on']) & (df['squeeze_on'].shift(1))
        
        # 3. Combine Entry + HTF Filter
        # Long: Squeeze fired, price > upper KC, AND 1H Close > 4H 200-SMA
        long_cond = squeeze_fired & (df['close'] > df['upper_kc']) & (df['close'] > df['htf_sma'])
        
        # Short: Squeeze fired, price < lower KC, AND 1H Close < 4H 200-SMA
        short_cond = squeeze_fired & (df['close'] < df['lower_kc']) & (df['close'] < df['htf_sma'])
        
        df['entry_signal'] = np.select([long_cond, short_cond], [1, -1], default=0)
        
        # Initial invalidation stop (used only until trailing stop takes over)
        df['sl'] = np.where(df['entry_signal'] == 1, 
                            df['lower_kc'] - (df['atr'] * 0.5),
                   np.where(df['entry_signal'] == -1, 
                            df['upper_kc'] + (df['atr'] * 0.5), 
                            np.nan))
                            
        df['sl'] = df['sl'].ffill()
        df['atr'] = df['atr'].bfill()
        
        return df
