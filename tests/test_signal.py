from src.core.signal import TargetCalculator, SignalFormatter
from src.core.journal import SignalJournal
import sqlite3

def test_target_calculator():
    targets = TargetCalculator.calculate_targets(100.0, "LONG")
    assert targets["entry"] == 100.0
    assert targets["sl"] < 100.0
    assert targets["tp1"] > 100.0
    assert targets["tp3"] > targets["tp2"]

def test_signal_formatter():
    data = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "strategy_id": "Trend_01",
        "targets": TargetCalculator.calculate_targets(100.0, "LONG")
    }
    formatted = SignalFormatter.format_signal(data)
    assert "AI TRADING SIGNAL" in formatted
    assert "BTCUSDT" in formatted
    assert "ADVISORY" in formatted

def test_signal_journal():
    data = {
        "symbol": "ETHUSDT",
        "direction": "SHORT",
        "strategy_id": "MeanRev_01",
        "quality_score": 92.5,
        "regime": "weak downtrend",
        "targets": TargetCalculator.calculate_targets(2000.0, "SHORT")
    }
    SignalJournal.log_signal(data)
    
    # Verify insertion
    from src.core.database import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM signal_journal WHERE symbol='ETHUSDT' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row[2] == "ETHUSDT"
    assert row[3] == "MeanRev_01"
