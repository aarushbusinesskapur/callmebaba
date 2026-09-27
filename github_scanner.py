import os
import sys
import time
import ccxt
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timezone

# Read secure tokens from GitHub Actions Environment Variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("FATAL ERROR: Telegram credentials not found in environment variables.")
    sys.exit(1)

def send_telegram_alert(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"Failed to send Telegram alert: {res.text}")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def fetch_kraken_tf(ex, symbol, tf):
    ohlcv = ex.fetch_ohlcv(symbol, timeframe=tf, limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.set_index('timestamp', inplace=True)
    return df

def scan_timeframe(ex, symbol, tf, htf_df):
    """
    tf: '15m', '30m', '1h', '4h'
    htf_df: Higher Timeframe DataFrame used for 200-SMA
    """
    df = fetch_kraken_tf(ex, symbol, tf)
    
    # Ensure we are evaluating the latest fully CLOSED candle
    # CCXT returns the currently open (forming) candle as the last row, so we drop it.
    df = df.iloc[:-1].copy()
    
    # 1. Higher Timeframe 200-SMA Mapping
    htf_df['sma_200_htf'] = htf_df['close'].rolling(200).mean().shift(1)
    df = df.join(htf_df[['sma_200_htf']], how='left')
    df['sma_200_htf'] = df['sma_200_htf'].ffill()
    
    # 2. ADX Calculation directly on this timeframe (simplified proxy)
    df['tr'] = np.maximum(df['high'] - df['low'], 
                             np.maximum(abs(df['high'] - df['close'].shift()), 
                                        abs(df['low'] - df['close'].shift())))
    df['atr'] = df['tr'].rolling(14).mean()
    df['up_move'] = df['high'] - df['high'].shift(1)
    df['down_move'] = df['low'].shift(1) - df['low']
    df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
    df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
    df['plus_di'] = 100 * (df['plus_dm'].rolling(14).mean() / df['atr'])
    df['minus_di'] = 100 * (df['minus_dm'].rolling(14).mean() / df['atr'])
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].rolling(14).mean().shift(1)
    
    # 3. Squeeze Calculation
    df['sma_20'] = df['close'].rolling(20).mean()
    df['std_20'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['sma_20'] + (df['std_20'] * 2)
    df['bb_lower'] = df['sma_20'] - (df['std_20'] * 2)
    df['atr_20'] = df['tr'].rolling(20).mean()
    df['kc_upper'] = df['sma_20'] + (df['atr_20'] * 1.5)
    df['kc_lower'] = df['sma_20'] - (df['atr_20'] * 1.5)
    df['squeeze_on'] = (df['bb_lower'] > df['kc_lower']) & (df['bb_upper'] < df['kc_upper'])
    df['squeeze_fired'] = (~df['squeeze_on']) & (df['squeeze_on'].shift(1))
    
    latest = df.iloc[-1]
    
    trending = latest['adx'] > 25
    bull_trend = latest['close'] > latest['sma_200_htf']
    bear_trend = latest['close'] < latest['sma_200_htf']
    
    long_setup = latest['squeeze_fired'] and latest['close'] > latest['kc_upper'] and bull_trend
    short_setup = latest['squeeze_fired'] and latest['close'] < latest['kc_lower'] and bear_trend
    
    if not trending:
        return None
        
    if long_setup:
        return {"side": "LONG", "price": latest['close'], "adx": latest['adx'], "atr": latest['atr_20'], "htf_sma": latest['sma_200_htf']}
    if short_setup:
        return {"side": "SHORT", "price": latest['close'], "adx": latest['adx'], "atr": latest['atr_20'], "htf_sma": latest['sma_200_htf']}
        
    return None

def main():
    print("Starting Multi-Timeframe Scanner on GitHub Actions...")
    
    now = datetime.now(timezone.utc)
    minute = now.minute
    hour = now.hour
    
    # Determine which timeframes just closed and need scanning
    tfs_to_scan = []
    
    # Allow a 5-minute buffer since GitHub actions cron might start a few minutes late
    if 10 <= minute <= 20 or 40 <= minute <= 50:
        tfs_to_scan.append('15m')
    elif 25 <= minute <= 35:
        tfs_to_scan.extend(['15m', '30m'])
    elif 55 <= minute <= 59 or 0 <= minute <= 5:
        tfs_to_scan.extend(['15m', '30m', '1h'])
        if hour % 4 == 0:
            tfs_to_scan.append('4h')
            
    if not tfs_to_scan:
        print(f"Current UTC time {now.strftime('%H:%M')} does not align with a candle close. Exiting.")
        sys.exit(0)
        
    print(f"Triggered at {now.strftime('%H:%M')} UTC. Scanning timeframes: {tfs_to_scan}")
    
    ex = ccxt.kraken({'enableRateLimit': True})
    symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD']
    
    for symbol in symbols:
        print(f"\n--- {symbol} ---")
        
        # Pre-fetch the HTF anchor charts to avoid redundant calls
        # 15m and 30m use 1H as HTF. 1H and 4H use 1D as HTF.
        try:
            df_1h = fetch_kraken_tf(ex, symbol, '1h')
            df_1d = fetch_kraken_tf(ex, symbol, '1d')
        except Exception as e:
            print(f"Failed to fetch HTF data for {symbol}: {e}")
            continue
            
        for tf in tfs_to_scan:
            try:
                # Assign HTF anchor
                htf_df = df_1h if tf in ['15m', '30m'] else df_1d
                
                signal = scan_timeframe(ex, symbol, tf, htf_df)
                
                if signal:
                    print(f"*** {tf} SIGNAL ON {symbol}: {signal['side']} ***")
                    
                    # Logic Validation Labeling
                    if tf in ['1h', '4h']:
                        validation_label = "Validated timeframe — tested this session"
                    else:
                        validation_label = "Untested timeframe — new, unvalidated logic"
                        
                    direction = signal['side']
                    price = signal['price']
                    atr = signal['atr']
                    
                    sl_dist = atr * 2
                    tp_dist = atr * 1.5
                    
                    sl = price - sl_dist if direction == "LONG" else price + sl_dist
                    tp1 = price + tp_dist if direction == "LONG" else price - tp_dist
                    tp2 = price + (tp_dist*2) if direction == "LONG" else price - (tp_dist*2)
                    tp3 = price + (tp_dist*3) if direction == "LONG" else price - (tp_dist*3)
                    tp4 = price + (tp_dist*4) if direction == "LONG" else price - (tp_dist*4)
                    
                    trend_type = "1H" if tf in ['15m', '30m'] else "1D"
                    
                    msg = f"<b>🚨 TIER A ({tf}) SIGNAL 🚨</b>\n"
                    msg += f"<i>{validation_label}</i>\n\n"
                    msg += f"<b>Asset:</b> {symbol}\n"
                    msg += f"<b>Direction:</b> {direction}\n"
                    msg += f"<b>Entry:</b> ${price:,.2f}\n"
                    msg += f"<b>SL:</b> ${sl:,.2f}\n"
                    msg += f"<b>TP1:</b> ${tp1:,.2f}\n"
                    msg += f"<b>TP2:</b> ${tp2:,.2f}\n"
                    msg += f"<b>TP3:</b> ${tp3:,.2f}\n"
                    msg += f"<b>TP4:</b> ${tp4:,.2f}\n\n"
                    msg += f"<i>Trend Conf: {trend_type} > ${signal['htf_sma']:,.2f} | ADX: {signal['adx']:.1f}</i>\n"
                    msg += f"<i>Motive: {tf} Squeeze Breakout + {trend_type} Trend Alignment</i>"
                    
                    send_telegram_alert(msg)
                else:
                    print(f"{tf}: No confluence signal.")
            except Exception as e:
                print(f"Failed to process {tf} for {symbol}: {e}")

if __name__ == "__main__":
    main()
