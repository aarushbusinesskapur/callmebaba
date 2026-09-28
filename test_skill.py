import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Literal, Optional
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

@dataclass
class SignalResult:
    signal: Literal["BUY", "SELL", "NEUTRAL"]
    confidence: float
    reason: str
    stop_price: Optional[float] = None
    target_price: Optional[float] = None

@dataclass
class BacktestConfig:
    risk_per_trade: float = 0.01
    commission: float = 0.0005
    slippage: float = 0.0005
    split_ratio: float = 0.7

@dataclass
class BacktestResult:
    win_rate: float
    profit_factor: float
    expectancy: float
    max_drawdown: float
    sharpe_ratio: float
    avg_r: float
    total_trades: int
    equity_curve: pd.Series
    is_in_sample_only: bool

class BaseSignalSkill(ABC):
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> SignalResult:
        pass
        
    @abstractmethod
    def backtest(self, df: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
        pass

def calculate_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df: pd.DataFrame, period: int=14) -> pd.Series:
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

class TripleRSI_MeanReversion(BaseSignalSkill):
    '''
    TripleRSI_MeanReversion Strategy.
    Scope: Daily timeframe, liquid stocks/ETFs.
    
    Confidence Formula:
    Base score of 60 if all binary conditions are met.
    Additional margin score (max 40) based on RSI(2) overextension:
    For Longs: margin = (10 - RSI(2)) * 4
    For Shorts: margin = (RSI(2) - 90) * 4
    Confidence = min(100, 60 + margin)
    '''
    def _prep_data(self, df: pd.DataFrame):
        df = df.copy()
        df['rsi_14'] = calculate_rsi(df['close'], 14)
        df['rsi_7'] = calculate_rsi(df['close'], 7)
        df['rsi_2'] = calculate_rsi(df['close'], 2)
        df['sma_200'] = df['close'].rolling(200).mean()
        df['atr_14'] = calculate_atr(df, 14)
        return df
        
    def generate_signal(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < 200:
            return SignalResult("NEUTRAL", 0.0, "Insufficient data (need 200 bars for SMA)")
            
        df = self._prep_data(df)
        last = df.iloc[-1]
        
        if pd.isna(last['sma_200']):
            return SignalResult("NEUTRAL", 0.0, "Insufficient data for SMA200")
            
        long_cond = (last['close'] > last['sma_200']) and (last['rsi_14'] < 40) and (last['rsi_7'] < 30) and (last['rsi_2'] < 10)
        short_cond = (last['close'] < last['sma_200']) and (last['rsi_14'] > 60) and (last['rsi_7'] > 70) and (last['rsi_2'] > 90)
        
        if long_cond:
            margin = max(0, (10 - last['rsi_2']) * 4)
            conf = min(100, 60 + margin)
            stop = last['close'] - (1.5 * last['atr_14'])
            return SignalResult("BUY", conf, "Triple RSI Oversold + Above SMA200", stop_price=stop)
            
        if short_cond:
            margin = max(0, (last['rsi_2'] - 90) * 4)
            conf = min(100, 60 + margin)
            stop = last['close'] + (1.5 * last['atr_14'])
            return SignalResult("SELL", conf, "Triple RSI Overbought + Below SMA200", stop_price=stop)
            
        return SignalResult("NEUTRAL", 0.0, "Conditions not met")

    def backtest(self, df: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
        df = self._prep_data(df)
        
        # Simple loop for state machine to ensure no lookahead bias
        # Entries use the NEXT bar's open.
        
        in_trade = False
        trade_dir = 0
        entry_price = 0.0
        stop_price = 0.0
        bars_held = 0
        
        trades = []
        equity = 10000.0
        equity_curve = []
        
        # Train/Test split handling
        split_idx = int(len(df) * config.split_ratio)
        test_df = df.iloc[split_idx:]
        
        for i in range(len(test_df)-1):
            curr = test_df.iloc[i]
            nxt = test_df.iloc[i+1]
            equity_curve.append(equity)
            
            if not in_trade:
                if pd.isna(curr['sma_200']): continue
                
                long_cond = (curr['close'] > curr['sma_200']) and (curr['rsi_14'] < 40) and (curr['rsi_7'] < 30) and (curr['rsi_2'] < 10)
                short_cond = (curr['close'] < curr['sma_200']) and (curr['rsi_14'] > 60) and (curr['rsi_7'] > 70) and (curr['rsi_2'] > 90)
                
                if long_cond:
                    in_trade = True
                    trade_dir = 1
                    entry_price = nxt['open'] * (1 + config.slippage) + (nxt['open'] * config.commission)
                    stop_price = curr['close'] - (1.5 * curr['atr_14'])
                    bars_held = 0
                elif short_cond:
                    in_trade = True
                    trade_dir = -1
                    entry_price = nxt['open'] * (1 - config.slippage) - (nxt['open'] * config.commission)
                    stop_price = curr['close'] + (1.5 * curr['atr_14'])
                    bars_held = 0
            else:
                bars_held += 1
                exit_price = 0.0
                closed = False
                
                # Check stops (hit on current bar)
                if trade_dir == 1 and nxt['low'] <= stop_price:
                    exit_price = stop_price * (1 - config.slippage) - (stop_price * config.commission)
                    closed = True
                elif trade_dir == -1 and nxt['high'] >= stop_price:
                    exit_price = stop_price * (1 + config.slippage) + (stop_price * config.commission)
                    closed = True
                
                # Check exit conditions
                if not closed:
                    if trade_dir == 1 and (curr['rsi_14'] > 55 or bars_held >= 8):
                        exit_price = nxt['open'] * (1 - config.slippage) - (nxt['open'] * config.commission)
                        closed = True
                    elif trade_dir == -1 and (curr['rsi_14'] < 45 or bars_held >= 8):
                        exit_price = nxt['open'] * (1 + config.slippage) + (nxt['open'] * config.commission)
                        closed = True
                
                if closed:
                    pnl = (exit_price - entry_price) / entry_price if trade_dir == 1 else (entry_price - exit_price) / entry_price
                    # Simplified risk sizing: assuming 1% risk based on stop distance
                    risk_amount = equity * config.risk_per_trade
                    stop_dist_pct = abs(entry_price - stop_price) / entry_price
                    pos_size = risk_amount / stop_dist_pct if stop_dist_pct > 0 else 0
                    trade_pnl = pos_size * pnl
                    
                    equity += trade_pnl
                    trades.append({'pnl': pnl, 'trade_pnl': trade_pnl, 'r': pnl / stop_dist_pct})
                    in_trade = False
                    
        equity_curve.append(equity)
        
        if not trades:
            return BacktestResult(0, 0, 0, 0, 0, 0, 0, pd.Series(equity_curve), False)
            
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        gross_profit = sum(t['trade_pnl'] for t in wins)
        gross_loss = abs(sum(t['trade_pnl'] for t in losses))
        
        win_rate = len(wins) / len(trades)
        pf = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        avg_r = sum(t['r'] for t in trades) / len(trades)
        expectancy = avg_r # Simplified expectancy in terms of R
        
        eq_s = pd.Series(equity_curve)
        peak = eq_s.cummax()
        dd = (eq_s - peak) / peak
        max_dd = abs(dd.min())
        
        returns = eq_s.pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if len(returns)>2 else 0
        
        return BacktestResult(win_rate, pf, expectancy, max_dd, sharpe, avg_r, len(trades), eq_s, False)

# Fetch sample data and test
import ccxt
ex = ccxt.kraken()
ohlcv = ex.fetch_ohlcv('BTC/USD', '1d', limit=1000)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

skill = TripleRSI_MeanReversion()
res = skill.backtest(df, BacktestConfig())
print(f"Total Trades: {res.total_trades}")
print(f"Win Rate: {res.win_rate:.2%}")
print(f"Profit Factor: {res.profit_factor:.2f}")
print(f"Expectancy: {res.expectancy:.2f}R")
print(f"Max DD: {res.max_drawdown:.2%}")
print(f"Sharpe: {res.sharpe_ratio:.2f}")

sig = skill.generate_signal(df.iloc[-250:])
print(f"Live Signal: {sig}")
