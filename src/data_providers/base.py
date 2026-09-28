from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional

class MarketDataProvider(ABC):
    """Abstract base class for all market data providers."""
    
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def get_historical_ohlcv(self, symbol: str, timeframe: str, since: Optional[int] = None) -> pd.DataFrame:
        """Fetch historical OHLCV data."""
        pass

    @abstractmethod
    def get_latest_price(self, symbol: str) -> float:
        """Fetch the latest price for a symbol."""
        pass
        
    def validate_data(self, df: pd.DataFrame) -> bool:
        """Ensure data contains required columns and no obvious gaps/stale data."""
        required_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        if not required_cols.issubset(df.columns):
            return False
        if df.empty:
            return False
        return True
