import os
import pandas as pd
import requests

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")

def compare_stats():
    kraken_symbols = {
        'BTCUSDT': 'pf_xbtusd',
        'ETHUSDT': 'pf_ethusd',
        'SOLUSDT': 'pf_solusd',
        'BNBUSDT': 'pf_bnbusd'
    }
    
    print(f"{'Asset':<10} | {'Exchange':<10} | {'Interval':<10} | {'Mean':<12} | {'Std Dev':<12} | {'Min':<12} | {'Max':<12}")
    print("-" * 90)
    
    for binance_sym, kraken_sym in kraken_symbols.items():
        # BINANCE DATA
        binance_path = os.path.join(CACHE_DIR, f"{binance_sym}_funding_700d.csv")
        b_interval = "Unknown"
        if os.path.exists(binance_path):
            df_b = pd.read_csv(binance_path)
            if 'fundingTime' in df_b.columns:
                df_b['timestamp'] = pd.to_datetime(df_b['fundingTime'], unit='ms', utc=True)
            elif 'timestamp' in df_b.columns:
                df_b['timestamp'] = pd.to_datetime(df_b['timestamp'], utc=True)
            
            df_b = df_b.sort_values('timestamp')
            # Calculate interval
            diffs = df_b['timestamp'].diff().dropna()
            mode_diff = diffs.mode()
            if not mode_diff.empty:
                b_interval = f"{mode_diff[0].seconds // 3600}H"
                
            rates = df_b['fundingRate']
            print(f"{binance_sym:<10} | {'Binance':<10} | {b_interval:<10} | {rates.mean():.8f} | {rates.std():.8f} | {rates.min():.8f} | {rates.max():.8f}")
            
        # KRAKEN DATA
        url = f"https://futures.kraken.com/derivatives/api/v4/historicalfundingrates?symbol={kraken_sym}"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json().get('rates', [])
            if data:
                df_k = pd.DataFrame(data)
                df_k['timestamp'] = pd.to_datetime(df_k['timestamp'], utc=True)
                df_k = df_k.sort_values('timestamp')
                
                # Calculate interval
                diffs = df_k['timestamp'].diff().dropna()
                mode_diff = diffs.mode()
                k_interval = "Unknown"
                if not mode_diff.empty:
                    k_interval = f"{mode_diff[0].seconds // 3600}H"
                    
                if 'relativeFundingRate' in df_k.columns:
                    rates = df_k['relativeFundingRate']
                else:
                    rates = df_k['fundingRate']
                print(f"{binance_sym:<10} | {'Kraken':<10} | {k_interval:<10} | {rates.mean():.8f} | {rates.std():.8f} | {rates.min():.8f} | {rates.max():.8f}")
        print("-" * 90)

if __name__ == "__main__":
    compare_stats()
