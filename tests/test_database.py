import os
import sqlite3
from src.core.database import init_db, DB_PATH

def test_db_initialization():
    # Remove the DB if it exists to test clean initialization
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    init_db()
    assert os.path.exists(DB_PATH)
    
    # Check if table exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ohlcv'")
    table = cursor.fetchone()
    conn.close()
    
    assert table is not None
    assert table[0] == 'ohlcv'
