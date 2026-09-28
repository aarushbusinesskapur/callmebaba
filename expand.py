import sys

with open('github_scanner.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Expand symbols
old_symbols = "symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD']"
new_symbols = '''symbols = [
        'BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD', 'DOGE/USD', 'ADA/USD', 'SHIB/USD', 'AVAX/USD',
        'DOT/USD', 'LINK/USD', 'PEPE/USD', 'MATIC/USD', 'LTC/USD', 'BCH/USD', 'UNI/USD', 'NEAR/USD',
        'APT/USD', 'SUI/USD', 'SEI/USD', 'TIA/USD', 'INJ/USD', 'FET/USD', 'RNDR/USD', 'AR/USD',
        'ATOM/USD', 'XMR/USD', 'ETC/USD', 'FIL/USD', 'ALGO/USD', 'QNT/USD', 'VET/USD', 'ICP/USD',
        'ARB/USD', 'OP/USD', 'GRT/USD', 'MKR/USD', 'SNX/USD', 'AAVE/USD', 'SAND/USD', 'THETA/USD',
        'AXS/USD', 'MANA/USD', 'EOS/USD', 'EGLD/USD', 'FLOW/USD', 'CHZ/USD', 'GALA/USD', 'BONK/USD',
        'WIF/USD', 'FLOKI/USD', 'KAS/USD', 'RUNE/USD', 'STX/USD', 'IMX/USD', 'LDO/USD', 'MNT/USD',
        'KAVA/USD', 'MINA/USD', 'ORDI/USD', 'BLUR/USD'
    ]'''
code = code.replace(old_symbols, new_symbols)

# 2. Fix stats KeyError
old_stats = '''                    # Enforce honest win rate filter (>= 25%)
                    stats = BACKTEST_STATS[symbol]
                    if stats['wr'] < 25.0:'''
new_stats = '''                    # Enforce honest win rate filter if stats exist
                    stats = BACKTEST_STATS.get(symbol)
                    if stats and stats['wr'] < 25.0:'''
code = code.replace(old_stats, new_stats)

# 3. Fix message formatting
old_msg = '''                    # Honest Confidence Formatting
                    if tf in ['1h', '4h']:
                        status_str = "PROMOTED" if stats['pf'] > 1.0 else "REJECTED"
                        msg += f"<i>[Validated Timeframe]: Backtested {stats['trades']} trades. Win Rate: {stats['wr']}%, Profit Factor: {stats['pf']} ({status_str} in-sample).</i>"
                    else:'''
new_msg = '''                    # Honest Confidence Formatting
                    if tf in ['1h', '4h'] and stats:
                        status_str = "PROMOTED" if stats['pf'] > 1.0 else "REJECTED"
                        msg += f"<i>[Validated Timeframe]: Backtested {stats['trades']} trades. Win Rate: {stats['wr']}%, Profit Factor: {stats['pf']} ({status_str} in-sample).</i>"
                    elif tf in ['1h', '4h'] and not stats:
                        msg += f"<i>[Untested Asset]: No historical backtest data for {symbol}. Trade with caution.</i>"
                    else:'''
code = code.replace(old_msg, new_msg)

with open('github_scanner.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Expansion applied!")
