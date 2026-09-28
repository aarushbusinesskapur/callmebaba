from typing import Dict, Any, List

class TargetCalculator:
    """Calculates Stop Loss and Take Profit targets based on volatility or structure."""
    
    @staticmethod
    def calculate_targets(entry: float, direction: str, atr: float = None, risk_reward: float = 2.0) -> Dict[str, float]:
        """
        Calculates strict targets. 
        In production, ATR or structural swing highs/lows define the base risk amount.
        """
        risk_pct = 0.02 # Fallback 2% risk if no structural data provided
        if atr is not None and entry > 0:
            risk_amt = atr * 1.5
        else:
            risk_amt = entry * risk_pct
            
        if direction == "LONG":
            sl = entry - risk_amt
            tp1 = entry + (risk_amt * 1.0) # Conservative nearby objective
            tp2 = entry + (risk_amt * 2.0) # Primary objective
            tp3 = entry + (risk_amt * 3.0) # Extended objective
        else:
            sl = entry + risk_amt
            tp1 = entry - (risk_amt * 1.0)
            tp2 = entry - (risk_amt * 2.0)
            tp3 = entry - (risk_amt * 3.0)
            
        return {
            "entry": round(entry, 4),
            "sl": round(sl, 4),
            "tp1": round(tp1, 4),
            "tp2": round(tp2, 4),
            "tp3": round(tp3, 4)
        }

class SignalFormatter:
    """Formats the raw signal data into the strict AI TRADING SIGNAL block."""
    
    @staticmethod
    def format_signal(signal_data: Dict[str, Any]) -> str:
        t = signal_data.get("targets", {})
        
        return f"""━━━━━━━━━━━━━━━━━━━━━━ AI TRADING SIGNAL ━━━━━━━━━━━━━━━━━━━━━━
Asset: {signal_data.get('symbol')}
Direction: {signal_data.get('direction')}
Market: {signal_data.get('provider', 'Unknown')}
Strategy: {signal_data.get('strategy_id')}
Timeframe: {signal_data.get('timeframe')}

ENTRY: 
Entry zone: {t.get('entry')}

STOP LOSS:
SL: {t.get('sl')}

TAKE PROFIT:
TP1: {t.get('tp1')}
TP2: {t.get('tp2')}
TP3: {t.get('tp3')}

RISK / REWARD:
R:R: 1:{signal_data.get('rr_ratio', 2.0)}

SIGNAL QUALITY: {signal_data.get('quality_score', 0)}/100
MARKET REGIME: {signal_data.get('regime')}

WARNINGS:
- ADVISORY — MANUAL EXECUTION ONLY
"""
