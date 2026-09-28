from src.core.notifications import ConsoleProvider, TelegramProvider
from src.core.daemon import QuantDaemon
from src.core.scanner import MarketScanner
from src.analysis.chief import ChiefAnalyst
from src.data_providers.binance import BinanceProvider
from src.strategies.base import BaseStrategy
import pandas as pd

class DummyStrategy(BaseStrategy):
    def generate_signals(self, df):
        # Prevent actually returning a signal to avoid triggering full pipeline in simple test
        df['entry_signal'] = 0
        return df

def test_notification_providers():
    console = ConsoleProvider()
    console.send("Test message")
    
    tg = TelegramProvider()
    assert tg.bot_token is None # Since we don't load real .env in tests
    tg.send("Test message") # Should just log a warning, not crash

def test_daemon_initialization():
    scanner = MarketScanner([BinanceProvider()], [DummyStrategy("D1", "1", {})])
    chief = ChiefAnalyst()
    daemon = QuantDaemon(scanner, chief, [ConsoleProvider()])
    
    # Run a single safe cycle
    daemon.run_cycle()
    assert daemon is not None
