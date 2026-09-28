import time
import sys
from tier_a_15m_live import run_tier_a_15m, get_signal_count

def main():
    print("Starting Tier A (15m — untested timeframe) Polling Loop...")
    
    cycle = 1
    while True:
        if get_signal_count() >= 5:
            print("Signal limit of 5 reached. Loop stopping permanently.")
            sys.exit(0)
            
        print(f"\n--- 15m Cycle {cycle} ---")
        try:
            run_tier_a_15m()
        except SystemExit as e:
            if e.code == 0:
                print("Signal limit reached inside executor. Exiting loop.")
                sys.exit(0)
            else:
                print(f"Executor exited with code {e.code}")
        except Exception as e:
            print(f"Loop Error: {str(e)}")
            
        # The user requested to "Poll every 15 minutes, checking for a newly closed 15m candle each time."
        print("Cycle complete. Sleeping for 15 minutes (900 seconds)...")
        time.sleep(900)
        cycle += 1

if __name__ == "__main__":
    main()
