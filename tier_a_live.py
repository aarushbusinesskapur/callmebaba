import time
import ccxt
import pandas as pd
from src.core.tier_a_scanner import TierAScanner

def fetch_multi_tf_kraken(symbol):
    ex = ccxt.kraken({'enableRateLimit': True})
    
    # Fetch 1H candles (returns 720 bars = 30 days)
    ohlcv_1h = ex.fetch_ohlcv(symbol, timeframe='1h')
    df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'], unit='ms', utc=True)
    df_1h.set_index('timestamp', inplace=True)
    
    # Fetch 4H candles (returns 720 bars = 120 days)
    ohlcv_4h = ex.fetch_ohlcv(symbol, timeframe='4h')
    df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_4h['timestamp'] = pd.to_datetime(df_4h['timestamp'], unit='ms', utc=True)
    df_4h.set_index('timestamp', inplace=True)
    
    # Fetch 1D candles (returns 720 bars = 2 years)
    ohlcv_1d = ex.fetch_ohlcv(symbol, timeframe='1d')
    df_1d = pd.DataFrame(ohlcv_1d, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_1d['timestamp'] = pd.to_datetime(df_1d['timestamp'], unit='ms', utc=True)
    df_1d.set_index('timestamp', inplace=True)
    
    return df_1h, df_4h, df_1d

class FastTierAScanner(TierAScanner):
    def __init__(self, df_1h, df_4h, df_1d):
        self.df = df_1h.copy()
        self.df_4h = df_4h.copy()
        self.df_1d = df_1d.copy()
        
    def calculate_indicators(self):
        df = self.df
        
        # 4H SMA (Pre-calculated on 4H dataframe to bypass the 800h limit on 1H data)
        self.df_4h['sma_200_4h'] = self.df_4h['close'].rolling(200).mean().shift(1)
        df = df.join(self.df_4h[['sma_200_4h']], how='left')
        df['sma_200_4h'] = df['sma_200_4h'].ffill()
        
        # Daily ADX (Pre-calculated on 1D dataframe)
        import numpy as np
        df_1d = self.df_1d
        df_1d['tr'] = np.maximum(df_1d['high'] - df_1d['low'], 
                                 np.maximum(abs(df_1d['high'] - df_1d['close'].shift()), 
                                            abs(df_1d['low'] - df_1d['close'].shift())))
        df_1d['atr'] = df_1d['tr'].rolling(14).mean()
        df_1d['up_move'] = df_1d['high'] - df_1d['high'].shift(1)
        df_1d['down_move'] = df_1d['low'].shift(1) - df_1d['low']
        df_1d['plus_dm'] = np.where((df_1d['up_move'] > df_1d['down_move']) & (df_1d['up_move'] > 0), df_1d['up_move'], 0)
        df_1d['minus_dm'] = np.where((df_1d['down_move'] > df_1d['up_move']) & (df_1d['down_move'] > 0), df_1d['down_move'], 0)
        df_1d['plus_di'] = 100 * (df_1d['plus_dm'].rolling(14).mean() / df_1d['atr'])
        df_1d['minus_di'] = 100 * (df_1d['minus_dm'].rolling(14).mean() / df_1d['atr'])
        df_1d['dx'] = 100 * abs(df_1d['plus_di'] - df_1d['minus_di']) / (df_1d['plus_di'] + df_1d['minus_di'])
        df_1d['adx_1d'] = df_1d['dx'].rolling(14).mean().shift(1)
        
        df = df.join(df_1d[['adx_1d']], how='left')
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

def run_tier_a_live():
    print("Running Tier A Scanner on Live Kraken Data...")
    symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD']
    
    for symbol in symbols:
        try:
            df_1h, df_4h, df_1d = fetch_multi_tf_kraken(symbol)
        except Exception as e:
            print(f"[{symbol}] Fetch error: {e}")
            continue
            
        scanner = FastTierAScanner(df_1h, df_4h, df_1d)
        df_indicators = scanner.calculate_indicators()
        latest = df_indicators.iloc[-1]
        
        print(f"\n--- {symbol} ---")
        print(f"Current Price:  ${latest['close']:,.2f}")
        print(f"Regime (ADX):   {latest['adx_1d']:.2f} (Trending if > 25)")
        
        trend = "BULLISH" if latest['close'] > latest['sma_200_4h'] else "BEARISH"
        print(f"HTF Trend 4H:   {trend} (200-SMA = ${latest['sma_200_4h']:,.2f})")
        print(f"Squeeze State:  {'COMPRESSED' if latest['squeeze_on'] else 'EXPANDING'}")
        
        signal = scanner.scan()
        if signal:
            print(f"🔥 **ACTIONABLE SIGNAL: {signal['side']}** 🔥")
        else:
            print("Status:         No confluence signal triggered.")

if __name__ == "__main__":
    run_tier_a_live()
