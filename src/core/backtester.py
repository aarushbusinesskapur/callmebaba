import pandas as pd
from src.strategies.base import BaseStrategy
from src.core.metrics import calculate_performance_metrics
from src.core.logger import logger

class Backtester:
    """Realistic backtesting framework with fee, slippage, strict position sizing, and trailing stops."""
    
    def __init__(self, initial_capital: float = 10000.0, asset: str = "BTC-USD", risk_per_trade: float = 0.02):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.fixed_risk = False
        self.asset = asset
        
        # Asset-Class Aware Fee Scaling
        if "=X" in asset:
            # Forex (ECN/Retail model): 0% commission, ~1 pip slippage per side (2 pips round turn)
            self.fee_rate = 0.0
            self.slippage_pct = 0.0001
            self.is_futures = False
            print(f"[{asset}] Using Forex ECN costs (0% fee, ~1 pip slippage per side)")
        else:
            # Crypto Perpetual Futures: 0.04% taker fee, 0.05% slippage
            self.fee_rate = 0.0004 
            self.slippage_pct = 0.0005
            self.is_futures = True
            print(f"[{asset}] Using Binance Perp costs (0.04% fee, 0.05% slippage, funding payments enabled)")
        
    def run(self, df: pd.DataFrame, strategy: BaseStrategy) -> dict:
        signals = strategy.generate_signals(df)
        trades_list = []
        
        in_position = False
        position_size = 0.0
        current_capital = self.initial_capital
        
        entry_price = 0.0
        sl = 0.0
        direction = 0 # 1 for LONG, -1 for SHORT
        
        # Trailing Stop variables
        highest_price = 0.0
        lowest_price = float('inf')
        trailing_sl_dist = 0.0
        use_trailing_stop = strategy.parameters.get("use_trailing_stop", True)
        atr_multiplier = strategy.parameters.get("trailing_atr_multiplier", 2.0)
        
        for idx, row in signals.iterrows():
            if current_capital <= 10.0 and not self.fixed_risk:
                break # Margin call / Account blown. Halt trading.
                
            if not in_position and row.get('entry_signal', 0) != 0:
                direction = row['entry_signal']
                in_position = True
                entry_time = row['timestamp'] if 'timestamp' in row else idx
                
                # Apply slippage to entry
                if direction == 1:
                    entry_price = row['close'] * (1 + self.slippage_pct)
                else:
                    entry_price = row['close'] * (1 - self.slippage_pct)
                
                current_atr = row.get('atr')
                if pd.isna(current_atr) or current_atr == 0:
                    current_atr = entry_price * 0.02
                    
                trailing_sl_dist = current_atr * atr_multiplier
                
                tp = row.get('tp2', 0)
                funding_paid = 0.0
                
                # Initial SL setup
                if use_trailing_stop:
                    if direction == 1:
                        sl = entry_price - trailing_sl_dist
                        highest_price = entry_price
                    else:
                        sl = entry_price + trailing_sl_dist
                        lowest_price = entry_price
                else:
                    sl = row.get('sl', 0)
                    
                # Position Sizing
                risk_amount = (self.initial_capital if self.fixed_risk else current_capital) * self.risk_per_trade
                risk_per_unit = abs(entry_price - sl)
                if risk_per_unit <= 0:
                    in_position = False # Invalid setup
                    continue
                    
                position_size = risk_amount / risk_per_unit
                
                # Cap position size to maximum realistic leverage
                max_leverage = 3.0 # Max 3x leverage for standard margin trading
                base_capital = self.initial_capital if self.fixed_risk else current_capital
                max_position_size = (base_capital * max_leverage) / entry_price
                position_size = min(position_size, max_position_size)
                bars_held = 0
                
            elif in_position:
                bars_held += 1
                
                # Apply Funding Payments if this is a perpetual futures contract
                if self.is_futures and 'fundingRate' in row and not pd.isna(row['fundingRate']):
                    fr = row['fundingRate']
                    if fr != 0:
                        payment = position_size * row['close'] * fr * (-direction)
                        funding_paid += payment
                        
                # Time-based exit check
                time_stop_bars = row.get('time_stop_bars', 0)
                if time_stop_bars > 0 and bars_held >= time_stop_bars:
                    exit_price = row['close']
                    gross_pnl = (exit_price - entry_price) * position_size if direction == 1 else (entry_price - exit_price) * position_size
                    fees = (entry_price * position_size * self.fee_rate) + (exit_price * position_size * self.fee_rate)
                    net_pnl = gross_pnl - fees + funding_paid
                    trades_list.append({"entry_time": entry_time, "exit_time": idx, "direction": "LONG" if direction == 1 else "SHORT", "entry_price": entry_price, "sl": sl, "tp": tp, "exit_price": exit_price, "exit_reason": "TIME", "pnl": net_pnl, "is_win": net_pnl > 0})
                    current_capital += net_pnl
                    in_position = False
                    continue
                        
                if direction == 1:
                    # Dynamic Exit Check (LONG)
                    if row.get('exit_long', False):
                        exit_price = row['close'] * (1 - self.slippage_pct)
                        gross_pnl = (exit_price - entry_price) * position_size
                        fees = (entry_price * position_size * self.fee_rate) + (exit_price * position_size * self.fee_rate)
                        net_pnl = gross_pnl - fees + funding_paid
                        trades_list.append({"entry_time": entry_time, "exit_time": idx, "direction": "LONG", "entry_price": entry_price, "sl": sl, "tp": tp, "exit_price": exit_price, "exit_reason": "DYN_EXIT", "pnl": net_pnl, "is_win": net_pnl > 0})
                        current_capital += net_pnl
                        in_position = False
                        continue
                        
                    # INSTRUMENTATION: Print evaluation state BEFORE updating
                    print(f"TRACE [{idx}]: Position=LONG | Low={row['low']} | Current SL={sl}")
                    
                    # Exit Check (SL hit) - Evaluated using the SL value set prior to this bar
                    if row['low'] <= sl:
                        print(f"TRACE [{idx}]: -> EVALUATION: Low <= SL. Hit SL. Position CLOSED.")
                        exit_price = sl * (1 - self.slippage_pct)
                        gross_pnl = (exit_price - entry_price) * position_size
                        fees = (entry_price * position_size * self.fee_rate) + (exit_price * position_size * self.fee_rate)
                        net_pnl = gross_pnl - fees + funding_paid
                        trades_list.append({"entry_time": entry_time, "exit_time": idx, "direction": "LONG", "entry_price": entry_price, "sl": sl, "tp": tp, "exit_price": exit_price, "exit_reason": "SL", "pnl": net_pnl, "is_win": net_pnl > 0})
                        current_capital += net_pnl
                        in_position = False
                        
                    # Trailing Stop Logic (LONG) - Updates SL for the *next* bar
                    elif use_trailing_stop and row['high'] > highest_price:
                        highest_price = row['high']
                        new_sl = highest_price - trailing_sl_dist
                        if new_sl > sl:
                            sl = new_sl
                            print(f"TRACE [{idx}]: -> UPDATE: New High ({highest_price}) pulled Stop up to {sl}")
                        else:
                            print(f"TRACE [{idx}]: -> UPDATE: Stop remains at {sl}")
                        
                    # Exit Check (TP hit)
                    current_tp = row.get('dynamic_tp', tp)
                    if current_tp > 0 and row['high'] >= current_tp:
                        exit_price = current_tp * (1 - self.slippage_pct)
                        gross_pnl = (exit_price - entry_price) * position_size
                        fees = (entry_price * position_size * self.fee_rate) + (exit_price * position_size * self.fee_rate)
                        net_pnl = gross_pnl - fees + funding_paid
                        trades_list.append({"entry_time": entry_time, "exit_time": idx, "direction": "LONG", "entry_price": entry_price, "sl": sl, "tp": current_tp, "exit_price": exit_price, "exit_reason": "TP", "pnl": net_pnl, "is_win": net_pnl > 0})
                        current_capital += net_pnl
                        in_position = False
                        
                elif direction == -1:
                    # Dynamic Exit Check (SHORT)
                    if row.get('exit_short', False):
                        exit_price = row['close'] * (1 + self.slippage_pct)
                        gross_pnl = (entry_price - exit_price) * position_size
                        fees = (entry_price * position_size * self.fee_rate) + (exit_price * position_size * self.fee_rate)
                        net_pnl = gross_pnl - fees + funding_paid
                        trades_list.append({"entry_time": entry_time, "exit_time": idx, "direction": "SHORT", "entry_price": entry_price, "sl": sl, "tp": tp, "exit_price": exit_price, "exit_reason": "DYN_EXIT", "pnl": net_pnl, "is_win": net_pnl > 0})
                        current_capital += net_pnl
                        in_position = False
                        continue
                        
                    # Exit Check (SL hit) - Evaluated using the SL value set prior to this bar
                    if row['high'] >= sl:
                        exit_price = sl * (1 + self.slippage_pct)
                        gross_pnl = (entry_price - exit_price) * position_size
                        fees = (entry_price * position_size * self.fee_rate) + (exit_price * position_size * self.fee_rate)
                        net_pnl = gross_pnl - fees + funding_paid
                        trades_list.append({"entry_time": entry_time, "exit_time": idx, "direction": "SHORT", "entry_price": entry_price, "sl": sl, "tp": tp, "exit_price": exit_price, "exit_reason": "SL", "pnl": net_pnl, "is_win": net_pnl > 0})
                        current_capital += net_pnl
                        in_position = False
                        
                    # Trailing Stop Logic (SHORT) - Updates SL for the *next* bar
                    elif use_trailing_stop and row['low'] < lowest_price:
                        lowest_price = row['low']
                        new_sl = lowest_price + trailing_sl_dist
                        if new_sl < sl:
                            sl = new_sl
                        
                    # Exit Check (TP hit)
                    current_tp = row.get('dynamic_tp', tp)
                    if current_tp > 0 and row['low'] <= current_tp:
                        exit_price = current_tp * (1 + self.slippage_pct)
                        gross_pnl = (entry_price - exit_price) * position_size
                        fees = (entry_price * position_size * self.fee_rate) + (exit_price * position_size * self.fee_rate)
                        net_pnl = gross_pnl - fees + funding_paid
                        trades_list.append({"entry_time": entry_time, "exit_time": idx, "direction": "SHORT", "entry_price": entry_price, "sl": sl, "tp": current_tp, "exit_price": exit_price, "exit_reason": "TP", "pnl": net_pnl, "is_win": net_pnl > 0})
                        current_capital += net_pnl
                        in_position = False
                        
        trades_df = pd.DataFrame(trades_list, columns=['pnl', 'is_win']) if trades_list else pd.DataFrame()
        return {
            "metrics": calculate_performance_metrics(trades_df, self.initial_capital),
            "trades": trades_list
        }
