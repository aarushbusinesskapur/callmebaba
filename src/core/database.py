import sqlite3
import os
from contextlib import contextmanager
from typing import Generator
import pandas as pd

from src.core.logger import logger

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "market_data.db")

def init_db():
    """Initializes the database schema."""
    logger.info(f"Initializing database at {DB_PATH}")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # OHLCV table for resampled candles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                provider TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                UNIQUE(symbol, provider, timeframe, timestamp)
            )
        """)
        # Create an index on symbol and timestamp for fast range queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_query ON ohlcv (symbol, timeframe, timestamp)")
        conn.commit()

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Provides a transactional scope around a series of operations."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def save_candles(df: pd.DataFrame, table: str = "ohlcv"):
    """Saves a dataframe of candles to the database."""
    with get_db_connection() as conn:
        df.to_sql(table, conn, if_exists='append', index=False)
        logger.debug(f"Saved {len(df)} rows to {table}")
