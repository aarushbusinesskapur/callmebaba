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

# Using the EXACT coins from the live filtration earlier
tier1 = ["BTC/USDT", "ETH/USDT", "QNT/USDT", "NEAR/USDT", "SOL/USDT", "USDC/USDT", "XRP/USDT", "SUI/USDT", "WLD/USDT", "HYPE/USDT", "ENA/USDT", "GRAM/USDT", "RLUSD/USDT", "MNT/USDT", "ONDO/USDT"]
tier2 = ["PUMP/USDT", "DOGE/USDT", "AVAX/USDT", "XPL/USDT", "UNI/USDT", "LTC/USDT", "VVV/USDT", "ZETA/USDT", "W/USDT", "RENDER/USDT", "CGPT/USDT", "MKR/USDT", "TAO/USDT", "STX/USDT", "TON/USDT", "AAVE/USDT", "KAS/USDT", "LINK/USDT", "RNDR/USDT", "APT/USDT", "INJ/USDT", "OP/USDT", "ARB/USDT", "TIA/USDT", "DOT/USDT"]
tier3 = ["ZRO/USDT", "BNB/USDT", "FLOCK/USDT", "TRUMP/USDT", "XDC/USDT", "ZIG/USDT", "ETHFI/USDT", "FTM/USDT", "BCH/USDT", "CORE/USDT", "ORDI/USDT", "GALA/USDT", "SEI/USDT", "BLUR/USDT", "PEPE/USDT", "WIF/USDT", "BONK/USDT", "FLOKI/USDT", "SHIB/USDT", "MEME/USDT"]

final_coins = tier1 + tier2 + tier3

def fetch_data(symbol):
    ex = ccxt.bybit({'options': {'defaultType': 'spot'}})
    # 1D
    try:
        bars_1d = ex.fetch_ohlcv(symbol, '1d', limit=1000)
        df_1d = pd.DataFrame(bars_1d, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1d['timestamp'] = pd.to_datetime(df_1d['timestamp'], unit='ms')
        df_1d.set_index('timestamp', inplace=True)
    except:
        df_1d = pd.DataFrame()
        
    # 15m
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
            
    if all_15m:
        df_15m = pd.DataFrame(all_15m[-5000:], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
        df_15m.set_index('timestamp', inplace=True)
    else:
        df_15m = pd.DataFrame()
        
    return symbol, df_1d.astype(float) if not df_1d.empty else None, df_15m.astype(float) if not df_15m.empty else None

print("Fetching data...", flush=True)
coin_data = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(fetch_data, final_coins)
    for sym, d1, d15 in results:
        coin_data[sym] = (d1, d15)
        
print("Data Fetched. Running Backtests...", flush=True)

cfg_is = BacktestConfig(split_ratio=0.0)
cfg_oos = BacktestConfig(split_ratio=0.7)

skills = [
    ("Skill 1 (Triple RSI)", TripleRSI_MeanReversion(), '1d'),
    ("Skill 2 (BB RSI)", BB_RSI_MeanReversion(), '1d'),
    ("Skill 5 (Confluence)", HighProbability_Confluence(), '1d'),
    ("Skill 3 (VWAP)", VWAP_MeanReversion(), '15m')
]
s4 = OpeningRangeBreakout_Pro(); s4.market_open_time = "00:00"; s4.cutoff_time = "02:30"
skills.append(("Skill 4 (ORB Pro - UTC)", s4, '15m'))

def run_skill(skill, df, is_cfg, oos_cfg):
    try:
        r_is = skill.backtest(df, is_cfg)
        r_oos = skill.backtest(df, oos_cfg)
        return r_is, r_oos
    except Exception as e:
        return None, None

def extract_gp_gl(res):
    if res.total_trades == 0: return 0.0, 0.0
    net = res.equity_curve.iloc[-1] - 10000.0
    pf = res.profit_factor
    if pf == float('inf'):
        return (net, 0.0) if net > 0 else (0.0, abs(net))
    if pf == 0.0:
        return 0.0, abs(net)
    if pf == 1.0:
        return abs(net), abs(net)
    gl = abs(net / (pf - 1.0))
    gp = gl * pf
    return gp, gl

def format_distribution(pf_list):
    if not pf_list: return "N/A"
    pf_list = sorted(pf_list)
    p25 = np.percentile(pf_list, 25)
    p50 = np.percentile(pf_list, 50)
    p75 = np.percentile(pf_list, 75)
    return f"Median: {p50:.2f} (25th: {p25:.2f} | 75th: {p75:.2f})"

def process_tier(tier_coins, skill, timeframe):
    total_is_trades, total_oos_trades = 0, 0
    is_gp, is_gl = 0.0, 0.0
    oos_gp, oos_gl = 0.0, 0.0
    is_pfs, oos_pfs = [], []
    
    for c in tier_coins:
        if c not in coin_data: continue
        d1, d15 = coin_data[c]
        df = d1 if timeframe == '1d' else d15
        if df is None or len(df) < 50: continue
        
        r_is, r_oos = run_skill(skill, df, cfg_is, cfg_oos)
        
        if r_is and r_is.total_trades > 0:
            total_is_trades += r_is.total_trades
            gp, gl = extract_gp_gl(r_is)
            is_gp += gp; is_gl += gl
            is_pfs.append(r_is.profit_factor if r_is.profit_factor != float('inf') else 5.0)
            
        if r_oos and r_oos.total_trades > 0:
            total_oos_trades += r_oos.total_trades
            gp, gl = extract_gp_gl(r_oos)
            oos_gp += gp; oos_gl += gl
            oos_pfs.append(r_oos.profit_factor if r_oos.profit_factor != float('inf') else 5.0)
            
    is_pooled_pf = (is_gp / is_gl) if is_gl > 0 else float('inf') if is_gp > 0 else 0.0
    oos_pooled_pf = (oos_gp / oos_gl) if oos_gl > 0 else float('inf') if oos_gp > 0 else 0.0
    
    is_str = f"[{total_is_trades}T | Pooled PF: {is_pooled_pf:.2f} | {format_distribution(is_pfs)}]"
    oos_str = f"[{total_oos_trades}T | Pooled PF: {oos_pooled_pf:.2f} | {format_distribution(oos_pfs)}]"
    return is_str, oos_str

print("\n===================== FINAL CORRECTED 60-COIN SWEEP =====================")
for skill_name, skill_obj, tf in skills:
    print(f"\n{skill_name}:")
    for tier_name, tier_list in [("Tier 1 (Majors)", tier1), ("Tier 2 (Mid-Caps)", tier2), ("Tier 3 (Memecoins)", tier3)]:
        is_str, oos_str = process_tier(tier_list, skill_obj, tf)
        print(f"  {tier_name}:")
        print(f"    IS:  {is_str}")
        print(f"    OOS: {oos_str}")
print("=========================================================================")
