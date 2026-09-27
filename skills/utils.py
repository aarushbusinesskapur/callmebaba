import pandas as pd
import numpy as np

def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close_prev = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower

def volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
    return sma(volume, period)

def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close_prev = df['close'].shift(1)
    
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    plus_dm = pd.Series(plus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean()
    minus_dm = pd.Series(minus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean()
    
    tr_ema = atr(df, period)
    
    plus_di = 100 * (plus_dm / tr_ema)
    minus_di = 100 * (minus_dm / tr_ema)
    
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    return dx.ewm(alpha=1/period, adjust=False).mean()

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def session_vwap_with_bands(df: pd.DataFrame) -> pd.DataFrame:
    '''Calculates daily session VWAP and StdDev bands. Expects DatetimeIndex.'''
    df = df.copy()
    df['date'] = df.index.date
    df['typ_price'] = (df['high'] + df['low'] + df['close']) / 3
    df['tp_v'] = df['typ_price'] * df['volume']
    
    groupby_date = df.groupby('date')
    df['cum_tp_v'] = groupby_date['tp_v'].cumsum()
    df['cum_v'] = groupby_date['volume'].cumsum()
    df['vwap'] = df['cum_tp_v'] / df['cum_v']
    
    # Variance and StdDev
    df['price_diff_sq'] = ((df['typ_price'] - df['vwap']) ** 2) * df['volume']
    df['cum_price_diff_sq'] = groupby_date['price_diff_sq'].cumsum()
    df['vwap_var'] = df['cum_price_diff_sq'] / df['cum_v']
    df['vwap_std'] = np.sqrt(df['vwap_var'])
    
    return df[['vwap', 'vwap_std']]
