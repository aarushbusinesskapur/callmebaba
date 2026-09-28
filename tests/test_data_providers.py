import pandas as pd
from src.data_providers.binance import BinanceProvider
from src.data_providers.forex import ForexProvider

def test_binance_provider():
    provider = BinanceProvider()
    assert provider.name == "Binance"
    df = provider.get_historical_ohlcv("BTCUSDT", "1h")
    assert provider.validate_data(df) is False # Empty dataframe should fail validation
    
    # Test valid structure validation
    valid_df = pd.DataFrame([{
        'timestamp': 1600000000,
        'open': 10000.0,
        'high': 10100.0,
        'low': 9900.0,
        'close': 10050.0,
        'volume': 100.0
    }])
    assert provider.validate_data(valid_df) is True

def test_forex_provider():
    provider = ForexProvider()
    assert provider.name == "Forex"
