import os
import sys
import time
import requests
import pandas as pd
import ccxt
import numpy as np
from datetime import datetime, timezone

# Strategy Parameters
FUND_LOOKBACK = 5760  # 240 days * 24 hours (time parity with Binance 8H 720 lookback)
BB_LEN = 100
BB_MULT = 1.5

# Symbol Mapping: CCXT to Kraken REST
SYMBOL_MAP = {
    'BTC/USD:USD': 'pf_xbtusd',
    'ETH/USD:USD': 'pf_ethusd',
    'SOL/USD:USD': 'pf_solusd',
    'BNB/USD:USD': 'pf_bnbusd'
}

def fetch_historical_funding(kraken_sym):
    url = f"https://futures.kraken.com/derivatives/api/v4/historicalfundingrates?symbol={kraken_sym}"
    res = requests.get(url)
    if res.status_code != 200:
        print(f"[{kraken_sym}] Error fetching historical funding: {res.status_code}")
        return pd.Series(dtype=float)
        
    rates = res.json().get('rates', [])
    if not rates:
        return pd.Series(dtype=float)
        
    df = pd.DataFrame(rates)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.set_index('timestamp').sort_index()
    
    # Use relativeFundingRate to match Binance percentage logic
    if 'relativeFundingRate' in df.columns:
        return df['relativeFundingRate']
    return df['fundingRate']

def fetch_live_funding():
    url = "https://futures.kraken.com/derivatives/api/v3/tickers"
    res = requests.get(url)
    if res.status_code != 200:
        return {}
    
    tickers = res.json().get('tickers', [])
    funding_map = {}
    for t in tickers:
        sym = t['symbol'].lower()
        if 'relativeFundingRate' in t:
            rate = t['relativeFundingRate']
        else:
            # Manually calculate relative rate: Absolute Funding / Index Price
            abs_rate = t.get('fundingRate', 0)
            idx_price = t.get('indexPrice', 1)
            rate = abs_rate / idx_price if idx_price else 0
        funding_map[sym] = rate
    return funding_map

def run_tier_b_live(log_file="tier_b_live_log.txt"):
    found_signal = False
    found_anomaly = False
    timestamp_str = datetime.now(timezone.utc).isoformat()
    
    output_lines = []
    output_lines.append(f"\n==================================================")
    output_lines.append(f"TIER B (PHASE 5) LIVE EXECUTOR - KRAKEN FUTURES")
    output_lines.append(f"Timestamp: {timestamp_str}")
    output_lines.append(f"==================================================")
    
    ex = ccxt.krakenfutures({'enableRateLimit': True})
    live_funding = fetch_live_funding()
    
    for ccxt_sym, kraken_sym in SYMBOL_MAP.items():
        output_lines.append(f"\n--- {ccxt_sym} ---")
        try:
            # 1. Fetch live OHLCV
            ohlcv = ex.fetch_ohlcv(ccxt_sym, timeframe='1h', limit=BB_LEN)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            current_close = df.iloc[-1]['close']
            prev_close = df.iloc[-2]['close']
            output_lines.append(f"Current Price:   ${current_close:,.2f}")
            
            # 2. Fetch Historical Funding for Z-Score Mean/Std
            hist_rates = fetch_historical_funding(kraken_sym)
            if len(hist_rates) < FUND_LOOKBACK:
                output_lines.append(f"Status:          INSUFFICIENT FUNDING DATA ({len(hist_rates)} < {FUND_LOOKBACK})")
                continue
                
            # Take the last N periods for the rolling window
            window = hist_rates.iloc[-FUND_LOOKBACK:]
            f_mean = window.mean()
            f_std = window.std()
            
            # 3. Get exact Live Funding Rate
            current_funding = live_funding.get(kraken_sym, window.iloc[-1])
            if f_std == 0:
                f_z = 0
            else:
                f_z = (current_funding - f_mean) / f_std
                
            # --- ANOMALY CHECK ---
            if f_z > 10 or f_z < -10:
                output_lines.append(f"[ANOMALY] Implausible Z-Score Detected: {f_z:.4f}")
                found_anomaly = True
                
            # 4. Calculate Bollinger Bands & Compression
            df['bb_mid'] = df['close'].rolling(20).mean()
            df['bb_std'] = df['close'].rolling(20).std()
            df['bb_upper'] = df['bb_mid'] + BB_MULT * df['bb_std']
            df['bb_lower'] = df['bb_mid'] - BB_MULT * df['bb_std']
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
            
            current_width = df.iloc[-1]['bb_width']
            prev_width = df.iloc[-2]['bb_width']
            
            width_rank_current = df['bb_width'].rank(pct=True).iloc[-1]
            width_rank_prev = df['bb_width'].rank(pct=True).iloc[-2]
            
            was_compressed = width_rank_prev < 0.2
            
            output_lines.append(f"Funding Z-Score: {f_z:.4f} (Mean: {f_mean:.6f}, Std: {f_std:.6f})")
            output_lines.append(f"Compression:     Rank {width_rank_current:.4f} (Prev: {width_rank_prev:.4f} -> {'COMPRESSED' if was_compressed else 'EXPANDING'})")
            
            # 5. Evaluate Triggers
            bb_upper_prev = df.iloc[-2]['bb_upper']
            bb_lower_prev = df.iloc[-2]['bb_lower']
            bb_upper_curr = df.iloc[-1]['bb_upper']
            bb_lower_curr = df.iloc[-1]['bb_lower']
            
            long_cond = (f_z < -1.5) and (current_close > bb_upper_curr) and (prev_close <= bb_upper_prev) and was_compressed
            short_cond = (f_z > 1.0) and (current_close < bb_lower_curr) and (prev_close >= bb_lower_prev) and was_compressed
            
            if long_cond:
                output_lines.append(f"Status:          >>> LONG SIGNAL TRIGGERED <<<")
                found_signal = True
            elif short_cond:
                output_lines.append(f"Status:          >>> SHORT SIGNAL TRIGGERED <<<")
                found_signal = True
            else:
                output_lines.append(f"Status:          No signal triggered.")
                
        except Exception as e:
            output_lines.append(f"Error processing {ccxt_sym}: {str(e)}")
            
    # Print to console and append to file
    final_output = "\n".join(output_lines)
    print(final_output)
    with open(log_file, "a") as f:
        f.write(final_output + "\n")
        
    return found_signal, found_anomaly

if __name__ == "__main__":
    run_tier_b_live()
