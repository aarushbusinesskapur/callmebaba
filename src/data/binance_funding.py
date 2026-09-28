import os
import requests
import pandas as pd
import time
from datetime import datetime, timedelta

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

import io
import zipfile
from dateutil.relativedelta import relativedelta

def fetch_binance_funding(symbol="BTCUSDT", days=700):
    cache_file = os.path.join(CACHE_DIR, f"{symbol}_funding_{days}d.csv")
    
    if os.path.exists(cache_file):
        print(f"Loading {symbol} funding rates from cache...")
        df = pd.read_csv(cache_file)
        df['fundingTime'] = pd.to_datetime(df['fundingTime'], utc=True)
        return df
        
    print(f"Fetching historical funding rates for {symbol} from data.binance.vision...")
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Generate list of year-months to download
    current_date = start_date.replace(day=1)
    months_to_fetch = []
    while current_date <= end_date:
        months_to_fetch.append(current_date.strftime("%Y-%m"))
        current_date += relativedelta(months=1)
        
    all_dfs = []
    
    for ym in months_to_fetch:
        # data.binance.vision URL format for monthly funding rates
        url = f"https://data.binance.vision/data/futures/um/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{ym}.zip"
        print(f"Downloading {ym}...", flush=True)
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    csv_filename = z.namelist()[0]
                    with z.open(csv_filename) as f:
                        month_df = pd.read_csv(f)
                        all_dfs.append(month_df)
            else:
                print(f"Could not find monthly data for {ym} (Status {response.status_code}).")
        except Exception as e:
            print(f"Error fetching {ym}: {e}")
            
    if not all_dfs:
        print("Failed to fetch any data.")
        return pd.DataFrame()
        
    df = pd.concat(all_dfs, ignore_index=True)
    
    # Standardize columns to match our expected format
    df['fundingTime'] = pd.to_datetime(df['calc_time'], unit='ms', utc=True)
    df['fundingRate'] = df['last_funding_rate'].astype(float)
    
    df = df[['fundingTime', 'fundingRate']]
    df.drop_duplicates(subset=['fundingTime'], inplace=True)
    df.sort_values('fundingTime', inplace=True)
    
    # Filter to exact requested timeframe
    df = df[df['fundingTime'] >= pd.to_datetime(start_date, utc=True)]
    
    df.to_csv(cache_file, index=False)
    print(f"Saved {len(df)} funding rate records to cache.")
    return df

if __name__ == "__main__":
    fetch_binance_funding("BTCUSDT", 700)
    fetch_binance_funding("ETHUSDT", 700)
