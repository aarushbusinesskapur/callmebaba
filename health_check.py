import sys
import os

def check_environment():
    print("--- Quantitative Research System Health Check ---")
    
    # 1. Check Python version
    print(f"Python Version: {sys.version.split(' ')[0]}")
    if sys.version_info < (3, 10):
        print("[FAIL] Python 3.10+ is required.")
        sys.exit(1)
    else:
        print("[PASS] Python version is suitable.")

    # 2. Check virtual environment
    if not (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)):
        print("[WARNING] Not running inside a virtual environment.")
    else:
        print("[PASS] Running inside a virtual environment.")

    # 3. Check project structure
    expected_dirs = ['data', 'src/core', 'src/data_providers', 'src/strategies', 'src/analysis', 'tests']
    missing_dirs = []
    for d in expected_dirs:
        if not os.path.isdir(d):
            missing_dirs.append(d)
    
    if missing_dirs:
        print(f"[FAIL] Missing directories: {', '.join(missing_dirs)}")
        sys.exit(1)
    else:
        print("[PASS] Project structure is intact.")

    print("--- Health Check Passed ---")

if __name__ == "__main__":
    check_environment()
