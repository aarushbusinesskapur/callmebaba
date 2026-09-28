import pandas as pd
import numpy as np
from src.strategies.indicators import Indicators
from typing import Dict, Any

class RegimeClassifier:
    """Classifies the current market regime independently using ADX and Volatility compression."""
    
    @staticmethod
    def vectorize_regime(df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies ADX and Bollinger/Keltner squeeze calculations to the entire dataframe.
        """
        df = df.copy()
        
        # 1. Primary Signal: ADX
        df['adx'] = Indicators.adx(df['high'], df['low'], df['close'], 14)
        
        # 2. Secondary Signal: Volatility Squeeze (Bollinger inside Keltner)
        # Squeeze indicates low volatility compression phase (potential breakout building)
        bb_upper, bb_lower = Indicators.bollinger_bands(df['close'], 20, 2.0)
        kc_upper, kc_lower = Indicators.keltner_channels(df['high'], df['low'], df['close'], 20, 14, 1.5)
        
        # Squeeze is "on" when Bollinger Bands are completely inside Keltner Channels
        df['squeeze_on'] = (bb_upper < kc_upper) & (bb_lower > kc_lower)
        
        # 3. Define the regimes based on ADX thresholds
        conditions = [
            (df['adx'] > 25),
            (df['adx'] < 20),
            (df['adx'] >= 20) & (df['adx'] <= 25)
        ]
        choices = ['TRENDING', 'CHOPPY/RANGING', 'TRANSITIONAL']
        # If NaN (e.g. beginning of dataframe), label UNCERTAIN
        df['regime_state'] = np.select(conditions, choices, default='UNCERTAIN')
        
        # Append squeeze flag to string representation
        df['regime'] = np.where(df['squeeze_on'], df['regime_state'] + " (SQUEEZE)", df['regime_state'])
        return df

    @staticmethod
    def detect_regime(df: pd.DataFrame) -> str:
        """Determines the CURRENT market regime string for the scanner."""
        if len(df) < 50:
            return "uncertain/mixed"
        df_reg = RegimeClassifier.vectorize_regime(df)
        return df_reg['regime'].iloc[-1]
