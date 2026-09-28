import ccxt
import time
import warnings
warnings.filterwarnings('ignore')

exchanges = {
    'Binance (Global)': ccxt.binance(),
    'Binance (US)': ccxt.binanceus(),
    'KuCoin': ccxt.kucoin(),
    'Bybit': ccxt.bybit(),
    'OKX': ccxt.okx(),
    'Gate.io': ccxt.gate(),
    'MEXC': ccxt.mexc(),
    'Kraken': ccxt.kraken()
}

print("Testing Crypto API Reachability from this environment...")
for name, ex in exchanges.items():
    try:
        ex.timeout = 5000
        markets = ex.load_markets()
        print(f"[OK] {name}: REACHABLE ({len(markets)} pairs available)")
    except Exception as e:
        print(f"[FAIL] {name}: BLOCKED/TIMEOUT")
