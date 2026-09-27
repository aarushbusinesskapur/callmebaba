import pandas as pd
from typing import List, Dict
import warnings
warnings.filterwarnings('ignore')

from skills.base import BaseSignalSkill, SignalResult
from skills.triple_rsi_mean_reversion import TripleRSI_MeanReversion
from skills.bb_rsi_mean_reversion import BB_RSI_MeanReversion
from skills.vwap_mean_reversion import VWAP_MeanReversion
from skills.opening_range_breakout_pro import OpeningRangeBreakout_Pro
from skills.high_probability_confluence import HighProbability_Confluence

class MasterScanner:
    def __init__(self):
        self.skills: Dict[str, BaseSignalSkill] = {
            "TripleRSI_MeanReversion": TripleRSI_MeanReversion(),
            "BB_RSI_MeanReversion": BB_RSI_MeanReversion(),
            "VWAP_MeanReversion": VWAP_MeanReversion(),
            "OpeningRangeBreakout_Pro": OpeningRangeBreakout_Pro(),
            "HighProbability_Confluence": HighProbability_Confluence()
        }

    def scan(self, df: pd.DataFrame, dry_run: bool = True) -> List[dict]:
        results = []
        
        for skill_name, skill in self.skills.items():
            try:
                res = skill.generate_signal(df)
                if res.signal != "NEUTRAL":
                    results.append({
                        "skill": skill_name,
                        "signal": res.signal,
                        "confidence": res.confidence,
                        "reason": res.reason,
                        "stop_price": res.stop_price,
                        "target_price": res.target_price
                    })
            except Exception as e:
                # Log explicitly so broken skills aren't mistaken for 'NEUTRAL' states
                print(f"[WARN] {skill_name} failed: {e}")
                
        # Rank by confidence descending
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        if dry_run:
            print(f"\n========================================================")
            print(f"   MASTER SCANNER RESULTS (DRY RUN)")
            print(f"========================================================")
            print(f"Analyzed {len(self.skills)} skills on data ending: {df.index[-1]}")
            print(f"Signals Found: {len(results)}\n")
            
            if not results:
                print("No actionable signals found meeting minimum thresholds.")
                
            for r in results:
                print(f"[{r['confidence']:>5.1f}%] {r['skill']} -> {r['signal']}")
                print(f"         Reason: {r['reason']}")
                print(f"         Stop: {r['stop_price']} | Target: {r['target_price']}")
                print("-" * 56)
                
        return results
