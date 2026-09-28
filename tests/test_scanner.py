import pandas as pd
from src.analysis.regime import RegimeClassifier
from src.core.scanner import MarketScanner
from src.data_providers.base import MarketDataProvider
from src.strategies.base import BaseStrategy

class MockProvider(MarketDataProvider):
    def __init__(self):
        super().__init__("Mock")
    def get_historical_ohlcv(self, symbol, timeframe, since=None):
        df = pd.DataFrame({'close': [10.0 + (i * 0.5) for i in range(60)]})
        df['timestamp'] = range(60)
        df['open'] = df['close'] - 0.1
        df['high'] = df['close'] + 0.5
        df['low'] = df['close'] - 0.5
        df['volume'] = 100.0
        return df
    def get_latest_price(self, symbol):
        return 40.0

class MockTrendStrategy(BaseStrategy):
    def generate_signals(self, df):
        df['entry_signal'] = 1 # Always signal long
        return df

def test_regime_classifier():
    df = pd.DataFrame({'close': [10.0 + (i * 0.5) for i in range(60)]})
    regime = RegimeClassifier.detect_regime(df)
    assert "uptrend" in regime # Since price is strictly increasing

def test_market_scanner():
    provider = MockProvider()
    strat = MockTrendStrategy("Trend_01", "1.0", {})
    scanner = MarketScanner([provider], [strat])
    
    candidates = scanner.scan_market("BTCUSDT", "1H")
    assert len(candidates) == 1
    assert candidates[0]['strategy_id'] == "Trend_01"
    assert candidates[0]['direction'] == "LONG"
    assert candidates[0]['score'] > 50 # Should receive bonus for long in uptrend
