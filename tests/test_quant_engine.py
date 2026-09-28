import pandas as pd
from src.core.metrics import calculate_performance_metrics
from src.core.backtester import Backtester
from src.strategies.base import BaseStrategy

class MockStrategy(BaseStrategy):
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['entry_signal'] = 1
        return df

def test_metrics_calculation():
    # Simulate a trades log
    trades = pd.DataFrame([
        {'pnl': 150.0, 'pnl_percent': 1.5, 'duration': 10, 'is_win': True},
        {'pnl': -50.0, 'pnl_percent': -0.5, 'duration': 5, 'is_win': False},
        {'pnl': 200.0, 'pnl_percent': 2.0, 'duration': 15, 'is_win': True}
    ])
    
    metrics = calculate_performance_metrics(trades)
    assert metrics['total_trades'] == 3
    assert metrics['win_rate'] == round(2/3, 4)
    assert metrics['total_pnl'] == 300.0
    assert metrics['profit_factor'] == 350.0 / 50.0

def test_backtester_initialization():
    strategy = MockStrategy("TEST_01", "1.0", {"ma": 20})
    backtester = Backtester()
    
    # Using an empty OHLCV dataframe
    df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    results = backtester.run(df, strategy)
    
    assert results['metrics']['total_trades'] == 0
