import time
from typing import List
from src.core.scanner import MarketScanner
from src.analysis.chief import ChiefAnalyst
from src.core.signal import SignalFormatter, TargetCalculator
from src.core.journal import SignalJournal
from src.core.notifications import NotificationProvider
from src.core.logger import logger

class QuantDaemon:
    """The continuous running engine that orchestrates the entire pipeline."""
    
    def __init__(self, scanner: MarketScanner, chief: ChiefAnalyst, notifiers: List[NotificationProvider]):
        self.scanner = scanner
        self.chief = chief
        self.notifiers = notifiers
        # For Phase 7 placeholder, hardcoded markets. Later drawn from config.
        self.markets_to_scan = [
            ("BTCUSDT", "1h"),
            ("ETHUSDT", "1h")
        ]
        
    def run_cycle(self):
        """Executes one full iteration of the market scan and AI analysis pipeline."""
        logger.info("Starting new scanning cycle...")
        
        all_candidates = []
        for symbol, tf in self.markets_to_scan:
            candidates = self.scanner.scan_market(symbol, tf)
            all_candidates.extend(candidates)
            
        # Sort by deterministic score to prioritize AI analysis (highest score first)
        all_candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        for candidate in all_candidates:
            # Only send promising candidates to the expensive AI layer
            if candidate.get("score", 0) >= 50:
                result = self.chief.evaluate_candidate(candidate)
                
                if result.get("status") == "CONFIRMED":
                    # Calculate strict targets
                    entry_price = candidate.get("data", {}).get("close", 0) # Placeholder
                    targets = TargetCalculator.calculate_targets(entry_price, candidate["direction"])
                    result["targets"] = targets
                    
                    # Store in research journal
                    SignalJournal.log_signal(result)
                    
                    # Format and broadcast
                    formatted_msg = SignalFormatter.format_signal(result)
                    for notifier in self.notifiers:
                        notifier.send(formatted_msg)
            else:
                logger.debug(f"Candidate {candidate['symbol']} skipped due to low score {candidate['score']}")
                
        logger.info("Scanning cycle completed.")
        
    def run_forever(self, interval_seconds: int = 3600):
        """Runs the daemon continuously (designed for persistent sidecar execution)."""
        logger.info(f"Starting Quant Daemon. Interval: {interval_seconds}s")
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Fatal error in run cycle: {e}")
            time.sleep(interval_seconds)
