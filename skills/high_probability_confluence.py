import pandas as pd
import numpy as np
import datetime
from typing import Literal
from skills.base import BaseSignalSkill, SignalResult, BacktestConfig, BacktestResult
from skills.utils import rsi, ema, atr, volume_sma, adx, macd

SKILL_VERSION = "1.0.2"

class HighProbability_Confluence(BaseSignalSkill):
    '''
    High Probability Confluence Strategy.
    Fires only when >= 3 of 5 conditions align and total confidence >= 70.
    
    Confidence Score Formula:
    Base Score: 36 (3 conditions), 48 (4 conditions), 60 (5 conditions).
    Margin Bonus (Max 40): min(40, max(0, (ADX - 22) * 2))

    ========================================================================
    KNOWN LIMITATIONS & VALIDATION RESULTS (v1.0.2)
    ========================================================================
    - NO EDGE DETECTED: Validated on 5,000 days of SPY data. Resulted in 
      PF 0.45 In-Sample and PF 0.53 Out-of-Sample.
    - MAX DRAWDOWN WARNING: Despite the 'High Probability' confluence gate,
      the In-Sample max drawdown was an unacceptable 18.37%. This is a severe 
      number for a setup branded as high-probability.
    - ROOT CAUSE: The reward:risk math requires a ~43% win rate to break even 
      (1.33:1 based on 2.0 ATR Target / 1.5 ATR Stop). The actual win rate was 
      31-35%. The static, non-trailing exit mechanics cause natural market noise 
      to stop out perfectly valid entries before they reach the 2R target.
    ========================================================================
    '''
    min_bars_required: int = 200 # Needed for EMA 200
    
    def _prep_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Core Indicators
        df['ema_50'] = ema(df['close'], 50)
        df['ema_200'] = ema(df['close'], 200)
        df['adx_14'] = adx(df, 14)
        df['rsi_14'] = rsi(df['close'], 14)
        _, _, df['macd_hist'] = macd(df['close'])
        
        df['atr_14'] = atr(df, 14)
        df['atr_sma_20'] = df['atr_14'].rolling(window=20).mean()
        df['vol_sma_20'] = volume_sma(df['volume'], 20)
        
        # Structure Lookback (Max High / Min Low of previous 10 bars)
        df['struct_high_10'] = df['high'].shift(1).rolling(window=10).max()
        df['struct_low_10'] = df['low'].shift(1).rolling(window=10).min()
        
        # --- 5 Confluence Conditions ---
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
        
        return df

    def generate_signal(self, df: pd.DataFrame) -> SignalResult:
        if len(df) < self.min_bars_required:
            return SignalResult("NEUTRAL", 0.0, f"Insufficient data (need {self.min_bars_required} bars)")
            
        df = self._prep_data(df)
        curr = df.iloc[-1]
        
        if pd.isna(curr['ema_200']) or pd.isna(curr['adx_14']):
            return SignalResult("NEUTRAL", 0.0, "Insufficient data for indicators")
            
        is_long = (curr['long_confluence'] >= 3) and (curr['c_trend_long'] or curr['c_struct_long'])
        is_short = (curr['short_confluence'] >= 3) and (curr['c_trend_short'] or curr['c_struct_short'])
        
        if is_long or is_short:
            match_count = curr['long_confluence'] if is_long else curr['short_confluence']
            
            if match_count == 3: base_score = 36
            elif match_count == 4: base_score = 48
            else: base_score = 60
                
            margin = min(40, max(0, (curr['adx_14'] - 22) * 2))
            conf = base_score + margin
            
            if conf < 70:
                return SignalResult("NEUTRAL", 0.0, f"Blocked: Score {conf:.1f} is below 70 threshold")
                
            if is_long:
                stop = curr['close'] - (1.5 * curr['atr_14'])
                target = curr['close'] + (2.0 * curr['atr_14'])
                return SignalResult("BUY", conf, f"Long Confluence ({match_count}/5)", stop_price=stop, target_price=target)
                
            if is_short:
                stop = curr['close'] + (1.5 * curr['atr_14'])
                target = curr['close'] - (2.0 * curr['atr_14'])
                return SignalResult("SELL", conf, f"Short Confluence ({match_count}/5)", stop_price=stop, target_price=target)
            
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
        target_price = 0.0
        
        trades = []
        equity = 10000.0
        equity_curve = []
        
        for i in range(len(test_df)):
            bar = test_df.iloc[i]
            
            if pending_entry:
                trade_dir = pending_dir
                in_trade = True
                pending_entry = False
                
                if trade_dir == 1:
                    entry_price = bar['open'] * (1 + config.slippage) + (bar['open'] * config.commission)
                else:
                    entry_price = bar['open'] * (1 - config.slippage) - (bar['open'] * config.commission)
                    
            if in_trade:
                closed = False
                
                hit_stop = (trade_dir == 1 and bar['low'] <= stop_price) or (trade_dir == -1 and bar['high'] >= stop_price)
                hit_target = (trade_dir == 1 and bar['high'] >= target_price) or (trade_dir == -1 and bar['low'] <= target_price)
                
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
                        actual_fill = max(bar['open'], target_price)
                        exit_price = actual_fill * (1 - config.slippage) - (actual_fill * config.commission)
                    else:
                        actual_fill = min(bar['open'], target_price)
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
                    
            if not in_trade and not pending_entry:
                if pd.isna(bar['ema_200']) or pd.isna(bar['adx_14']): continue
                
                is_long = (bar['long_confluence'] >= 3) and (bar['c_trend_long'] or bar['c_struct_long'])
                is_short = (bar['short_confluence'] >= 3) and (bar['c_trend_short'] or bar['c_struct_short'])
                
                if is_long or is_short:
                    match_count = bar['long_confluence'] if is_long else bar['short_confluence']
                    
                    if match_count == 3: base_score = 36
                    elif match_count == 4: base_score = 48
                    else: base_score = 60
                        
                    margin = min(40, max(0, (bar['adx_14'] - 22) * 2))
                    conf = base_score + margin
                    
                    if conf >= 70:
                        pending_entry = True
                        if is_long:
                            pending_dir = 1
                            stop_price = bar['close'] - (1.5 * bar['atr_14'])
                            target_price = bar['close'] + (2.0 * bar['atr_14'])
                        else:
                            pending_dir = -1
                            stop_price = bar['close'] + (1.5 * bar['atr_14'])
                            target_price = bar['close'] - (2.0 * bar['atr_14'])
                    
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
