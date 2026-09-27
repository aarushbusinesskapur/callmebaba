import pandas as pd
import numpy as np
from typing import Literal
from skills.base import BaseSignalSkill, SignalResult, BacktestConfig, BacktestResult
from skills.utils import rsi, sma, atr

SKILL_VERSION = "1.0.2"

class TripleRSI_MeanReversion(BaseSignalSkill):
    '''
    TripleRSI Mean Reversion Strategy.
    Best suited for: Daily timeframe, liquid stocks/ETFs.
    
    Confidence Score Formula:
    Base Score: 60 (if all strict conditions are met).
    Margin Bonus (Max 40):
        - Long: min(40, max(0, (10 - RSI(2)) * 4))
        - Short: min(40, max(0, (RSI(2) - 90) * 4))
        
    NOTE 1: The margin multiplier constant (4) is a v1 heuristic estimate, 
    not empirically calibrated. To be revisited with real backtest data 
    across different asset classes.
    
    NOTE 2: If backtested on Crypto (24/7 markets), this is operating 
    outside its intended equities scope. Ensure Sharpe is annualized via sqrt(365).

    ========================================================================
    KNOWN LIMITATIONS & VALIDATION RESULTS (v1.0.2)
    ========================================================================
    - EQUITIES: Default parameters show NO POSITIVE EDGE on 25 years of SPY 
      daily data (in-sample PF 1.04, out-of-sample PF 0.85, negative expectancy OOS). 
      This strategy SHOULD NOT be enabled live on equities with default settings 
      without further work (e.g., a market-regime filter that disables shorts in 
      confirmed uptrends, or reserving it for range-bound conditions only).
      
    - CRYPTO: Initial BTC results looked more promising (PF 2.16 in-sample, 
      PF 1.66 OOS), but were on far too few trades (10 and 5 respectively) 
      to draw any real conclusion. FLAG: Insufficient sample, not validated.
    ========================================================================
    '''
    min_bars_required: int = 200

    def _prep_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['rsi_14'] = rsi(df['close'], 14)
        df['rsi_7'] = rsi(df['close'], 7)
        df['rsi_2'] = rsi(df['close'], 2)
        df['sma_200'] = sma(df['close'], 200)
        df['atr_14'] = atr(df, 14)
        return df

    def generate_signal(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < self.min_bars_required:
            return SignalResult("NEUTRAL", 0.0, f"Insufficient data (need {self.min_bars_required} bars)")
            
        df = self._prep_data(df)
        last = df.iloc[-1]
        
        if pd.isna(last['sma_200']):
            return SignalResult("NEUTRAL", 0.0, "Insufficient data for SMA200")
            
        is_long = (last['close'] > last['sma_200']) and (last['rsi_14'] < 40) and (last['rsi_7'] < 30) and (last['rsi_2'] < 10)
        is_short = (last['close'] < last['sma_200']) and (last['rsi_14'] > 60) and (last['rsi_7'] > 70) and (last['rsi_2'] > 90)
        
        if is_long:
            margin = min(40, max(0, (10 - last['rsi_2']) * 4))
            conf = 60 + margin
            stop = last['close'] - (1.5 * last['atr_14'])
            return SignalResult("BUY", conf, "Triple RSI Oversold + Above SMA200", stop_price=stop)
            
        if is_short:
            margin = min(40, max(0, (last['rsi_2'] - 90) * 4))
            conf = 60 + margin
            stop = last['close'] + (1.5 * last['atr_14'])
            return SignalResult("SELL", conf, "Triple RSI Overbought + Below SMA200", stop_price=stop)
            
        return SignalResult("NEUTRAL", 0.0, "Conditions not met")

    def backtest(self, df: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
        df = self._prep_data(df)
        split_idx = int(len(df) * config.split_ratio)
        test_df = df.iloc[split_idx:].copy()
        
        if len(test_df) < 50:
            return BacktestResult(0, 0, 0, 0, 0, 0, 0, pd.Series(dtype=float), False)

        in_trade = False
        pending_entry = False
        pending_exit = False
        
        trade_dir = 0
        entry_price = 0.0
        stop_price = 0.0
        bars_held = 0
        
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
                bars_held = 0
                if trade_dir == 1:
                    entry_price = bar['open'] * (1 + config.slippage) + (bar['open'] * config.commission)
                else:
                    entry_price = bar['open'] * (1 - config.slippage) - (bar['open'] * config.commission)
            
            if pending_exit:
                if trade_dir == 1:
                    exit_price = bar['open'] * (1 - config.slippage) - (bar['open'] * config.commission)
                else:
                    exit_price = bar['open'] * (1 + config.slippage) + (bar['open'] * config.commission)
                
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
                pending_exit = False
                
            # 2. Track intra-bar price action (Stops evaluated during the bar)
            if in_trade:
                bars_held += 1
                closed = False
                
                if trade_dir == 1 and bar['low'] <= stop_price:
                    actual_fill = min(bar['open'], stop_price)
                    exit_price = actual_fill * (1 - config.slippage) - (actual_fill * config.commission)
                    closed = True
                elif trade_dir == -1 and bar['high'] >= stop_price:
                    actual_fill = max(bar['open'], stop_price)
                    exit_price = actual_fill * (1 + config.slippage) + (actual_fill * config.commission)
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
                    
            # 3. End of bar calculations (Close)
            if not in_trade and not pending_entry:
                if pd.isna(bar['sma_200']): continue
                long_cond = (bar['close'] > bar['sma_200']) and (bar['rsi_14'] < 40) and (bar['rsi_7'] < 30) and (bar['rsi_2'] < 10)
                short_cond = (bar['close'] < bar['sma_200']) and (bar['rsi_14'] > 60) and (bar['rsi_7'] > 70) and (bar['rsi_2'] > 90)
                
                if long_cond:
                    pending_entry = True
                    pending_dir = 1
                    stop_price = bar['close'] - (1.5 * bar['atr_14'])
                elif short_cond:
                    pending_entry = True
                    pending_dir = -1
                    stop_price = bar['close'] + (1.5 * bar['atr_14'])
                    
            if in_trade and not pending_exit:
                if trade_dir == 1 and (bar['rsi_14'] > 55 or bars_held >= 8):
                    pending_exit = True
                elif trade_dir == -1 and (bar['rsi_14'] < 45 or bars_held >= 8):
                    pending_exit = True
                    
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
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if len(returns)>2 and returns.std() != 0 else 0.0
        
        return BacktestResult(win_rate, pf, expectancy, max_dd, sharpe, avg_r, len(trades), eq_s, False)
