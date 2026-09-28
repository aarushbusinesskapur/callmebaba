from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies. 
    Any logic change MUST result in a version increment."""
    
    def __init__(self, strategy_id: str, version: str, parameters: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.version = version
        self.parameters = parameters
        
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes OHLCV dataframe and appends signal columns.
        Expected appended columns: 
        - 'entry_signal' (1 for long, -1 for short, 0 for none)
        - 'stop_loss', 'tp1', 'tp2', 'tp3'
        """
        pass
