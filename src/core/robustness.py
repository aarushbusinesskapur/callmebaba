import pandas as pd
import numpy as np
import copy
from typing import List, Dict, Any
from src.core.backtester import Backtester
from src.strategies.base import BaseStrategy
from src.core.logger import logger

class RobustnessTester:
    """Framework to test strategy fragility via perturbation and Monte Carlo."""
    
    def __init__(self, backtester: Backtester):
        self.backtester = backtester
        
    def test_slippage_variance(self, df: pd.DataFrame, strategy: BaseStrategy, iterations: int = 5) -> List[Dict[str, Any]]:
        """Runs the strategy with randomized adverse slippage penalties to detect fragility."""
        logger.info(f"Running slippage robustness test for {strategy.strategy_id}")
        results = []
        base_slippage = self.backtester.slippage_pct
        
        for i in range(iterations):
            # Temporarily modify backtester slippage (random between 1x and 3x base)
            test_slippage = base_slippage * np.random.uniform(1.0, 3.0)
            
            bt = Backtester(
                initial_capital=self.backtester.initial_capital,
                fee_rate=self.backtester.fee_rate,
                slippage_pct=test_slippage
            )
            
            res = bt.run(df, strategy)
            results.append({
                "iteration": i,
                "slippage_applied": test_slippage,
                "metrics": res["metrics"]
            })
            
        return results

    def test_parameter_perturbation(self, df: pd.DataFrame, strategy: BaseStrategy, param_key: str, variations: List[Any]) -> List[Dict[str, Any]]:
        """Tests if tiny parameter changes cause performance to collapse."""
        logger.info(f"Running parameter perturbation on '{param_key}' for {strategy.strategy_id}")
        results = []
        
        for val in variations:
            # Create a copy of the strategy to avoid mutating the original production config
            strat_copy = copy.copy(strategy)
            strat_copy.parameters = copy.deepcopy(strategy.parameters)
            strat_copy.parameters[param_key] = val
            strat_copy.version = f"{strategy.version}-pert-{val}"
            
            res = self.backtester.run(df, strat_copy)
            results.append({
                "perturbed_val": val,
                "metrics": res["metrics"]
            })
            
        return results
