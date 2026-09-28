import ccxt
import time
import pandas as pd
import numpy as np
import concurrent.futures
import warnings
warnings.filterwarnings('ignore')

from skills.base import BacktestConfig
from skills.triple_rsi_mean_reversion import TripleRSI_MeanReversion
from skills.bb_rsi_mean_reversion import BB_RSI_MeanReversion
from skills.vwap_mean_reversion import VWAP_MeanReversion
from skills.opening_range_breakout_pro import OpeningRangeBreakout_Pro
from skills.high_probability_confluence import HighProbability_Confluence

print("Generating Programmatic Coin List from Bybit (Live Validation)...", flush=True)
exchange = ccxt.bybit({'options': {'defaultType': 'spot'}})
markets = exchange.load_markets()
tickers = exchange.fetch_tickers()

valid_pairs = []
for symbol, ticker in tickers.items():
    market = markets.get(symbol, {})
    if market.get('spot') and symbol.endswith('/USDT'):
        qv = ticker.get('quoteVolume')
        if qv is not None and float(qv) >= 1_000_000:
            valid_pairs.append({'symbol': symbol, 'vol': float(qv)})
            
valid_pairs = sorted(valid_pairs, key=lambda x: x['vol'], reverse=True)
print(f"Found {len(valid_pairs)} pairs with > $1M daily volume.", flush=True)

final_coins = []
dropped_coins = []
one_year_ago = exchange.milliseconds() - (365 * 24 * 60 * 60 * 1000)

for p in valid_pairs:
    if len(final_coins) >= 60:
        break
    symbol = p['symbol']
    try:
        bars = exchange.fetch_ohlcv(symbol, '1d', since=int(one_year_ago), limit=1)
        if not bars or len(bars) == 0 or bars[0][0] > one_year_ago + (7 * 24 * 60 * 60 * 1000):
            dropped_coins.append(symbol)
        else:
            final_coins.append(symbol)
    except Exception:
        dropped_coins.append(symbol)
    time.sleep(0.05)

tier1 = final_coins[:15]
tier2 = final_coins[15:40]
tier3 = final_coins[40:60]

def fetch_data(symbol):
    ex = ccxt.bybit({'options': {'defaultType': 'spot'}})
    bars_1d = ex.fetch_ohlcv(symbol, '1d', limit=1000)
    df_1d = pd.DataFrame(bars_1d, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_1d['timestamp'] = pd.to_datetime(df_1d['timestamp'], unit='ms')
    df_1d.set_index('timestamp', inplace=True)
    
    all_15m = []
    now = ex.milliseconds()
    start = now - (5000 * 15 * 60 * 1000)
    for _ in range(5):
        try:
            b = ex.fetch_ohlcv(symbol, '15m', since=int(start), limit=1000)
            if not b: break
            all_15m.extend(b)
            start = b[-1][0] + 1
            time.sleep(0.1)
        except:
            break
            
    df_15m = pd.DataFrame(all_15m[-5000:], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
    df_15m.set_index('timestamp', inplace=True)
    
    return symbol, df_1d.astype(float), df_15m.astype(float)

print("Fetching 5000 bars per coin (Parallelized)...", flush=True)
coin_data = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(fetch_data, final_coins)
    for sym, d1, d15 in results:
        coin_data[sym] = (d1, d15)
        
print("Data Fetched. Running Backtests...", flush=True)

cfg_is = BacktestConfig(split_ratio=0.0)
cfg_oos = BacktestConfig(split_ratio=0.7)

s1 = TripleRSI_MeanReversion()
s2 = BB_RSI_MeanReversion()
s3 = VWAP_MeanReversion()
s4 = OpeningRangeBreakout_Pro(); s4.market_open_time = "00:00"; s4.cutoff_time = "02:30"
s5 = HighProbability_Confluence()

def run_skill(skill, df, is_cfg, oos_cfg):
    try:
        r_is = skill.backtest(df, is_cfg)
        r_oos = skill.backtest(df, oos_cfg)
        return r_is, r_oos
    except:
        return None, None
        
def agg_tier(tier_coins, skill, timeframe='1d'):
    total_is_trades = 0
    total_oos_trades = 0
    is_pf_list = []
    oos_pf_list = []
    
    for c in tier_coins:
        if c not in coin_data: continue
        d1, d15 = coin_data[c]
        df = d1 if timeframe == '1d' else d15
        if len(df) < 50: continue
        
        r_is, r_oos = run_skill(skill, df, cfg_is, cfg_oos)
        if r_is and r_is.total_trades > 0:
            total_is_trades += r_is.total_trades
            is_pf_list.append(r_is.profit_factor)
        if r_oos and r_oos.total_trades > 0:
            total_oos_trades += r_oos.total_trades
            oos_pf_list.append(r_oos.profit_factor)
            
    avg_is_pf = np.mean(is_pf_list) if is_pf_list else 0
    avg_oos_pf = np.mean(oos_pf_list) if oos_pf_list else 0
    
    thin_is = " [THIN]" if total_is_trades < 30 else ""
    thin_oos = " [THIN]" if total_oos_trades < 30 else ""
    
    return f"IS [{total_is_trades}T{thin_is} | Avg PF {avg_is_pf:.2f}] || OOS [{total_oos_trades}T{thin_oos} | Avg PF {avg_oos_pf:.2f}]"

print(f"\n--- DROPPED COINS (< 365 Days History) ---")
print(", ".join(dropped_coins[:15]) + (f" ... and {len(dropped_coins)-15} more" if len(dropped_coins) > 15 else ""))

print("\n--- FINAL TIERED COIN LIST (Top 60) ---")
print(f"Tier 1 (Majors): {', '.join(tier1)}")
print(f"Tier 2 (Mid-Caps): {', '.join(tier2[:7])}... ({len(tier2)} total)")
print(f"Tier 3 (Memecoins/Small): {', '.join(tier3[:7])}... ({len(tier3)} total)")

print("\n===================== 60-COIN SWEEP RESULTS =====================")
for skill_name, skill_obj, tf in [
    ("Skill 1 (Triple RSI)", s1, '1d'),
    ("Skill 2 (BB RSI)", s2, '1d'),
    ("Skill 5 (Confluence)", s5, '1d'),
    ("Skill 3 (VWAP)", s3, '15m'),
    ("Skill 4 (ORB Pro - UTC)", s4, '15m')
]:
    print(f"\n{skill_name}:")
    print(f"  Tier 1 (Majors):   {agg_tier(tier1, skill_obj, tf)}")
    print(f"  Tier 2 (Mid-Caps): {agg_tier(tier2, skill_obj, tf)}")
    print(f"  Tier 3 (Memecoins):{agg_tier(tier3, skill_obj, tf)}")
print("=================================================================")
