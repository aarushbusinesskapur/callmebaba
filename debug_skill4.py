import pandas as pd
import urllib.request
import io
import warnings
warnings.filterwarnings('ignore')

from skills.base import BacktestConfig
from skills.opening_range_breakout_pro import OpeningRangeBreakout_Pro

API_KEY = "7873877dad9f4f7fb1750fa5ef5eaa86"

def get_twelvedata(symbol, interval, outputsize=5000):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={API_KEY}&outputsize={outputsize}&format=csv"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req)
    df = pd.read_csv(io.StringIO(res.read().decode('utf-8')), sep=';')
    df.rename(columns={'datetime': 'timestamp'}, inplace=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df.sort_index().astype(float)

qqq_15m = get_twelvedata('QQQ', '15min')

skill4 = OpeningRangeBreakout_Pro()
cfg_is = BacktestConfig(split_ratio=0.0)
cfg_oos = BacktestConfig(split_ratio=0.7)

res_is = skill4.backtest(qqq_15m, cfg_is)
res_oos = skill4.backtest(qqq_15m, cfg_oos)

print(f"IS Trades: {res_is.total_trades}")
print(f"OOS Trades: {res_oos.total_trades}")

# Debug: Which days did the trades occur?
is_df = skill4._prep_data(qqq_15m)
test_oos = is_df.iloc[int(len(is_df)*0.7):].copy()

def find_trade_dates(df, skill):
    trades = []
    pending_entry = False
    in_trade = False
    for i in range(len(df)):
        bar = df.iloc[i]
        
        if pending_entry:
            in_trade = True
            pending_entry = False
            trades.append(bar.name)
            
        if in_trade:
            # End of day check
            end_of_day = (bar.name.time() >= pd.to_datetime("15:50").time())
            if end_of_day:
                in_trade = False
                
        if not in_trade and not pending_entry:
            if pd.isna(bar['or_high']) or not bar['valid_entry_time'] or not bar['atr_valid']:
                continue
            if (bar['close'] > bar['or_high']) and (bar['vol_mult'] > skill.volume_threshold):
                pending_entry = True
            elif (bar['close'] < bar['or_low']) and (bar['vol_mult'] > skill.volume_threshold):
                pending_entry = True
    return trades

t_is = find_trade_dates(is_df, skill4)
t_oos = find_trade_dates(test_oos, skill4)
print("\nIS Trade Dates in last 30% window:")
for t in t_is:
    if t >= test_oos.index[0]:
        print(t)
        
print("\nOOS Trade Dates:")
for t in t_oos:
    print(t)
