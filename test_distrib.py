import pandas as pd
import numpy as np
import urllib.request
import io
import warnings
warnings.filterwarnings('ignore')

from skills.utils import rsi, ema, atr, volume_sma, adx, macd

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

print("Fetching SPY (1d) to map distributions...")
df = get_twelvedata('SPY', '1day')

df['ema_50'] = ema(df['close'], 50)
df['ema_200'] = ema(df['close'], 200)
df['adx_14'] = adx(df, 14)
df['rsi_14'] = rsi(df['close'], 14)
_, _, df['macd_hist'] = macd(df['close'])
df['atr_14'] = atr(df, 14)
df['atr_sma_20'] = df['atr_14'].rolling(window=20).mean()
df['vol_sma_20'] = volume_sma(df['volume'], 20)
df['struct_high_10'] = df['high'].shift(1).rolling(window=10).max()
df['struct_low_10'] = df['low'].shift(1).rolling(window=10).min()

df['c_trend_long'] = (df['close'] > df['ema_50']) & (df['close'] > df['ema_200']) & (df['adx_14'] > 22)
df['c_trend_short'] = (df['close'] < df['ema_50']) & (df['close'] < df['ema_200']) & (df['adx_14'] > 22)
df['c_mom_long'] = (df['rsi_14'].between(40, 60)) | (df['macd_hist'] > df['macd_hist'].shift(1))
df['c_mom_short'] = (df['rsi_14'].between(40, 60)) | (df['macd_hist'] < df['macd_hist'].shift(1))
df['c_volat_active'] = df['atr_14'] > df['atr_sma_20']
df['c_vol_active'] = df['volume'] > (1.2 * df['vol_sma_20'])
df['c_struct_long'] = df['close'] > df['struct_high_10']
df['c_struct_short'] = df['close'] < df['struct_low_10']

df['long_confluence'] = df['c_trend_long'].astype(int) + df['c_mom_long'].astype(int) + df['c_volat_active'].astype(int) + df['c_vol_active'].astype(int) + df['c_struct_long'].astype(int)
df['short_confluence'] = df['c_trend_short'].astype(int) + df['c_mom_short'].astype(int) + df['c_volat_active'].astype(int) + df['c_vol_active'].astype(int) + df['c_struct_short'].astype(int)

df = df.dropna()

valid_longs = (df['long_confluence'] >= 3) & (df['c_trend_long'] | df['c_struct_long'])
valid_shorts = (df['short_confluence'] >= 3) & (df['c_trend_short'] | df['c_struct_short'])

def calc_score(match_count, adx_val):
    base = 36 if match_count == 3 else (48 if match_count == 4 else 60)
    margin = min(40, max(0, (adx_val - 22) * 2))
    return base + margin

scores = []
for i in range(len(df)):
    if valid_longs.iloc[i]:
        scores.append(calc_score(df['long_confluence'].iloc[i], df['adx_14'].iloc[i]))
    elif valid_shorts.iloc[i]:
        scores.append(calc_score(df['short_confluence'].iloc[i], df['adx_14'].iloc[i]))
        
scores = pd.Series(scores)

print("\n==== SIGNAL POTENTIAL (5000 Days of SPY) ====")
print(f"Total raw signals with >=3 confluence AND directional confirmation: {len(scores)}")
print(f"Signals with Score >= 70 (Original Gate): {len(scores[scores >= 70])}")
print(f"Signals with Score >= 65: {len(scores[scores >= 65])}")
print(f"Signals with Score >= 60: {len(scores[scores >= 60])}")
print(f"Signals with Score >= 50: {len(scores[scores >= 50])}")

print("\nScore Breakdown by Confluence Count (Total Signals):")
print(f"3/5 Conditions Met: {len(df[(valid_longs | valid_shorts) & ((df['long_confluence']==3) | (df['short_confluence']==3))])}")
print(f"4/5 Conditions Met: {len(df[(valid_longs | valid_shorts) & ((df['long_confluence']==4) | (df['short_confluence']==4))])}")
print(f"5/5 Conditions Met: {len(df[(valid_longs | valid_shorts) & ((df['long_confluence']==5) | (df['short_confluence']==5))])}")
