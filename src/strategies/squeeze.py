import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy
from src.strategies.indicators import Indicators

class VolatilitySqueezeStrategy(BaseStrategy):
    """
    Implements the Volatility Squeeze Breakout Thesis.
    Thesis: Markets alternate between volatility compression and expansion. 
    Entering on the breakout of a severe compression (with volume and structural confirmation)
    allows us to catch fat-tail momentum moves using an ATR trailing stop.
    """
    
    def __init__(self, strategy_id: str, version: str, parameters: dict):
        super().__init__(strategy_id, version, parameters)
        self.bb_period = self.parameters.get("bb_period", 20)
        self.bb_std = self.parameters.get("bb_std", 2.0)
        self.kc_period = self.parameters.get("kc_period", 20)
        self.kc_atr_period = self.parameters.get("kc_atr_period", 14)
        self.kc_mult = self.parameters.get("kc_mult", 1.5)
        self.vol_period = self.parameters.get("vol_period", 20)
        self.vol_mult = self.parameters.get("vol_mult", 1.5)
        # Required by backtester for ATR trailing stop
        self.parameters["use_trailing_stop"] = True
        self.parameters["trailing_atr_multiplier"] = 2.0
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # 1. Volatility Bands
        bb_upper, bb_lower = Indicators.bollinger_bands(df['close'], self.bb_period, self.bb_std)
        kc_upper, kc_lower = Indicators.keltner_channels(df['high'], df['low'], df['close'], self.kc_period, self.kc_atr_period, self.kc_mult)
        df['atr'] = Indicators.atr(df['high'], df['low'], df['close'], 14)
        
        # Squeeze definition: Bollinger Bands fully inside Keltner Channels
        df['squeeze_on'] = (bb_upper < kc_upper) & (bb_lower > kc_lower)
        
        # 2. Volume Expansion Filter
        vol_sma = Indicators.sma(df['volume'], self.vol_period)
        df['vol_expansion'] = df['volume'] > (vol_sma * self.vol_mult)
        
        # 3. Trigger Condition (The Breakout)
        # Squeeze was ON in the previous bar, but is OFF in the current bar
        squeeze_fired = (df['squeeze_on'].shift(1) == True) & (df['squeeze_on'] == False)
        
        # Directional Confirmation: Must CLOSE outside the Keltner Channel (not just wick)
        long_breakout = squeeze_fired & (df['close'] > kc_upper) & df['vol_expansion']
        short_breakout = squeeze_fired & (df['close'] < kc_lower) & df['vol_expansion']
        
        # Generate final signals
        conditions = [long_breakout, short_breakout]
        choices = [1, -1] # 1 for Long, -1 for Short
        df['entry_signal'] = np.select(conditions, choices, default=0)
        
        return df

class FailedBreakoutFadeStrategy(BaseStrategy):
    """
    Implements the Failed Breakout Mean Reversion Thesis.
    If a Volatility Squeeze fires and breaks out with volume, but price reverses 
    back inside the Keltner Channel within N bars, we fade the breakout (trade the opposite direction)
    targeting a mean reversion back to the 20 SMA.
    """
    
    def __init__(self, strategy_id: str, version: str, parameters: dict):
        super().__init__(strategy_id, version, parameters)
        self.bb_period = self.parameters.get("bb_period", 20)
        self.bb_std = self.parameters.get("bb_std", 2.0)
        self.kc_period = self.parameters.get("kc_period", 20)
        self.kc_atr_period = self.parameters.get("kc_atr_period", 14)
        self.kc_mult = self.parameters.get("kc_mult", 1.5)
        self.vol_period = self.parameters.get("vol_period", 20)
        self.vol_mult = self.parameters.get("vol_mult", 1.5)
        self.lookback_n = self.parameters.get("lookback_n", 4)
        
        # Turn off ATR trailing stop, this is a fixed mean-reversion target trade
        self.parameters["use_trailing_stop"] = False
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        bb_upper, bb_lower = Indicators.bollinger_bands(df['close'], self.bb_period, self.bb_std)
        kc_upper, kc_lower = Indicators.keltner_channels(df['high'], df['low'], df['close'], self.kc_period, self.kc_atr_period, self.kc_mult)
        df['atr'] = Indicators.atr(df['high'], df['low'], df['close'], 14)
        sma20 = Indicators.sma(df['close'], self.bb_period)
        
        df['squeeze_on'] = (bb_upper < kc_upper) & (bb_lower > kc_lower)
        
        vol_sma = Indicators.sma(df['volume'], self.vol_period)
        
        # Bypass volume filter if data is missing/flat (like Forex)
        df['vol_expansion'] = np.where(df['volume'].sum() == 0, True, df['volume'] > (vol_sma * self.vol_mult))
        
        squeeze_fired = (df['squeeze_on'].shift(1) == True) & (df['squeeze_on'] == False)
        
        # Raw breakouts
        long_breakout = squeeze_fired & (df['close'] > kc_upper) & df['vol_expansion']
        short_breakout = squeeze_fired & (df['close'] < kc_lower) & df['vol_expansion']
        
        # Check if a breakout happened in the last N bars
        # Convert boolean series to int before rolling sum
        recent_long_bo = long_breakout.shift(1).fillna(False).astype(int).rolling(self.lookback_n).sum() > 0
        recent_short_bo = short_breakout.shift(1).fillna(False).astype(int).rolling(self.lookback_n).sum() > 0
        
        # Reversion Triggers
        # Failed Long: A recent long breakout happened, but current close falls back BELOW upper KC.
        # We also enforce that the PREVIOUS bar was still above KC, to trigger exactly on the reversion bar.
        fell_back_in = (df['close'].shift(1) > kc_upper.shift(1)) & (df['close'] < kc_upper)
        failed_long = recent_long_bo & fell_back_in
        
        # Failed Short: A recent short breakout happened, but current close climbs back ABOVE lower KC.
        climbed_back_in = (df['close'].shift(1) < kc_lower.shift(1)) & (df['close'] > kc_lower)
        failed_short = recent_short_bo & climbed_back_in
        
        # Enter SHORT if long failed. Enter LONG if short failed.
        df['entry_signal'] = np.select([failed_short, failed_long], [1, -1], default=0)
        
        # Dynamic Stop Loss parameters
        sl_type = self.parameters.get("sl_type", "extreme")
        tp_type = self.parameters.get("tp_type", "sma")
        rr_ratio = self.parameters.get("rr_ratio", 1.5)
        
        lowest_low_n = df['low'].rolling(self.lookback_n).min()
        highest_high_n = df['high'].rolling(self.lookback_n).max()
        
        lowest_close_n = df['close'].rolling(self.lookback_n).min()
        highest_close_n = df['close'].rolling(self.lookback_n).max()
        
        # Calculate SL based on variant
        if sl_type == "tight":
            # Tighter stop: breakout candle's close +/- 0.25 ATR
            long_sl = lowest_close_n - (0.25 * df['atr'])
            short_sl = highest_close_n + (0.25 * df['atr'])
        else: # "extreme" (original)
            # Breakout extreme wick +/- 0.5 ATR
            long_sl = lowest_low_n - (0.5 * df['atr'])
            short_sl = highest_high_n + (0.5 * df['atr'])
            
        df['sl'] = np.where(df['entry_signal'] == 1, long_sl,
                   np.where(df['entry_signal'] == -1, short_sl, np.nan))
                   
        # Calculate TP based on variant
        if tp_type == "fixed_rr":
            # Fixed 1.5:1 Risk:Reward based on stop distance
            risk_dist = abs(df['close'] - df['sl'])
            reward = risk_dist * rr_ratio
            long_tp = df['close'] + reward
            short_tp = df['close'] - reward
            df['tp2'] = np.where(df['entry_signal'] == 1, long_tp,
                        np.where(df['entry_signal'] == -1, short_tp, np.nan))
        else: # "sma" (original)
            df['tp2'] = sma20
        
        return df
