import pandas_datareader.data as web
import pandas as pd
try:
    df = web.DataReader('SPY.US', 'stooq')
    print("Stooq SPY Data fetched!")
    print(df.head())
except Exception as e:
    print(f"Stooq failed: {e}")
