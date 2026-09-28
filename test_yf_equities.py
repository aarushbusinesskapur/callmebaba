import yfinance as yf
import traceback

def test_ticker(ticker, interval, period):
    print(f"\n--- Testing {ticker} ({interval}, {period}) ---")
    try:
        df = yf.download(ticker, interval=interval, period=period, progress=False)
        print(f"Success! Fetched {len(df)} rows.")
        if len(df) > 0:
            print(df.head(2))
    except Exception as e:
        print(f"FAILED. Error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()

test_ticker('BTC-USD', '1h', '5d')
test_ticker('SPY', '1d', '5d')
test_ticker('QQQ', '1h', '5d')
