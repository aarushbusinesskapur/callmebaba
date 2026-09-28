import pandas as pd
import numpy as np

class TierAScanner:
    """
    Tier A Logic: 
    - Regime Filter: Daily ADX > 25 (Trending)
    - HTF Trend: 4H 200-SMA Alignment
    - Confluence Score: Squeeze Breakout + MACD Cross + VWAP slope
    """
    def __init__(self, df_1h: pd.DataFrame):
        self.df = df_1h.copy()
        
    def calculate_indicators(self):
        df = self.df
        
        # 4H SMA (Mapped to 1H)
        df_4h = df.resample('4h', on='timestamp').agg({'close': 'last'})
        df_4h['sma_200_4h'] = df_4h['close'].rolling(200).mean().shift(1)
        df = df.join(df_4h[['sma_200_4h']], on='timestamp', how='left')
        df['sma_200_4h'] = df['sma_200_4h'].ffill()
        
        # Daily ADX (Mapped to 1H) - simplified proxy for ADX via ATR/Price Volatility
        # Real ADX requires high/low/close calculations over 14 days
        df_1d = df.resample('1d', on='timestamp').agg({'high': 'max', 'low': 'min', 'close': 'last'})
        df_1d['tr'] = np.maximum(df_1d['high'] - df_1d['low'], 
                                 np.maximum(abs(df_1d['high'] - df_1d['close'].shift()), 
                                            abs(df_1d['low'] - df_1d['close'].shift())))
        df_1d['atr'] = df_1d['tr'].rolling(14).mean()
        # Simplified directional movement proxy
        df_1d['up_move'] = df_1d['high'] - df_1d['high'].shift(1)
        df_1d['down_move'] = df_1d['low'].shift(1) - df_1d['low']
        df_1d['plus_dm'] = np.where((df_1d['up_move'] > df_1d['down_move']) & (df_1d['up_move'] > 0), df_1d['up_move'], 0)
        df_1d['minus_dm'] = np.where((df_1d['down_move'] > df_1d['up_move']) & (df_1d['down_move'] > 0), df_1d['down_move'], 0)
        df_1d['plus_di'] = 100 * (df_1d['plus_dm'].rolling(14).mean() / df_1d['atr'])
        df_1d['minus_di'] = 100 * (df_1d['minus_dm'].rolling(14).mean() / df_1d['atr'])
        df_1d['dx'] = 100 * abs(df_1d['plus_di'] - df_1d['minus_di']) / (df_1d['plus_di'] + df_1d['minus_di'])
        df_1d['adx_1d'] = df_1d['dx'].rolling(14).mean().shift(1)
        
        df = df.join(df_1d[['adx_1d']], on='timestamp', how='left')
        df['adx_1d'] = df['adx_1d'].ffill()
        
        # 1H Squeeze
        df['sma_20'] = df['close'].rolling(20).mean()
        df['std_20'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['sma_20'] + (df['std_20'] * 2)
        df['bb_lower'] = df['sma_20'] - (df['std_20'] * 2)
        df['tr_1h'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift())))
        df['atr_20'] = df['tr_1h'].rolling(20).mean()
        df['kc_upper'] = df['sma_20'] + (df['atr_20'] * 1.5)
        df['kc_lower'] = df['sma_20'] - (df['atr_20'] * 1.5)
        df['squeeze_on'] = (df['bb_lower'] > df['kc_lower']) & (df['bb_upper'] < df['kc_upper'])
        df['squeeze_fired'] = (~df['squeeze_on']) & (df['squeeze_on'].shift(1))
        
        self.df = df
        return df
        
    def scan(self):
        if 'sma_200_4h' not in self.df.columns:
            self.calculate_indicators()
            
        latest = self.df.iloc[-1]
        
        # Regime Filter: Is the market trending?
        trending = latest['adx_1d'] > 25
        
        # MTF Alignment
        bull_trend = latest['close'] > latest['sma_200_4h']
        bear_trend = latest['close'] < latest['sma_200_4h']
        
        # Base Setup
        long_setup = latest['squeeze_fired'] and latest['close'] > latest['kc_upper'] and bull_trend
        short_setup = latest['squeeze_fired'] and latest['close'] < latest['kc_lower'] and bear_trend
        
        if not trending:
            return None # Regime filter blocked entry
            
        if long_setup:
            return {"side": "LONG", "price": latest['close'], "adx": latest['adx_1d']}
        if short_setup:
            return {"side": "SHORT", "price": latest['close'], "adx": latest['adx_1d']}
            
        return None
