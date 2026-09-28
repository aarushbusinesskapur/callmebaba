import pandas as pd
from src.core.backtester import Backtester
def run_trace():
    # Mock 5 bars of data
    data = {
        'timestamp': pd.date_range('2025-01-01', periods=5, freq='1h', tz='UTC'),
        'open': [100, 105, 110, 115, 120],
        'high': [105, 112, 118, 125, 110],
        'low':  [95,  104, 108, 105, 90],
        'close':[105, 110, 115, 105, 95],
        'volume': [100]*5
    }
    df = pd.DataFrame(data)
    
    # We will write out the exact evaluation sequence
    
    with open("trailing_stop_trace.txt", "w") as f:
        f.write("BAR-BY-BAR TRAILING STOP TRACE\n")
        f.write("===============================\n")
        
        # Simulating the internal loop of backtester to print exact state BEFORE and AFTER evaluation
        signals = df
        
        position = 1 # Long
        entry_price = 100.0
        trailing_sl = 90.0
        
        for i in range(1, len(signals)):
            row = signals.iloc[i]
            high = row['high']
            low = row['low']
            
            f.write(f"\n--- Bar {i} ({row['timestamp']}) ---\n")
            f.write(f"Price Action: High {high}, Low {low}\n")
            f.write(f"Stop Level AT START of bar: {trailing_sl}\n")
            
            # 1. EVALUATION PHASE (Check against existing stop)
            hit_stop = False
            if position == 1 and low <= trailing_sl:
                hit_stop = True
                f.write(f"-> EVALUATION: Low ({low}) hit Stop ({trailing_sl}). Position CLOSED.\n")
                break
            else:
                f.write(f"-> EVALUATION: Low ({low}) > Stop ({trailing_sl}). Position HELD.\n")
                
            # 2. UPDATE PHASE (Update trailing stop using this bar's high)
            new_sl = high - 10.0 # Mock 10-point trailing distance
            if new_sl > trailing_sl:
                trailing_sl = new_sl
                f.write(f"-> UPDATE: New High ({high}) pulled Stop up to {trailing_sl}\n")
            else:
                f.write(f"-> UPDATE: Stop remains at {trailing_sl}\n")
                
    print("Wrote trailing_stop_trace.txt")

if __name__ == "__main__":
    run_trace()
