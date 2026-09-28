import sqlite3
import json
from src.core.database import get_db_connection
from src.core.logger import logger
from typing import Dict, Any

class ExperimentJournal:
    """Stores the results of all strategy mutations and hypotheses, especially the failures."""
    
    @staticmethod
    def init_experiment_table():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiment_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    base_strategy_id TEXT NOT NULL,
                    new_version TEXT NOT NULL,
                    parameter_mutations TEXT NOT NULL,
                    expectancy REAL,
                    win_rate REAL,
                    profit_factor REAL,
                    robustness_passed BOOLEAN,
                    status TEXT NOT NULL,
                    reasoning TEXT
                )
            """)
            conn.commit()

    @staticmethod
    def log_experiment(exp_data: Dict[str, Any]):
        ExperimentJournal.init_experiment_table()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO experiment_journal 
                (base_strategy_id, new_version, parameter_mutations, expectancy, win_rate, profit_factor, robustness_passed, status, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exp_data.get("base_strategy_id"),
                exp_data.get("new_version"),
                json.dumps(exp_data.get("parameter_mutations", {})),
                exp_data.get("expectancy", 0.0),
                exp_data.get("win_rate", 0.0),
                exp_data.get("profit_factor", 0.0),
                exp_data.get("robustness_passed", False),
                exp_data.get("status"), # e.g., 'REJECTED_FRAGILE', 'PROMOTED'
                exp_data.get("reasoning", "")
            ))
            conn.commit()
            logger.info(f"Experiment logged: {exp_data.get('new_version')} -> {exp_data.get('status')}")
