from src.data_providers.tradingview import TradingViewProvider
from src.data_providers.polymarket import PolymarketProvider

def test_tradingview_provider():
    provider = TradingViewProvider()
    assert provider.name == "TradingView"

def test_polymarket_provider():
    provider = PolymarketProvider()
    assert provider.name == "Polymarket"
    probs = provider.get_event_probabilities("mock-event")
    assert "Yes" in probs
    assert "No" in probs
