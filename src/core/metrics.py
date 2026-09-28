import pandas as pd
from typing import Dict, Any

def calculate_performance_metrics(trades: pd.DataFrame, initial_capital: float = 10000.0) -> Dict[str, Any]:
    """Calculates professional quantitative metrics from a trades log."""
    if trades.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "expectancy": 0.0,
            "profit_factor": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_drawdown": 0.0,
            "total_pnl": 0.0
        }
        
    # Assume trades df has: 'pnl', 'pnl_percent', 'duration', 'is_win'
    wins = trades[trades['pnl'] > 0]
    losses = trades[trades['pnl'] < 0]
    
    total_trades = len(trades)
    win_rate = len(wins) / total_trades if total_trades > 0 else 0
    
    avg_win = wins['pnl'].mean() if not wins.empty else 0
    avg_loss = losses['pnl'].mean() if not losses.empty else 0
    
    # Expectancy = (Win Rate * Avg Win) + (Loss Rate * Avg Loss)
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
    
    # Profit factor
    gross_profit = wins['pnl'].sum()
    gross_loss = abs(losses['pnl'].sum())
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
    
    # Max Drawdown approximation based on cumulative PnL
    cumulative_pnl = trades['pnl'].cumsum()
    running_max = cumulative_pnl.cummax()
    drawdown = running_max - cumulative_pnl
    max_drawdown = drawdown.max()
    
    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 4),
        "expectancy": round(expectancy, 4),
        "profit_factor": round(profit_factor, 4),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "max_drawdown": round(max_drawdown, 4),
        "total_pnl": round(trades['pnl'].sum(), 4)
    }
