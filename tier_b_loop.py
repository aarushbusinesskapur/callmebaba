import time
import sys
from tier_b_live import run_tier_b_live

def main():
    print("Starting Tier B (Phase 5) Unattended Loop Test...")
    print("Writing logs to tier_b_live_log.txt")
    
    cycle = 1
    while True:
        print(f"\n--- Cycle {cycle} ---")
        try:
            found_signal, found_anomaly = run_tier_b_live()
            
            if found_anomaly:
                print("ANOMALY DETECTED. Stopping loop and exiting to alert user.")
                sys.exit(1)
                
            if found_signal:
                print("SIGNAL DETECTED. Stopping loop and exiting to alert user.")
                sys.exit(0)
                
        except Exception as e:
            print(f"Critical Loop Error: {str(e)}")
            sys.exit(1)
            
        print("Cycle complete. Sleeping for 1 hour...")
        time.sleep(3600)
        cycle += 1

if __name__ == "__main__":
    main()
