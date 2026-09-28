import pandas as pd
import urllib.request
import io

API_KEY = "7873877dad9f4f7fb1750fa5ef5eaa86"

def get_twelvedata(symbol, interval, outputsize=5000):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={API_KEY}&outputsize={outputsize}&format=csv"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req, timeout=15)
    csv_data = res.read().decode('utf-8')
    
    if "code" in csv_data and "message" in csv_data and "status" in csv_data:
        print(f"API Error for {symbol} {interval}: {csv_data}")
        return pd.DataFrame()
        
    df = pd.read_csv(io.StringIO(csv_data), sep=';')
    
    if len(df) > 0 and 'datetime' in df.columns:
        df.rename(columns={'datetime': 'timestamp'}, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df = df.sort_index() # Twelve Data returns descending by default
    
    return df

print("Fetching SPY (1day) from Twelve Data...")
spy = get_twelvedata('SPY', '1day')
print(f"SPY fetched: {len(spy)} rows.")
if len(spy) > 0: print(spy.head(2))

print("\nFetching QQQ (1h) from Twelve Data...")
qqq = get_twelvedata('QQQ', '1h')
print(f"QQQ fetched: {len(qqq)} rows.")
if len(qqq) > 0: print(qqq.head(2))

