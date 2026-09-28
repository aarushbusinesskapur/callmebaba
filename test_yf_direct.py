import pandas as pd
import urllib.request
import io

def get_yf_csv(ticker):
    url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1=946684800&period2=1735689600&interval=1d&events=history&includeAdjustedClose=true"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req, timeout=10)
    csv_data = res.read().decode('utf-8')
    df = pd.read_csv(io.StringIO(csv_data))
    return df

df = get_yf_csv('SPY')
print(f"SPY Data Length: {len(df)}")
print(df.head(2))
