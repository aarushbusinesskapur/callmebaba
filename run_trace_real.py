import os
import sys
import pandas as pd
sys.path.append(os.path.dirname(__file__))

from src.core.backtester import Backtester
from src.strategies.base import BaseStrategy

class SimpleTraceStrategy(BaseStrategy):
    def generate_signals(self, df):
        df = df.copy()
        df['entry_signal'] = 0
        df['exit_signal'] = 0
        df['sl'] = 0.0
        df['tp'] = 0.0
        
        # Enter Long on the first bar
        df.loc[0, 'entry_signal'] = 1
        df.loc[0, 'sl'] = df.loc[0, 'close'] - 1000 # Stop loss 1000 points away
        
        # Set a trailing stop distance
        df['trailing_sl'] = 500 # 500 point trailing stop
        return df

def run_trace():
    print("Running REAL Backtester instance to verify trailing stop logic...")
    
    # Generate 10 mock bars mimicking BTC price action
    data = {
        'timestamp': pd.date_range('2025-01-01', periods=10, freq='1h', tz='UTC'),
        'open':  [90000, 91000, 91500, 92000, 91800, 93000, 93500, 93200, 91000, 90000],
        'high':  [91500, 92000, 92500, 92500, 93500, 94000, 94000, 93500, 91500, 90500],
        'low':   [89500, 90500, 91000, 91500, 91500, 92500, 93000, 91000, 89000, 88000],
        'close': [91000, 91500, 92000, 91800, 93000, 93500, 93200, 91000, 90000, 89000],
        'volume': [100]*10
    }
    df = pd.DataFrame(data)
    
    # Run the real Backtester
    bt = Backtester(initial_capital=10000.0)
    bt.fee_rate = 0.0
    strat = SimpleTraceStrategy("TraceStrat", "1.0", {})
    
    print("\n--- BEGIN BACKTESTER EXECUTION ---")
    bt.run(df, strat)
    print("--- END BACKTESTER EXECUTION ---")

if __name__ == "__main__":
    run_trace()
