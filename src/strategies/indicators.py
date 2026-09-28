import pandas as pd
import numpy as np

class Indicators:
    @staticmethod
    def sma(series, period):
        return series.rolling(window=period).mean()

    @staticmethod
    def ema(series, period):
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rma(series, period):
        """Wilder's Smoothing (Running Moving Average)"""
        return series.ewm(alpha=1/period, adjust=False).mean()

    @staticmethod
    def rsi(series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(high, low, close, period=14):
        tr = pd.Series(np.maximum((high - low), np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1)))))
        return Indicators.rma(tr, period)

    @staticmethod
    def adx(high, low, close, period=14):
        """Calculates Average Directional Index (ADX) using Wilder's smoothing."""
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0))
        minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0))
        
        tr = pd.Series(np.maximum((high - low), np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1)))))
        
        atr = Indicators.rma(tr, period)
        # Avoid division by zero
        atr = atr.replace(0, np.nan)
        
        plus_di = 100 * (Indicators.rma(plus_dm, period) / atr)
        minus_di = 100 * (Indicators.rma(minus_dm, period) / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = Indicators.rma(dx, period)
        return adx
        
    @staticmethod
    def bollinger_bands(close, period=20, std_dev=2):
        sma = close.rolling(period).mean()
        std = close.rolling(period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, lower

    @staticmethod
    def keltner_channels(high, low, close, period=20, atr_period=10, multiplier=1.5):
        ema = Indicators.ema(close, period)
        atr = Indicators.atr(high, low, close, atr_period)
        upper = ema + (multiplier * atr)
        lower = ema - (multiplier * atr)
        return upper, lower
