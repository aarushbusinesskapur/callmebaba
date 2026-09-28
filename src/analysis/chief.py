from typing import Dict, Any, List
from src.analysis.agents import QuantAgent, TechnicalAgent, MacroAgent, RiskAgent
from src.core.logger import logger

class ChiefAnalyst:
    """The orchestrator agent that makes the final NO TRADE or SIGNAL decision."""
    
    def __init__(self):
        self.name = "Chief Analyst"
        self.subagents = [
            QuantAgent(),
            TechnicalAgent(),
            MacroAgent(),
            RiskAgent()
        ]
        
    def evaluate_candidate(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the candidate through all subagents and synthesizes a final decision."""
        logger.info(f"[{self.name}] Initiating multi-agent review for {candidate.get('symbol')} {candidate.get('direction')}")
        
        reports = []
        for agent in self.subagents:
            report = agent.analyze(candidate)
            reports.append(report)
            
            # Fast fail if a critical agent outright rejects
            if not report.get("approved", False):
                logger.info(f"[{self.name}] Setup REJECTED by {agent.name}: {report.get('notes')}")
                return self._generate_no_trade(candidate, f"Rejected by {agent.name}")
                
        # Aggregate component scores to determine Signal Quality Score (0-100)
        avg_score = sum(r.get("score", 0) for r in reports) / len(reports)
        
        # 85/100 threshold from system rules
        if avg_score < 85: 
            logger.info(f"[{self.name}] Setup REJECTED. Score {avg_score} below 85 threshold.")
            return self._generate_no_trade(candidate, "Insufficient aggregate signal quality.")
            
        logger.info(f"[{self.name}] Setup APPROVED with quality score {avg_score}")
        return self._generate_signal(candidate, reports, avg_score)
        
    def _generate_no_trade(self, candidate: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "status": "REJECTED",
            "symbol": candidate.get("symbol"),
            "reason": reason
        }
        
    def _generate_signal(self, candidate: Dict[str, Any], reports: List[Dict[str, Any]], final_score: float) -> Dict[str, Any]:
        return {
            "status": "CONFIRMED",
            "symbol": candidate.get("symbol"),
            "direction": candidate.get("direction"),
            "strategy": candidate.get("strategy_id"),
            "quality_score": round(final_score, 1),
            "reports": reports
            # Detailed Entry, SL, and TP targets will be attached in the signal formatter
        }
