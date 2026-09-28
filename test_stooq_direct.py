import pandas as pd
import urllib.request
import io

def get_stooq(ticker):
    url = f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req, timeout=10)
    csv_data = res.read().decode('utf-8')
    df = pd.read_csv(io.StringIO(csv_data))
    return df

print("Fetching SPY from Stooq...")
df = get_stooq('spy')
print(f"Fetched {len(df)} rows.")
if len(df) > 0:
    print(df.tail(2))
