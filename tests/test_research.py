import pandas as pd
from src.core.backtester import Backtester
from src.analysis.research import ResearchEngine
from src.strategies.base import BaseStrategy
from src.core.experiments import ExperimentJournal

class MockResearchStrategy(BaseStrategy):
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['entry_signal'] = 1
        return df

def test_research_engine(monkeypatch):
    bt = Backtester()
    df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Mock the backtester run method to simulate passing/failing metrics deterministically
    def mock_run(self, data, strategy):
        val = strategy.parameters.get("threshold", 0)
        if val > 10:
            return {"metrics": {"expectancy": 5.0, "profit_factor": 2.0, "win_rate": 0.6}}
        else:
            return {"metrics": {"expectancy": -1.0, "profit_factor": 0.5, "win_rate": 0.3}}
            
    monkeypatch.setattr(Backtester, "run", mock_run)
    
    engine = ResearchEngine(bt, df)
    base_strat = MockResearchStrategy("Res_01", "1.0", {"threshold": 5})
    
    # Test a failure mutation (threshold 8 < 10, yields negative expectancy)
    res_fail = engine.run_mutation_experiment(base_strat, "threshold", 8)
    assert res_fail["status"] == "REJECTED_NEGATIVE_EXPECTANCY"
    assert res_fail["robustness_passed"] is False
    
    # Test a passing mutation (threshold 15 > 10, yields positive expectancy)
    res_pass = engine.run_mutation_experiment(base_strat, "threshold", 15)
    assert res_pass["status"] == "PROMOTED_TO_WALK_FORWARD"
    assert res_pass["robustness_passed"] is True
