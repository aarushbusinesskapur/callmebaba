import pandas as pd
import urllib.request
import io
import warnings
import datetime
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
is_df = skill4._prep_data(qqq_15m)

def run_loop(df):
    in_trade = False
    pending_entry = False
    log = []
    
    for i in range(len(df)):
        bar = df.iloc[i]
        
        if pending_entry:
            in_trade = True
            pending_entry = False
            log.append((bar.name, 'ENTRY'))
            
        if in_trade:
            end_of_day = (bar.name.time() >= datetime.time(15, 50))
            # Just for debug, assume stop never hits, only EOD hits
            if end_of_day:
                in_trade = False
                log.append((bar.name, 'EXIT (EOD)'))
                
        if not in_trade and not pending_entry:
            if pd.isna(bar['or_high']) or not bar['valid_entry_time'] or not bar['atr_valid']:
                pass
            elif (bar['close'] > bar['or_high']) and (bar['vol_mult'] > skill4.volume_threshold):
                pending_entry = True
                log.append((bar.name, 'SIGNAL LONG'))
            elif (bar['close'] < bar['or_low']) and (bar['vol_mult'] > skill4.volume_threshold):
                pending_entry = True
                log.append((bar.name, 'SIGNAL SHORT'))
    return log

log_is = run_loop(is_df)
test_oos = is_df.iloc[int(len(is_df)*0.7):].copy()
log_oos = run_loop(test_oos)

print("IS Logs around July 15:")
for l in log_is:
    if l[0].month == 7 and l[0].day in [14, 15, 16] and l[0].year == 2026:
        print(l)
        
print("\nOOS Logs around July 15:")
for l in log_oos:
    if l[0].month == 7 and l[0].day in [14, 15, 16] and l[0].year == 2026:
        print(l)
