import os
import sys
import json
import ccxt
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "state.json"

# The honest, empirically tested stats for the MTF Squeeze strategy
BACKTEST_STATS = {
    "BTC/USD": {"wr": 34.65, "pf": 0.74, "trades": 101},
    "ETH/USD": {"wr": 28.44, "pf": 0.74, "trades": 109},
    "SOL/USD": {"wr": 36.45, "pf": 1.22, "trades": 107},
    "BNB/USD": {"wr": 30.28, "pf": 0.82, "trades": 109}
}

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def send_telegram_alert(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing, cannot send alert.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def fetch_kraken_tf(ex, symbol, tf):
    ohlcv = ex.fetch_ohlcv(symbol, timeframe=tf, limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.set_index('timestamp', inplace=True)
    return df

def scan_timeframe(ex, symbol, tf, htf_df):
    df = fetch_kraken_tf(ex, symbol, tf)
    df = df.iloc[:-1].copy() # Ensure we only evaluate CLOSED candles
    
    # 1. Higher Timeframe 200-SMA Mapping
    htf_df['sma_200_htf'] = htf_df['close'].rolling(200).mean().shift(1)
    df = df.join(htf_df[['sma_200_htf']], how='left')
    df['sma_200_htf'] = df['sma_200_htf'].ffill()
    
    # 2. ADX Filter
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
    
    # 3. Squeeze
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
    
    if not trending: return None
    if long_setup: return {"side": "LONG", "price": latest['close'], "adx": latest['adx'], "atr": latest['atr_20'], "htf_sma": latest['sma_200_htf']}
    if short_setup: return {"side": "SHORT", "price": latest['close'], "adx": latest['adx'], "atr": latest['atr_20'], "htf_sma": latest['sma_200_htf']}
    return None

def manage_open_trades(ex, state):
    """Check live prices of open trades to see if they hit SL or TP1."""
    resolved_assets = []
    for asset, trade in state.items():
        try:
            ticker = ex.fetch_ticker(asset)
            current_price = ticker['last']
            
            # Simple resolution logic
            if trade['side'] == 'LONG':
                if current_price <= trade['sl']:
                    print(f"[{asset}] Hit Stop Loss. Resolving trade.")
                    resolved_assets.append(asset)
                elif current_price >= trade['tp1']:
                    print(f"[{asset}] Hit Take Profit 1. Resolving trade.")
                    resolved_assets.append(asset)
            else: # SHORT
                if current_price >= trade['sl']:
                    print(f"[{asset}] Hit Stop Loss. Resolving trade.")
                    resolved_assets.append(asset)
                elif current_price <= trade['tp1']:
                    print(f"[{asset}] Hit Take Profit 1. Resolving trade.")
                    resolved_assets.append(asset)
        except Exception as e:
            print(f"Error checking status for {asset}: {e}")
            
    for asset in resolved_assets:
        del state[asset]
    return state

def main():
    print("Quant Scanner Booting...")
    now = datetime.now(timezone.utc)
    minute = now.minute
    hour = now.hour
    
    state = load_state()
    
    if not state.get("TEST_SIGNAL_LIVE_PEPE"):
        try:
            temp_ex = ccxt.kraken()
            ticker = temp_ex.fetch_ticker('PEPE/USD')
            live_price = ticker['last']
            
            atr = live_price * 0.015
            sl = live_price - (atr * 2)
            tp1 = live_price + (atr * 1.5)
            tp2 = live_price + (atr * 2.0)
            tp3 = live_price + (atr * 3.0)
            tp4 = live_price + (atr * 4.0)
            
            test_msg = "<b>🚨 TIER A (5m) SIGNAL [LIVE PRICE TEST] 🚨</b>\n\n"
            test_msg += f"<b>Asset:</b> PEPE/USD\n<b>Direction:</b> LONG\n<b>Entry:</b> ${live_price:,.8f}\n"
            test_msg += f"<b>SL:</b> ${sl:,.8f}\n<b>TP1-4:</b> ${tp1:,.8f} | ${tp2:,.8f} | ${tp3:,.8f} | ${tp4:,.8f}\n\n"
            test_msg += "<b>Motive:</b> 5m Squeeze Breakout with 1H Trend Alignment (TEST)\n"
            test_msg += f"<b>Live Chart Conf:</b> 1H > ${(live_price * 0.95):,.8f} | ADX: 35.2\n\n"
            test_msg += "<i>[Untested Asset]: No historical backtest data for PEPE/USD. Trade with caution.</i>"
            
            send_telegram_alert(test_msg)
            state["TEST_SIGNAL_LIVE_PEPE"] = True
            save_state(state)
        except Exception as e:
            print("Test signal error:", e)
        
    # ONE-TIME PING IF STATE IS COMPLETELY EMPTY (First Run)
    if not state and not os.path.exists(STATE_FILE):
        send_telegram_alert("🟢 <b>Quant Scanner Status: ONLINE</b>\n\nGitHub Actions connection established. Tracking 1 signal per coin strictly.")
    
    # Determine target timeframes
    tfs_to_scan = ['5m']
    if 10 <= minute <= 22 or 40 <= minute <= 52: tfs_to_scan.append('15m')
    elif 25 <= minute <= 37: tfs_to_scan.extend(['15m', '30m'])
    elif 55 <= minute <= 59 or 0 <= minute <= 7:
        tfs_to_scan.extend(['15m', '30m', '1h'])
        if hour % 4 == 0: tfs_to_scan.append('4h')
        
    ex = ccxt.kraken({'enableRateLimit': True})
    symbols = [
        'BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD', 'DOGE/USD', 'ADA/USD', 'SHIB/USD', 'AVAX/USD',
        'DOT/USD', 'LINK/USD', 'PEPE/USD', 'MATIC/USD', 'LTC/USD', 'BCH/USD', 'UNI/USD', 'NEAR/USD',
        'APT/USD', 'SUI/USD', 'SEI/USD', 'TIA/USD', 'INJ/USD', 'FET/USD', 'RNDR/USD', 'AR/USD',
        'ATOM/USD', 'XMR/USD', 'ETC/USD', 'FIL/USD', 'ALGO/USD', 'QNT/USD', 'VET/USD', 'ICP/USD',
        'ARB/USD', 'OP/USD', 'GRT/USD', 'MKR/USD', 'SNX/USD', 'AAVE/USD', 'SAND/USD', 'THETA/USD',
        'AXS/USD', 'MANA/USD', 'EOS/USD', 'EGLD/USD', 'FLOW/USD', 'CHZ/USD', 'GALA/USD', 'BONK/USD',
        'WIF/USD', 'FLOKI/USD', 'KAS/USD', 'RUNE/USD', 'STX/USD', 'IMX/USD', 'LDO/USD', 'MNT/USD',
        'KAVA/USD', 'MINA/USD', 'ORDI/USD', 'BLUR/USD'
    ]
    
    # Resolve any open trades that hit targets
    state = manage_open_trades(ex, state)
    
    for symbol in symbols:
        print(f"\n--- {symbol} ---")
        
        # Rule: One active signal per asset
        if symbol in state:
            print(f"ACTIVE TRADE OPEN ({state[symbol]['side']} @ ${state[symbol]['entry']:,.2f}). Skipping scans for {symbol}.")
            continue
            
        try:
            df_1h = fetch_kraken_tf(ex, symbol, '1h')
            df_1d = fetch_kraken_tf(ex, symbol, '1d')
        except: continue
            
        for tf in tfs_to_scan:
            try:
                htf_df = df_1h if tf in ['5m', '15m', '30m'] else df_1d
                signal = scan_timeframe(ex, symbol, tf, htf_df)
                
                if signal:
                    # Enforce honest win rate filter if stats exist
                    stats = BACKTEST_STATS.get(symbol)
                    if stats and stats['wr'] < 25.0:
                        print(f"Filtered out: {symbol} win rate {stats['wr']}% is below 25% threshold.")
                        break # Skip this asset entirely
                        
                    print(f"*** {tf} SIGNAL ON {symbol}: {signal['side']} ***")
                    direction, price, atr = signal['side'], signal['price'], signal['atr']
                    sl_dist, tp_dist = atr * 2, atr * 1.5
                    
                    sl = price - sl_dist if direction == "LONG" else price + sl_dist
                    tp1 = price + tp_dist if direction == "LONG" else price - tp_dist
                    tp2 = price + (tp_dist*2) if direction == "LONG" else price - (tp_dist*2)
                    tp3 = price + (tp_dist*3) if direction == "LONG" else price - (tp_dist*3)
                    tp4 = price + (tp_dist*4) if direction == "LONG" else price - (tp_dist*4)
                    
                    trend_type = "1H" if tf in ['5m', '15m', '30m'] else "1D"
                    
                    msg = f"<b>🚨 TIER A ({tf}) SIGNAL 🚨</b>\n\n"
                    msg += f"<b>Asset:</b> {symbol}\n<b>Direction:</b> {direction}\n<b>Entry:</b> ${price:,.2f}\n"
                    msg += f"<b>SL:</b> ${sl:,.2f}\n<b>TP1-4:</b> ${tp1:,.2f} | ${tp2:,.2f} | ${tp3:,.2f} | ${tp4:,.2f}\n\n"
                    msg += f"<b>Motive:</b> {tf} Squeeze Breakout with {trend_type} Trend Alignment\n"
                    msg += f"<b>Live Chart Conf:</b> {trend_type} > ${signal['htf_sma']:,.2f} | ADX: {signal['adx']:.1f}\n\n"
                    
                    # Honest Confidence Formatting
                    if tf in ['1h', '4h'] and stats:
                        status_str = "PROMOTED" if stats['pf'] > 1.0 else "REJECTED"
                        msg += f"<i>[Validated Timeframe]: Backtested {stats['trades']} trades. Win Rate: {stats['wr']}%, Profit Factor: {stats['pf']} ({status_str} in-sample).</i>"
                    elif tf in ['1h', '4h'] and not stats:
                        msg += f"<i>[Untested Asset]: No historical backtest data for {symbol}. Trade with caution.</i>"
                    else:
                        confluence_score = min(100, int((signal['adx'] / 60) * 100)) # Simple ADX strength 0-100 proxy
                        msg += f"<i>[Rule Confluence Score: {confluence_score}/100] — NOT backtested, no historical accuracy data exists yet for this timeframe.</i>"
                    
                    send_telegram_alert(msg)
                    
                    # Record in state to prevent duplicates
                    state[symbol] = {
                        "tf": tf, "side": direction, "entry": price, 
                        "sl": sl, "tp1": tp1, "timestamp": now.isoformat()
                    }
                    break # Stop scanning smaller TFs if a larger TF fired for this asset
                else:
                    print(f"{tf}: No live confirmation signal.")
            except Exception as e:
                print(f"Error processing {tf} for {symbol}: {e}")

    save_state(state)

if __name__ == "__main__":
    main()
