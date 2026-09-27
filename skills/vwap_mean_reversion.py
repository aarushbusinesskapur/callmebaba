import pandas as pd
import numpy as np
from typing import Literal
from skills.base import BaseSignalSkill, SignalResult, BacktestConfig, BacktestResult
from skills.utils import rsi, ema, atr, session_vwap_with_bands

SKILL_VERSION = "1.0.1"

class VWAP_MeanReversion(BaseSignalSkill):
    '''
    VWAP Mean Reversion Strategy.
    Timeframe: 1H (Crypto Proxy for Equities Intraday).
    
    Confidence Score Formula:
    Base Score: 60 (if all strict conditions are met).
    Margin Bonus (Max 40):
        - Long: min(40, max(0, (StdDevs_Below_VWAP - 1.5) * 80))
        - Short: min(40, max(0, (StdDevs_Above_VWAP - 1.5) * 80))

    ========================================================================
    KNOWN LIMITATIONS & VALIDATION RESULTS (v1.0.1)
    ========================================================================
    - PROXY CAVEAT: This backtest uses a 1H Crypto (BTC) proxy standing in 
      for the equities intraday use case, due to API blocks in the test env. 
      This is NOT a validation of its performance on actual equities.
    - EXTREME RARITY: The combination of 1.5+ StdDevs, deep RSI, and a strict 
      1H bar reclaim triggered only 16 times across 17,000 bars (2 years).
    - POOR R:R (PF 0.37): Waiting for a 1H bar to reclaim its upper-half 
      after a deep VWAP deviation means you enter very late. By the time 
      you enter, the distance back to the dynamic VWAP target is heavily 
      compressed, resulting in tiny wins relative to the 1.0 ATR stop risk.
    ========================================================================
    '''
    min_bars_required: int = 200 

    def _prep_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        vwap_df = session_vwap_with_bands(df)
        df['vwap'] = vwap_df['vwap']
        df['vwap_std'] = vwap_df['vwap_std']
        df['z_score'] = np.where(df['vwap_std'] > 0, (df['close'] - df['vwap']) / df['vwap_std'], 0.0)
        df['rsi_14'] = rsi(df['close'], 14)
        df['ema_200'] = ema(df['close'], 200)
        df['atr_14'] = atr(df, 14)
        return df

    def generate_signal(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < self.min_bars_required:
            return SignalResult("NEUTRAL", 0.0, f"Insufficient data (need {self.min_bars_required} bars)")
            
        df = self._prep_data(df)
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        if pd.isna(curr['ema_200']) or pd.isna(curr['vwap']):
            return SignalResult("NEUTRAL", 0.0, "Insufficient data for indicators")
            
        long_reclaim = (curr['close'] > prev['close']) and ((curr['close'] - curr['low']) > (curr['high'] - curr['close']))
        short_rejection = (curr['close'] < prev['close']) and ((curr['high'] - curr['close']) > (curr['close'] - curr['low']))
        
        is_long = (-2.0 <= curr['z_score'] <= -1.5) and (curr['rsi_14'] < 35) and long_reclaim and (curr['close'] > curr['ema_200'])
        is_short = (1.5 <= curr['z_score'] <= 2.0) and (curr['rsi_14'] > 65) and short_rejection and (curr['close'] < curr['ema_200'])
        
        if is_long:
            std_below = abs(curr['z_score'])
            margin = min(40, max(0, (std_below - 1.5) * 80))
            conf = 60 + margin
            stop = curr['low'] - curr['atr_14']
            return SignalResult("BUY", conf, "VWAP Below -1.5 + Reclaim + Uptrend", stop_price=stop)
            
        if is_short:
            std_above = curr['z_score']
            margin = min(40, max(0, (std_above - 1.5) * 80))
            conf = 60 + margin
            stop = curr['high'] + curr['atr_14']
            return SignalResult("SELL", conf, "VWAP Above 1.5 + Rejection + Downtrend", stop_price=stop)
            
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
        
        for i in range(1, len(test_df)):
            curr = test_df.iloc[i-1]
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
                
            # 2. Track intra-bar price action
            if in_trade:
                bars_held += 1
                closed = False
                
                hit_stop = (trade_dir == 1 and bar['low'] <= stop_price) or (trade_dir == -1 and bar['high'] >= stop_price)
                hit_target = (trade_dir == 1 and bar['high'] >= bar['vwap']) or (trade_dir == -1 and bar['low'] <= bar['vwap'])
                
                if hit_stop and hit_target:
                    hit_target = False
                    
                if hit_stop:
                    if trade_dir == 1:
                        actual_fill = min(bar['open'], stop_price)
                        exit_price = actual_fill * (1 - config.slippage) - (actual_fill * config.commission)
                    else:
                        actual_fill = max(bar['open'], stop_price)
                        exit_price = actual_fill * (1 + config.slippage) + (actual_fill * config.commission)
                    closed = True
                elif hit_target:
                    if trade_dir == 1:
                        actual_fill = max(bar['open'], bar['vwap'])
                        exit_price = actual_fill * (1 - config.slippage) - (actual_fill * config.commission)
                    else:
                        actual_fill = min(bar['open'], bar['vwap'])
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
                if pd.isna(bar['ema_200']) or pd.isna(bar['vwap']): continue
                
                long_reclaim = (bar['close'] > curr['close']) and ((bar['close'] - bar['low']) > (bar['high'] - bar['close']))
                short_rejection = (bar['close'] < curr['close']) and ((bar['high'] - bar['close']) > (bar['close'] - bar['low']))
                
                long_cond = (-2.0 <= bar['z_score'] <= -1.5) and (bar['rsi_14'] < 35) and long_reclaim and (bar['close'] > bar['ema_200'])
                short_cond = (1.5 <= bar['z_score'] <= 2.0) and (bar['rsi_14'] > 65) and short_rejection and (bar['close'] < bar['ema_200'])
                
                if long_cond:
                    pending_entry = True
                    pending_dir = 1
                    stop_price = bar['low'] - bar['atr_14']
                elif short_cond:
                    pending_entry = True
                    pending_dir = -1
                    stop_price = bar['high'] + bar['atr_14']
                    
            if in_trade and not pending_exit:
                if bars_held >= 12:
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
        sharpe = (returns.mean() / returns.std()) * np.sqrt(365 * 24) if len(returns)>2 and returns.std() != 0 else 0.0
        
        return BacktestResult(win_rate, pf, expectancy, max_dd, sharpe, avg_r, len(trades), eq_s, False)
