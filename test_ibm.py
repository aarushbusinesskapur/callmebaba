import pandas as pd
import urllib.request
import io
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&outputsize=full&apikey=demo&datatype=csv'
res = urllib.request.urlopen(url, timeout=10)
csv = res.read().decode('utf-8')
df = pd.read_csv(io.StringIO(csv))
print(f"IBM length: {len(df)}")
