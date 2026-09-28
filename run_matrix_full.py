import pandas as pd
import numpy as np
import urllib.request
import io
import ccxt
import time
import warnings
warnings.filterwarnings('ignore')

from skills.base import BacktestConfig
from skills.triple_rsi_mean_reversion import TripleRSI_MeanReversion
from skills.bb_rsi_mean_reversion import BB_RSI_MeanReversion
from skills.vwap_mean_reversion import VWAP_MeanReversion
from skills.opening_range_breakout_pro import OpeningRangeBreakout_Pro
from skills.high_probability_confluence import HighProbability_Confluence

API_KEY = "7873877dad9f4f7fb1750fa5ef5eaa86"

def get_twelvedata(symbol, interval, limit=5000):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={API_KEY}&outputsize={limit}&format=csv"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req)
    df = pd.read_csv(io.StringIO(res.read().decode('utf-8')), sep=';')
    df.rename(columns={'datetime': 'timestamp'}, inplace=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df.sort_index().astype(float)

def get_kraken_full(symbol, timeframe, limit=5000):
    exchange = ccxt.kraken()
    all_bars = []
    now = exchange.milliseconds()
    ms_per_bar = 86400000 if timeframe == '1d' else 900000
    start_time = now - ((limit + 500) * ms_per_bar) # Give buffer
    
    while len(all_bars) < limit:
        try:
            bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=int(start_time))
            if not bars: 
                break
            all_bars.extend(bars)
            start_time = bars[-1][0] + 1
            time.sleep(1.5)
        except Exception as e:
            print(f"Kraken error: {e}")
            break
            
    df = pd.DataFrame(all_bars[-limit:], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df.astype(float)

print("Fetching Data (Max History 5000 bars)...", flush=True)
spy_1d = get_twelvedata('SPY', '1day', 5000)
qqq_15m = get_twelvedata('QQQ', '15min', 5000)

btc_1d = get_kraken_full('BTC/USD', '1d', 5000)
btc_15m = get_kraken_full('BTC/USD', '15m', 5000)
eth_1d = get_kraken_full('ETH/USD', '1d', 5000)
eth_15m = get_kraken_full('ETH/USD', '15m', 5000)
print("Data Fetched. Running Backtests...", flush=True)

cfg_is = BacktestConfig(split_ratio=0.0)
cfg_oos = BacktestConfig(split_ratio=0.7)

skills_daily = {
    "Skill 1 (Triple RSI)": TripleRSI_MeanReversion(),
    "Skill 2 (BB RSI)": BB_RSI_MeanReversion(),
    "Skill 5 (Confluence)": HighProbability_Confluence()
}

s4_eq = OpeningRangeBreakout_Pro()
s4_eq.market_open_time = "09:30"
s4_eq.cutoff_time = "11:30"

s4_utc = OpeningRangeBreakout_Pro()
s4_utc.market_open_time = "00:00"
s4_utc.cutoff_time = "02:30"

s4_ny = OpeningRangeBreakout_Pro()
s4_ny.market_open_time = "13:30"
s4_ny.cutoff_time = "16:00"

def fmt(res):
    if res.total_trades == 0: return "0T"
    tag = " [THIN]" if res.total_trades < 30 else ""
    return f"{res.total_trades}T{tag} | WR {res.win_rate:.0%} | PF {res.profit_factor:.2f}"

results = []

for name, skill in skills_daily.items():
    print(f"Running {name}...", flush=True)
    s_is = skill.backtest(spy_1d, cfg_is)
    s_oos = skill.backtest(spy_1d, cfg_oos)
    b_is = skill.backtest(btc_1d, cfg_is)
    b_oos = skill.backtest(btc_1d, cfg_oos)
    e_is = skill.backtest(eth_1d, cfg_is)
    e_oos = skill.backtest(eth_1d, cfg_oos)
    results.append(f"{name}:\n"
                   f"  SPY: IS [{fmt(s_is)}] || OOS [{fmt(s_oos)}]\n"
                   f"  BTC: IS [{fmt(b_is)}] || OOS [{fmt(b_oos)}]\n"
                   f"  ETH: IS [{fmt(e_is)}] || OOS [{fmt(e_oos)}]\n")

print("Running Skill 3...", flush=True)
s3 = VWAP_MeanReversion()
q_is = s3.backtest(qqq_15m, cfg_is)
q_oos = s3.backtest(qqq_15m, cfg_oos)
b_is = s3.backtest(btc_15m, cfg_is)
b_oos = s3.backtest(btc_15m, cfg_oos)
e_is = s3.backtest(eth_15m, cfg_is)
e_oos = s3.backtest(eth_15m, cfg_oos)
results.append(f"Skill 3 (VWAP):\n"
               f"  QQQ: IS [{fmt(q_is)}] || OOS [{fmt(q_oos)}]\n"
               f"  BTC: IS [{fmt(b_is)}] || OOS [{fmt(b_oos)}]\n"
               f"  ETH: IS [{fmt(e_is)}] || OOS [{fmt(e_oos)}]\n")

print("Running Skill 4...", flush=True)
q_is = s4_eq.backtest(qqq_15m, cfg_is)
q_oos = s4_eq.backtest(qqq_15m, cfg_oos)
b_utc_is = s4_utc.backtest(btc_15m, cfg_is)
b_utc_oos = s4_utc.backtest(btc_15m, cfg_oos)
b_ny_is = s4_ny.backtest(btc_15m, cfg_is)
b_ny_oos = s4_ny.backtest(btc_15m, cfg_oos)
e_utc_is = s4_utc.backtest(eth_15m, cfg_is)
e_utc_oos = s4_utc.backtest(eth_15m, cfg_oos)
e_ny_is = s4_ny.backtest(eth_15m, cfg_is)
e_ny_oos = s4_ny.backtest(eth_15m, cfg_oos)

results.append(f"Skill 4 (ORB Pro):\n"
               f"  QQQ (09:30): IS [{fmt(q_is)}] || OOS [{fmt(q_oos)}]\n"
               f"  BTC (UTC)  : IS [{fmt(b_utc_is)}] || OOS [{fmt(b_utc_oos)}]\n"
               f"  BTC (NY)   : IS [{fmt(b_ny_is)}] || OOS [{fmt(b_ny_oos)}]\n"
               f"  ETH (UTC)  : IS [{fmt(e_utc_is)}] || OOS [{fmt(e_utc_oos)}]\n"
               f"  ETH (NY)   : IS [{fmt(e_ny_is)}] || OOS [{fmt(e_ny_oos)}]\n")

print("\n===================== FINAL MATRIX (FULL HISTORY) =====================")
print("\n".join(results))
