from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional
import pandas as pd

@dataclass
class SignalResult:
    signal: Literal["BUY", "SELL", "NEUTRAL"]
    confidence: float
    reason: str
    stop_price: Optional[float] = None
    target_price: Optional[float] = None

@dataclass
class BacktestConfig:
    risk_per_trade: float = 0.01        # Default 1% risk per trade
    max_position_pct: float = 0.20      # Cap position size to 20% of account max
    commission: float = 0.0005          # Default 0.05% commission
    slippage: float = 0.0005            # Default 0.05% slippage
    split_ratio: float = 0.70           # Train/Test split ratio (0.7 = 70% in-sample)

@dataclass
class BacktestResult:
    win_rate: float
    profit_factor: float
    expectancy: float
    max_drawdown: float
    sharpe_ratio: float
    avg_r: float
    total_trades: int
    equity_curve: pd.Series
    is_in_sample_only: bool

class BaseSignalSkill(ABC):
    min_bars_required: int = 0
    
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> SignalResult:
        pass

    @abstractmethod
    def backtest(self, df: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
        pass
