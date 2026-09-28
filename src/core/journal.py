import sqlite3
import json
from src.core.database import get_db_connection, DB_PATH
from src.core.logger import logger
from typing import Dict, Any

class SignalJournal:
    """Stores every generated setup into the system's persistent research history."""
    
    @staticmethod
    def init_journal_table():
        """Creates the signal journal table if it doesn't exist."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signal_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry REAL,
                    sl REAL,
                    tp1 REAL,
                    tp2 REAL,
                    tp3 REAL,
                    quality_score REAL,
                    regime TEXT,
                    raw_data TEXT,
                    state TEXT DEFAULT 'PUBLISHED'
                )
            """)
            conn.commit()
            
    @staticmethod
    def log_signal(signal_data: Dict[str, Any]):
        """Logs a new signal to the database for post-trade analysis."""
        SignalJournal.init_journal_table()
        
        t = signal_data.get("targets", {})
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO signal_journal 
                (symbol, strategy, direction, entry, sl, tp1, tp2, tp3, quality_score, regime, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_data.get("symbol"),
                signal_data.get("strategy_id"),
                signal_data.get("direction"),
                t.get("entry"),
                t.get("sl"),
                t.get("tp1"),
                t.get("tp2"),
                t.get("tp3"),
                signal_data.get("quality_score"),
                signal_data.get("regime"),
                json.dumps(signal_data)
            ))
            conn.commit()
            logger.info(f"Signal securely logged to research journal for {signal_data.get('symbol')}")
