import pandas as pd
import numpy as np
import datetime
from typing import Literal
from skills.base import BaseSignalSkill, SignalResult, BacktestConfig, BacktestResult
from skills.utils import atr, volume_sma

SKILL_VERSION = "1.0.2"

class OpeningRangeBreakout_Pro(BaseSignalSkill):
    '''
    Opening Range Breakout (ORB) Pro Strategy.
    Explicitly designed for session-based equities (e.g., 09:30-16:00).
    
    Confidence Score Formula:
    Base Score: 60 (strict setup conditions met).
    Margin Bonus (Max 40):
        min(40, max(0, (Volume_Multiplier - volume_threshold) * 20))

    ========================================================================
    KNOWN LIMITATIONS & VALIDATION RESULTS (v1.0.2)
    ========================================================================
    - NO EDGE DETECTED: Validated on 5,000 bars of QQQ 15m equities data. 
      Resulted in PF 0.31 In-Sample and PF 0.08 Out-of-Sample.
    - ROOT CAUSE: Using the opposite side of the Opening Range as the stop 
      results in a very wide risk distance (1R). Because massive volume 
      breakouts at the open are frequently exhaustion spikes (fake-outs), price 
      often reverses back into the range, dragging the trade to a full 1R loss 
      or a heavy time-based EOD loss. 
    - RECOMMENDATION: This specific variant is unviable. Requires a tighter 
      intra-range trailing stop or fading high-volume OR breaks rather than 
      following them.
    ========================================================================
    '''
    min_bars_required: int = 50
    
    market_open_time: str = "09:30"
    range_minutes: int = 30
    cutoff_time: str = "11:30"
    volume_threshold: float = 1.2
    
    def _prep_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['vol_sma_20'] = volume_sma(df['volume'], 20)
        df['atr_14'] = atr(df, 14)
        
        h_open, m_open = map(int, self.market_open_time.split(':'))
        open_time = datetime.time(h_open, m_open)
        
        dummy_date = datetime.datetime(2000, 1, 1, h_open, m_open)
        end_time = (dummy_date + datetime.timedelta(minutes=self.range_minutes)).time()
        
        h_cut, m_cut = map(int, self.cutoff_time.split(':'))
        cutoff = datetime.time(h_cut, m_cut)
        
        df['is_or'] = (df.index.time >= open_time) & (df.index.time < end_time)
        df['date'] = df.index.date
        
        or_highs = df[df['is_or']].groupby('date')['high'].max()
        or_lows = df[df['is_or']].groupby('date')['low'].min()
        
        df['or_high'] = df['date'].map(or_highs)
        df['or_low'] = df['date'].map(or_lows)
        df['or_width'] = df['or_high'] - df['or_low']
        
        # Proper datetime object comparison for cutoff
        df['valid_entry_time'] = (df.index.time >= end_time) & (df.index.time <= cutoff)
        df['atr_valid'] = (df['or_width'] >= 0.5 * df['atr_14']) & (df['or_width'] <= 2.5 * df['atr_14'])
        df['vol_mult'] = np.where(df['vol_sma_20'] > 0, df['volume'] / df['vol_sma_20'], 0)
        
        return df

    def generate_signal(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < self.min_bars_required:
            return SignalResult("NEUTRAL", 0.0, f"Insufficient data (need {self.min_bars_required} bars)")
            
        df = self._prep_data(df)
        curr = df.iloc[-1]
        
        if pd.isna(curr['or_high']) or not curr['valid_entry_time'] or not curr['atr_valid']:
            return SignalResult("NEUTRAL", 0.0, "Outside valid entry time or invalid ATR range")
            
        is_long = (curr['close'] > curr['or_high']) and (curr['vol_mult'] > self.volume_threshold)
        is_short = (curr['close'] < curr['or_low']) and (curr['vol_mult'] > self.volume_threshold)
        
        if is_long:
            margin = min(40, max(0, (curr['vol_mult'] - self.volume_threshold) * 20))
            conf = 60 + margin
            stop = curr['or_low']
            return SignalResult("BUY", conf, "ORB Long + Volume Confirmation", stop_price=stop)
            
        if is_short:
            margin = min(40, max(0, (curr['vol_mult'] - self.volume_threshold) * 20))
            conf = 60 + margin
            stop = curr['or_high']
            return SignalResult("SELL", conf, "ORB Short + Volume Confirmation", stop_price=stop)
            
        return SignalResult("NEUTRAL", 0.0, "Conditions not met")

    def backtest(self, df: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
        df = self._prep_data(df)
        split_idx = int(len(df) * config.split_ratio)
        test_df = df.iloc[split_idx:].copy()
        
        if len(test_df) < 50:
            return BacktestResult(0, 0, 0, 0, 0, 0, 0, pd.Series(dtype=float), False)

        in_trade = False
        pending_entry = False
        
        trade_dir = 0
        entry_price = 0.0
        stop_price = 0.0
        
        trades = []
        equity = 10000.0
        equity_curve = []
        
        for i in range(len(test_df)):
            bar = test_df.iloc[i]
            
            # 1. Execute Pending Actions at the OPEN of this bar
            if pending_entry:
                trade_dir = pending_dir
                in_trade = True
                pending_entry = False
                
                if trade_dir == 1:
                    entry_price = bar['open'] * (1 + config.slippage) + (bar['open'] * config.commission)
                else:
                    entry_price = bar['open'] * (1 - config.slippage) - (bar['open'] * config.commission)
                    
            # 2. Track intra-bar price action
            if in_trade:
                closed = False
                
                hit_stop = (trade_dir == 1 and bar['low'] <= stop_price) or (trade_dir == -1 and bar['high'] >= stop_price)
                
                # Dynamic EOD check that works regardless of timeframe or missing bars
                end_of_day = (i == len(test_df) - 1) or (test_df.index[i+1].date() != bar.name.date())
                
                if hit_stop:
                    if trade_dir == 1:
                        actual_fill = min(bar['open'], stop_price)
                        exit_price = actual_fill * (1 - config.slippage) - (actual_fill * config.commission)
                    else:
                        actual_fill = max(bar['open'], stop_price)
                        exit_price = actual_fill * (1 + config.slippage) + (actual_fill * config.commission)
                    closed = True
                    
                elif end_of_day:
                    if trade_dir == 1:
                        exit_price = bar['close'] * (1 - config.slippage) - (bar['close'] * config.commission)
                    else:
                        exit_price = bar['close'] * (1 + config.slippage) + (bar['close'] * config.commission)
                    closed = True
                    
                if closed:
                    pnl_pct = (exit_price - entry_price) / entry_price if trade_dir == 1 else (entry_price - exit_price) / entry_price
                    risk_amount = equity * config.risk_per_trade
                    stop_dist_pct = abs(entry_price - stop_price) / entry_price if entry_price > 0 else 0.01
                    pos_size = risk_amount / stop_dist_pct if stop_dist_pct > 0 else 0
                    max_pos_value = equity * config.max_position_pct
                    if pos_size > max_pos_value:
                        pos_size = max_pos_value
                        
                    trade_pnl = pos_size * pnl_pct
                    equity += trade_pnl
                    trades.append({'pnl': pnl_pct, 'trade_pnl': trade_pnl, 'r': pnl_pct / stop_dist_pct if stop_dist_pct > 0 else 0})
                    
                    in_trade = False

            equity_curve.append(equity)
                    
            # 3. End of bar calculations (Close) - check for setups
            if not in_trade and not pending_entry:
                if pd.isna(bar['or_high']) or not bar['valid_entry_time'] or not bar['atr_valid']:
                    continue
                    
                long_cond = (bar['close'] > bar['or_high']) and (bar['vol_mult'] > self.volume_threshold)
                short_cond = (bar['close'] < bar['or_low']) and (bar['vol_mult'] > self.volume_threshold)
                
                if long_cond:
                    pending_entry = True
                    pending_dir = 1
                    stop_price = bar['or_low']
                elif short_cond:
                    pending_entry = True
                    pending_dir = -1
                    stop_price = bar['or_high']
                    
        eq_s = pd.Series(equity_curve)
        if not trades:
            return BacktestResult(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, eq_s, False)
            
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        gross_profit = sum(t['trade_pnl'] for t in wins)
        gross_loss = abs(sum(t['trade_pnl'] for t in losses))
        
        win_rate = len(wins) / len(trades)
        pf = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        avg_r = sum(t['r'] for t in trades) / len(trades)
        expectancy = avg_r
        
        peak = eq_s.cummax()
        dd = (eq_s - peak) / peak
        max_dd = abs(dd.min())
        
        returns = eq_s.pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 26) if len(returns)>2 and returns.std() != 0 else 0.0
        
        return BacktestResult(win_rate, pf, expectancy, max_dd, sharpe, avg_r, len(trades), eq_s, False)
