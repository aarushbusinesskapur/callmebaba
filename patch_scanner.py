import ccxt
import re

# Get top 100 spot pairs from Binance.US (fast and reliable)
ex = ccxt.binanceus()
markets = ex.load_markets()
tickers = ex.fetch_tickers()
valid = []
for sym, t in tickers.items():
    if sym.endswith('/USDT'):
        valid.append({'sym': sym, 'vol': float(t.get('quoteVolume', 0) or 0)})
        
valid = sorted(valid, key=lambda x: x['vol'], reverse=True)[:100]
top_100 = [x['sym'] for x in valid]

# Read master_scanner.py
with open('master_scanner.py', 'r') as f:
    content = f.read()

# Replace TICKERS list
# We find the TICKERS = [...] block and replace it
import ast
# We'll just use regex to replace the TICKERS block safely
new_tickers_str = "TICKERS = [\n    " + ", ".join([f'"{s}"' for s in top_100]) + "\n]"
content = re.sub(r'TICKERS = \[[^\]]+\]', new_tickers_str, content)

# Replace 1d timeframe with 1h for the main scan
content = content.replace("timeframe='1d'", "timeframe='1h'")
content = content.replace("timeframe=\"1d\"", "timeframe='1h'")

with open('master_scanner.py', 'w') as f:
    f.write(content)

print(f"Patched master_scanner.py with {len(top_100)} coins and 1h timeframe.")
