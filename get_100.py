import ccxt
exchange = ccxt.bybit({'options': {'defaultType': 'spot'}})
exchange.load_markets()
tickers = exchange.fetch_tickers()
valid_pairs = []
for symbol, ticker in tickers.items():
    if symbol.endswith('/USDT') and ':' not in symbol:
        qv = ticker.get('quoteVolume')
        if qv is not None and float(qv) > 1000000:
            valid_pairs.append({'symbol': symbol, 'vol': float(qv)})
valid_pairs = sorted(valid_pairs, key=lambda x: x['vol'], reverse=True)[:100]
print([p['symbol'] for p in valid_pairs])
