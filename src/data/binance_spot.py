import os
import io
import zipfile
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_binance_spot_klines(symbol="BTCUSDT", interval="1h", days=700):
    cache_file = os.path.join(CACHE_DIR, f"{symbol}_spot_{interval}_{days}d.csv")
    
    if os.path.exists(cache_file):
        print(f"Loading {symbol} {interval} spot data from cache...")
        df = pd.read_csv(cache_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        return df
        
    print(f"Fetching historical spot OHLCV for {symbol} from data.binance.vision...")
    
    # We use timezone-aware datetime for UTC now
    end_date = datetime.now(pd.Timestamp.utcnow().tzinfo)
    start_date = end_date - timedelta(days=days)
    
    current_date = start_date.replace(day=1)
    months_to_fetch = []
    while current_date <= end_date:
        months_to_fetch.append(current_date.strftime("%Y-%m"))
        current_date += relativedelta(months=1)
        
    all_dfs = []
    
    for ym in months_to_fetch:
        url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{ym}.zip"
        print(f"Downloading {ym}...", flush=True)
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    csv_filename = z.namelist()[0]
                    with z.open(csv_filename) as f:
                        # Binance kline headers are not included in the CSV
                        cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'num_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore']
                        month_df = pd.read_csv(f, names=cols, header=None)
                        all_dfs.append(month_df)
            else:
                print(f"Could not find monthly data for {ym} (Status {response.status_code}).")
        except Exception as e:
            print(f"Error fetching {ym}: {e}")
            
    if not all_dfs:
        print("Failed to fetch any data.")
        return pd.DataFrame()
        
    df = pd.concat(all_dfs, ignore_index=True)
    
    # Binance recently switched some historical data from ms to us.
    # If the timestamp > 1e14, it's in microseconds, otherwise milliseconds.
    df['timestamp'] = pd.to_numeric(df['timestamp'])
    df['timestamp'] = np.where(df['timestamp'] > 1e14, 
                               pd.to_datetime(df['timestamp'], unit='us', utc=True), 
                               pd.to_datetime(df['timestamp'], unit='ms', utc=True))
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
        
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df.drop_duplicates(subset=['timestamp'], inplace=True)
    df.sort_values('timestamp', inplace=True)
    
    # Filter to requested timeframe
    df = df[df['timestamp'] >= start_date]
    
    df.to_csv(cache_file, index=False)
    print(f"Saved {len(df)} spot records to cache.")
    return df

if __name__ == "__main__":
    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    for asset in assets:
        fetch_binance_spot_klines(asset, "1h", 700)
