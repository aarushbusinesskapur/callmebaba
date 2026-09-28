import pandas as pd
import copy
from typing import Dict, Any
from src.core.backtester import Backtester
from src.core.validation import DataSplitter
from src.core.robustness import RobustnessTester
from src.strategies.base import BaseStrategy
from src.core.experiments import ExperimentJournal
from src.core.logger import logger

class ResearchEngine:
    """The controlled self-improvement loop for strategy evolution."""
    
    def __init__(self, backtester: Backtester, df: pd.DataFrame):
        self.backtester = backtester
        self.df = df # Master historical dataset
        
    def run_mutation_experiment(self, base_strategy: BaseStrategy, target_param: str, new_value: Any) -> Dict[str, Any]:
        """
        Runs a strict pipeline to evaluate a single parameter mutation.
        Never modifies the original strategy directly.
        """
        logger.info(f"Starting research experiment on {base_strategy.strategy_id} mutating '{target_param}' to {new_value}")
        
        # 1. Isolate the mutation
        test_strat = copy.copy(base_strategy)
        test_strat.parameters = copy.deepcopy(base_strategy.parameters)
        test_strat.parameters[target_param] = new_value
        # Strict versioning rule
        test_strat.version = f"{base_strategy.version}-exp-{new_value}"
        
        # 2. Strict Data Splitting
        train, val, test = DataSplitter.standard_split(self.df)
        
        # 3. Development Phase (Train)
        train_res = self.backtester.run(train, test_strat)
        train_metrics = train_res["metrics"]
        
        # Enforce statistical significance (minimum 30 trades)
        if train_metrics.get("total_trades", 0) < 30:
            return self._finalize_experiment(base_strategy, test_strat, target_param, new_value, train_metrics, False, "INCONCLUSIVE_INSUFFICIENT_DATA", f"Only {train_metrics.get('total_trades')} trades. Need at least 30 for statistical significance.")
            
        if train_metrics.get("expectancy", 0) <= 0:
            return self._finalize_experiment(base_strategy, test_strat, target_param, new_value, train_metrics, False, "REJECTED_NEGATIVE_EXPECTANCY", "Failed in training phase.")
            
        # 4. Validation Phase (Unseen)
        val_res = self.backtester.run(val, test_strat)
        val_metrics = val_res["metrics"]
        
        # Objective criteria check (preventing over-optimization on win rate)
        if val_metrics.get("profit_factor", 0) < 1.2 or val_metrics.get("expectancy", 0) <= 0:
             return self._finalize_experiment(base_strategy, test_strat, target_param, new_value, val_metrics, False, "REJECTED_VALIDATION", "Failed to generalize to validation data.")
             
        # 5. Robustness Testing
        robust_tester = RobustnessTester(self.backtester)
        # Test 3x slippage variance
        slippage_results = robust_tester.test_slippage_variance(val, test_strat, iterations=3)
        survived_slippage = all(r["metrics"].get("expectancy", 0) > 0 for r in slippage_results)
        
        if not survived_slippage:
            return self._finalize_experiment(base_strategy, test_strat, target_param, new_value, val_metrics, False, "REJECTED_FRAGILE", "Collapsed under adverse slippage variance.")
            
        # 6. Promotion
        return self._finalize_experiment(base_strategy, test_strat, target_param, new_value, val_metrics, True, "PROMOTED_TO_WALK_FORWARD", "Passed all strict objective criteria.")
        
    def _finalize_experiment(self, base_strat, test_strat, param, val, metrics, robust_passed, status, reasoning) -> Dict[str, Any]:
        exp_data = {
            "base_strategy_id": base_strat.strategy_id,
            "new_version": test_strat.version,
            "parameter_mutations": {param: val},
            "expectancy": metrics.get("expectancy"),
            "win_rate": metrics.get("win_rate"),
            "profit_factor": metrics.get("profit_factor"),
            "robustness_passed": robust_passed,
            "status": status,
            "reasoning": reasoning
        }
        ExperimentJournal.log_experiment(exp_data)
        return exp_data
