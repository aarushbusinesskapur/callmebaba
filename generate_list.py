import ccxt
import time
import warnings
warnings.filterwarnings('ignore')

exchange = ccxt.bybit()
print("Fetching Bybit markets and tickers...", flush=True)
markets = exchange.load_markets()
tickers = exchange.fetch_tickers()

valid_pairs = []
for symbol, ticker in tickers.items():
    if symbol.endswith('/USDT') and ':' not in symbol: # Spot USDT only
        quote_vol = ticker.get('quoteVolume', 0)
        if quote_vol and quote_vol >= 5_000_000:
            valid_pairs.append({'symbol': symbol, 'vol': quote_vol})
            
valid_pairs = sorted(valid_pairs, key=lambda x: x['vol'], reverse=True)
print(f"Found {len(valid_pairs)} pairs with > $5M daily volume.", flush=True)

final_coins = []
dropped = []

print("Validating 365-day history constraint...", flush=True)
one_year_ago = exchange.milliseconds() - (365 * 24 * 60 * 60 * 1000)

for p in valid_pairs:
    if len(final_coins) >= 60:
        break
    symbol = p['symbol']
    try:
        # fetch 1 daily bar from 1 year ago
        bars = exchange.fetch_ohlcv(symbol, '1d', since=int(one_year_ago), limit=1)
        if not bars or len(bars) == 0 or bars[0][0] > one_year_ago + (7 * 24 * 60 * 60 * 1000):
            dropped.append(symbol)
            time.sleep(0.05)
            continue
        final_coins.append(symbol)
        time.sleep(0.05)
    except Exception as e:
        dropped.append(f"{symbol} (Error)")
        time.sleep(0.05)
        
print("\n--- DROPPED COINS (< 365 Days History) ---")
print(", ".join(dropped))

print("\n--- FINAL TIERED COIN LIST ---")
print("Tier 1 (Majors) - Bybit Vol Rank 1-15:")
print(", ".join([c for c in final_coins[:15]]))
print("\nTier 2 (Mid-Caps) - Bybit Vol Rank 16-40:")
print(", ".join([c for c in final_coins[15:40]]))
print("\nTier 3 (Small-Caps/High-Vol) - Bybit Vol Rank 41-60:")
print(", ".join([c for c in final_coins[40:]]))
