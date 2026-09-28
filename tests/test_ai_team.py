import pytest
from src.analysis.chief import ChiefAnalyst
from src.analysis.agents import MacroAgent

def test_chief_analyst_approval():
    chief = ChiefAnalyst()
    candidate = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "strategy_id": "Trend_01"
    }
    
    result = chief.evaluate_candidate(candidate)
    assert result["status"] == "CONFIRMED"
    assert result["quality_score"] >= 85

def test_chief_analyst_rejection(monkeypatch):
    chief = ChiefAnalyst()
    
    # Mock MacroAgent to reject the setup (e.g. FOMC day)
    def mock_macro_analyze(self, candidate):
        return {"agent": "Macro Agent", "approved": False, "notes": "FOMC meeting today. High risk.", "score": 20}
        
    monkeypatch.setattr(MacroAgent, "analyze", mock_macro_analyze)
    
    candidate = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "strategy_id": "Trend_01"
    }
    
    result = chief.evaluate_candidate(candidate)
    assert result["status"] == "REJECTED"
    assert "Rejected by Macro Agent" in result["reason"]
