import pandas as pd
from src.core.validation import DataSplitter
from src.core.robustness import RobustnessTester
from src.core.backtester import Backtester
from src.strategies.base import BaseStrategy

class MockStrategy(BaseStrategy):
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['entry_signal'] = 1
        return df

def test_standard_split():
    df = pd.DataFrame({'close': range(100)})
    train, val, test = DataSplitter.standard_split(df, 0.6, 0.2)
    assert len(train) == 60
    assert len(val) == 20
    assert len(test) == 20

def test_walk_forward_split():
    df = pd.DataFrame({'close': range(100)})
    splits = DataSplitter.walk_forward_split(df, n_splits=3, train_size_pct=0.7)
    
    assert len(splits) == 3
    # Step size should be int((100 * 0.3) / 3) = 10
    # First split: train 0-70, val 70-80
    assert len(splits[0][0]) == 70
    assert len(splits[0][1]) == 10
    
    # Second split: train 10-80, val 80-90
    assert len(splits[1][0]) == 70
    assert len(splits[1][1]) == 10

def test_robustness_tester():
    bt = Backtester()
    tester = RobustnessTester(bt)
    strat = MockStrategy("T1", "1.0", {"p": 1})
    df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    res_slippage = tester.test_slippage_variance(df, strat, iterations=2)
    assert len(res_slippage) == 2
    
    res_pert = tester.test_parameter_perturbation(df, strat, "p", [0.9, 1.1])
    assert len(res_pert) == 2
    assert res_pert[0]["perturbed_val"] == 0.9
