import time
from datetime import datetime, timezone
import sys
import os

# Append current directory to path
sys.path.append(os.path.dirname(__file__))
from tier_a_live import run_tier_a_live

def run_loop():
    print("Starting 3-Hour Unattended Loop Test for Tier A Scanner...")
    
    for i in range(1, 5): # Runs 4 times (Hours 0, 1, 2, 3)
        print(f"\n==================================================")
        print(f"CYCLE {i}/4 - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"==================================================")
        
        try:
            run_tier_a_live()
        except Exception as e:
            print(f"Error during cycle {i}: {e}")
            
        if i < 4:
            print(f"\nCycle {i} complete. Sleeping for 1 hour...")
            time.sleep(3600) # Sleep for 1 hour
            
    print("\n==================================================")
    print("3-Hour Unattended Loop Test Complete.")
    print("==================================================")

if __name__ == "__main__":
    # Ensure stdout is unbuffered for real-time logging
    sys.stdout.reconfigure(line_buffering=True)
    run_loop()
