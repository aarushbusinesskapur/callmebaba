import time
import ccxt
import pandas as pd
import numpy as np
import requests
import os
import sys

TELEGRAM_TOKEN = "8900720623:AAEsfrm2d7sLPWPx47S4yRXLxsNlVqdGKdM"
TELEGRAM_CHAT_ID = "745457169"
SIGNAL_COUNT_FILE = "15m_signals_count.txt"

def get_signal_count():
    if os.path.exists(SIGNAL_COUNT_FILE):
        with open(SIGNAL_COUNT_FILE, "r") as f:
            try:
                return int(f.read().strip())
            except:
                return 0
    return 0

def increment_signal_count():
    count = get_signal_count() + 1
    with open(SIGNAL_COUNT_FILE, "w") as f:
        f.write(str(count))
    return count

def send_telegram_alert(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def fetch_multi_tf_kraken(symbol):
    ex = ccxt.kraken({'enableRateLimit': True})
    
    ohlcv_15m = ex.fetch_ohlcv(symbol, timeframe='15m')
    df_15m = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms', utc=True)
    df_15m.set_index('timestamp', inplace=True)
    
    ohlcv_1h = ex.fetch_ohlcv(symbol, timeframe='1h')
    df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'], unit='ms', utc=True)
    df_1h.set_index('timestamp', inplace=True)
    
    ohlcv_1d = ex.fetch_ohlcv(symbol, timeframe='1d')
    df_1d = pd.DataFrame(ohlcv_1d, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_1d['timestamp'] = pd.to_datetime(df_1d['timestamp'], unit='ms', utc=True)
    df_1d.set_index('timestamp', inplace=True)
    
    return df_15m, df_1h, df_1d

class Scanner15m:
    def __init__(self, df_15m, df_1h, df_1d):
        self.df = df_15m.copy()
        self.df_1h = df_1h.copy()
        self.df_1d = df_1d.copy()
        
    def calculate_indicators(self):
        df = self.df
        
        # 1H SMA
        self.df_1h['sma_200_1h'] = self.df_1h['close'].rolling(200).mean().shift(1)
        df = df.join(self.df_1h[['sma_200_1h']], how='left')
        df['sma_200_1h'] = df['sma_200_1h'].ffill()
        
        # Daily ADX
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
        
        # 15m Squeeze
        df['sma_20'] = df['close'].rolling(20).mean()
        df['std_20'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['sma_20'] + (df['std_20'] * 2)
        df['bb_lower'] = df['sma_20'] - (df['std_20'] * 2)
        df['tr_15m'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift())))
        df['atr_20'] = df['tr_15m'].rolling(20).mean()
        df['kc_upper'] = df['sma_20'] + (df['atr_20'] * 1.5)
        df['kc_lower'] = df['sma_20'] - (df['atr_20'] * 1.5)
        df['squeeze_on'] = (df['bb_lower'] > df['kc_lower']) & (df['bb_upper'] < df['kc_upper'])
        df['squeeze_fired'] = (~df['squeeze_on']) & (df['squeeze_on'].shift(1))
        
        # We need a stop loss / take profit distance based on ATR
        df['atr_sl'] = df['atr_20']
        
        self.df = df
        return df

    def scan(self):
        latest = self.df.iloc[-1]
        
        # Require stronger ADX for 15m given higher noise
        trending = latest['adx_1d'] > 28
        
        bull_trend = latest['close'] > latest['sma_200_1h']
        bear_trend = latest['close'] < latest['sma_200_1h']
        
        long_setup = latest['squeeze_fired'] and latest['close'] > latest['kc_upper'] and bull_trend
        short_setup = latest['squeeze_fired'] and latest['close'] < latest['kc_lower'] and bear_trend
        
        if not trending:
            return None
            
        if long_setup:
            return {"side": "LONG", "price": latest['close'], "adx": latest['adx_1d'], "atr": latest['atr_sl']}
        if short_setup:
            return {"side": "SHORT", "price": latest['close'], "adx": latest['adx_1d'], "atr": latest['atr_sl']}
            
        return None

def run_tier_a_15m():
    if get_signal_count() >= 5:
        print("Signal limit reached (5). Halting 15m scanner.")
        sys.exit(0)
        
    print("Running Tier A 15m Scanner (UNTESTED TIMEFRAME) on Live Kraken Data...")
    symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD']
    
    for symbol in symbols:
        try:
            df_15m, df_1h, df_1d = fetch_multi_tf_kraken(symbol)
        except Exception as e:
            print(f"[{symbol}] Fetch error: {e}")
            continue
            
        scanner = Scanner15m(df_15m, df_1h, df_1d)
        scanner.calculate_indicators()
        
        latest = scanner.df.iloc[-1]
        
        print(f"\n--- {symbol} (15m — untested timeframe) ---")
        print(f"Current Price:  ${latest['close']:,.2f}")
        print(f"Regime (ADX):   {latest['adx_1d']:.2f} (Trending if > 28)")
        
        trend = "BULLISH" if latest['close'] > latest['sma_200_1h'] else "BEARISH"
        print(f"HTF Trend 1H:   {trend} (200-SMA = ${latest['sma_200_1h']:,.2f})")
        print(f"Squeeze State:  {'COMPRESSED' if latest['squeeze_on'] else 'EXPANDING'}")
        
        if symbol == 'BTC/USD':
            print("--- FORCING MOCK SIGNAL ON BTC FOR USER VERIFICATION ---")
            signal = {"side": "LONG", "price": latest['close'], "adx": latest['adx_1d'], "atr": latest['atr_sl']}
        else:
            signal = scanner.scan()
            
        if signal:
            print(f"*** ACTIONABLE SIGNAL: {signal['side']} ***")
            
            # Formatting Telegram Message
            direction = signal['side']
            price = signal['price']
            atr = signal['atr']
            
            sl_dist = atr * 2
            tp_dist = atr * 1.5
            
            sl = price - sl_dist if direction == "LONG" else price + sl_dist
            tp1 = price + tp_dist if direction == "LONG" else price - tp_dist
            tp2 = price + (tp_dist*2) if direction == "LONG" else price - (tp_dist*2)
            tp3 = price + (tp_dist*3) if direction == "LONG" else price - (tp_dist*3)
            
            msg = f"<b>🚨 TIER A (15m — Untested Timeframe) SIGNAL 🚨</b>\n\n"
            msg += f"<b>Asset:</b> {symbol}\n"
            msg += f"<b>Direction:</b> {direction}\n"
            msg += f"<b>Entry:</b> ${price:,.2f}\n"
            msg += f"<b>SL:</b> ${sl:,.2f}\n"
            msg += f"<b>TP1:</b> ${tp1:,.2f}\n"
            msg += f"<b>TP2:</b> ${tp2:,.2f}\n"
            msg += f"<b>TP3:</b> ${tp3:,.2f}\n\n"
            msg += f"<i>Reason: 15m Squeeze Breakout + 1H Trend Alignment (ADX {signal['adx']:.1f})</i>"
            
            send_telegram_alert(msg)
            count = increment_signal_count()
            print(f"Telegram alert sent. (Signal {count}/5)")
            
            if count >= 5:
                print("Signal limit reached (5). Halting 15m scanner.")
                sys.exit(0)
        else:
            print("Status:         No confluence signal triggered.")

if __name__ == "__main__":
    run_tier_a_15m()
