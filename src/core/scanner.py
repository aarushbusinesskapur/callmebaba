import pandas as pd
from typing import List, Dict, Any
from src.data_providers.base import MarketDataProvider
from src.analysis.regime import RegimeClassifier
from src.strategies.base import BaseStrategy
from src.core.logger import logger

class MarketScanner:
    """Deterministic screening stage that ranks setups before AI analysis."""
    
    def __init__(self, providers: List[MarketDataProvider], strategies: List[BaseStrategy]):
        self.providers = providers
        self.strategies = strategies
        
    def scan_market(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        """Scans a single market across all configured strategies."""
        candidates = []
        
        for provider in self.providers:
            try:
                df = provider.get_historical_ohlcv(symbol, timeframe)
                if not provider.validate_data(df):
                    logger.warning(f"Invalid or stale data from {provider.name} for {symbol}")
                    continue
                    
                regime = RegimeClassifier.detect_regime(df)
                
                for strategy in self.strategies:
                    # Run deterministic rules
                    signals_df = strategy.generate_signals(df)
                    latest_signal = signals_df.iloc[-1]
                    
                    if latest_signal.get('entry_signal', 0) != 0:
                        candidate = {
                            "symbol": symbol,
                            "provider": provider.name,
                            "timeframe": timeframe,
                            "strategy_id": strategy.strategy_id,
                            "regime": regime,
                            "direction": "LONG" if latest_signal['entry_signal'] == 1 else "SHORT",
                            "score": self._rank_candidate(latest_signal, regime, strategy),
                            "data": latest_signal.to_dict()
                        }
                        candidates.append(candidate)
            except Exception as e:
                logger.error(f"Error scanning {symbol} on {provider.name}: {e}")
                
        # Sort candidates by quantitative score descending
        return sorted(candidates, key=lambda x: x["score"], reverse=True)
        
    def _rank_candidate(self, signal_row: pd.Series, regime: str, strategy: BaseStrategy) -> float:
        """
        Assigns a base deterministic score (0-100) before sending to the AI layer.
        Rejects obviously bad combinations (e.g., trend following in a low-vol range).
        """
        score = 50.0 # Base score
        
        # Example regime filter logic
        if "range" in regime and "Trend" in strategy.strategy_id:
            score -= 30.0
        elif "uptrend" in regime and signal_row.get('entry_signal') == 1:
            score += 20.0
        elif "downtrend" in regime and signal_row.get('entry_signal') == -1:
            score += 20.0
            
        return min(max(score, 0.0), 100.0)
