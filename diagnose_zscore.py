import pandas as pd
import requests

def fetch_historical_funding(kraken_sym):
    url = f"https://futures.kraken.com/derivatives/api/v4/historicalfundingrates?symbol={kraken_sym}"
    res = requests.get(url)
    rates = res.json().get('rates', [])
    df = pd.DataFrame(rates)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.set_index('timestamp').sort_index()
    return df

def fetch_live_funding():
    url = "https://futures.kraken.com/derivatives/api/v3/tickers"
    res = requests.get(url)
    tickers = res.json().get('tickers', [])
    funding_map = {}
    for t in tickers:
        sym = t['symbol'].lower()
        funding_map[sym] = {
            'relative': t.get('relativeFundingRate'),
            'absolute': t.get('fundingRate')
        }
    return funding_map

def diagnose_zscore():
    print("--- 1. UNITS MISMATCH CHECK ---")
    live = fetch_live_funding()
    live_bnb = live.get('pf_bnbusd', {})
    
    df_hist = fetch_historical_funding('pf_bnbusd')
    hist_last_rel = df_hist['relativeFundingRate'].iloc[-1]
    hist_last_abs = df_hist['fundingRate'].iloc[-1]
    
    print("BNB Live relativeFundingRate:   ", live_bnb['relative'])
    print("BNB Live absolute fundingRate:  ", live_bnb['absolute'])
    print("BNB Hist relativeFundingRate:   ", hist_last_rel)
    print("BNB Hist absolute fundingRate:  ", hist_last_abs)
    
    print("\n--- 2. NEAR-ZERO DIVISION CHECK ---")
    fund_lookback = 5760
    window = df_hist['relativeFundingRate'].iloc[-fund_lookback:]
    f_mean = window.mean()
    f_std = window.std()
    print("BNB Historical Window Mean:     ", f_mean)
    print("BNB Historical Window Std Dev:  ", f_std)
    
    # Calculate what tier_b_live did
    current_live = live_bnb['relative']
    if current_live is None:
        current_live = live_bnb['absolute'] # Fallback used in script
        print("WARNING: 'relativeFundingRate' was missing in live, fell back to absolute!")
        
    f_z = (current_live - f_mean) / f_std
    print(f"Calculated Z-Score using Live:  {f_z}")
    
    print("\n--- 3. OCTOBER 10 CASCADE CHECK ---")
    # October 10 cascade for BTC
    df_btc = fetch_historical_funding('pf_xbtusd')
    target_time = pd.to_datetime('2025-10-10 22:00:00+00:00')
    
    if target_time in df_btc.index:
        idx_pos = df_btc.index.get_loc(target_time)
        window_btc = df_btc['relativeFundingRate'].iloc[idx_pos - fund_lookback : idx_pos]
        btc_mean = window_btc.mean()
        btc_std = window_btc.std()
        btc_current = df_btc['relativeFundingRate'].iloc[idx_pos]
        
        btc_z = (btc_current - btc_mean) / btc_std
        print("BTC Oct 10 Cascade Z-Score:     ", btc_z)
        print("  Current value:                ", btc_current)
        print("  Window Mean:                  ", btc_mean)
        print("  Window Std Dev:               ", btc_std)

if __name__ == "__main__":
    diagnose_zscore()
