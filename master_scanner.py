import pandas as pd
from typing import List, Dict
import warnings
import os
import requests
warnings.filterwarnings('ignore')

from skills.base import BaseSignalSkill, SignalResult
from skills.triple_rsi_mean_reversion import TripleRSI_MeanReversion
from skills.bb_rsi_mean_reversion import BB_RSI_MeanReversion
from skills.vwap_mean_reversion import VWAP_MeanReversion
from skills.opening_range_breakout_pro import OpeningRangeBreakout_Pro
from skills.high_probability_confluence import HighProbability_Confluence

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing, cannot send alert.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

class MasterScanner:
    def __init__(self):
        self.skills: Dict[str, BaseSignalSkill] = {
            "TripleRSI_MeanReversion": TripleRSI_MeanReversion(),
            "BB_RSI_MeanReversion": BB_RSI_MeanReversion(),
            "VWAP_MeanReversion": VWAP_MeanReversion(),
            "OpeningRangeBreakout_Pro": OpeningRangeBreakout_Pro(),
            "HighProbability_Confluence": HighProbability_Confluence()
        }

    def scan(self, df: pd.DataFrame, ticker: str = "UNKNOWN", dry_run: bool = True) -> List[dict]:
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
                print(f"[WARN] {skill_name} failed: {e}")
                
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        if dry_run:
            print(f"\n========================================================")
            print(f"   MASTER SCANNER RESULTS (DRY RUN)")
            print(f"========================================================")
            print(f"Analyzed {len(self.skills)} skills on data ending: {df.index[-1]}")
            
            if not results:
                print("No actionable signals found meeting minimum thresholds.")
                
            for r in results:
                print(f"[{r['confidence']:>5.1f}%] {r['skill']} -> {r['signal']}")
                print(f"         Reason: {r['reason']}")
                print(f"         Stop: {r['stop_price']} | Target: {r['target_price']}")
                print("-" * 56)
        else:
            # Live Execution / Telegram Alert
            for r in results:
                msg = (
                    f"?? <b>QUANT SYSTEM ALERT ({ticker})</b> ??\n\n"
                    f"<b>Skill:</b> {r['skill']}\n"
                    f"<b>Signal:</b> {r['signal']}\n"
                    f"<b>Confidence:</b> {r['confidence']:.1f}%\n"
                    f"<b>Reason:</b> {r['reason']}\n\n"
                    f"<b>Stop Loss:</b> {r['stop_price']:.2f}\n"
                    f"<b>Target:</b> {r['target_price']:.2f}\n"
                )
                send_telegram_alert(msg)
                
        return results

if __name__ == "__main__":
    import urllib.request
    import io
    
    # Twelve Data API Key from previous prompt
    API_KEY = "7873877dad9f4f7fb1750fa5ef5eaa86" 
    
    def get_twelvedata(symbol, interval, outputsize=1000):
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={API_KEY}&outputsize={outputsize}&format=csv"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req)
        df = pd.read_csv(io.StringIO(res.read().decode('utf-8')), sep=';')
        df.rename(columns={'datetime': 'timestamp'}, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df.sort_index().astype(float)
        
    scanner = MasterScanner()
    
    # Example live run on SPY and QQQ
    tickers = ["SPY", "QQQ"]
    for ticker in tickers:
        try:
            print(f"Fetching {ticker} (Daily) data...")
            df = get_twelvedata(ticker, '1day', 500)
            # Run LIVE (dry_run=False) so it sends to Telegram!
            scanner.scan(df, ticker=ticker, dry_run=False)
        except Exception as e:
            print(f"Failed to fetch/scan {ticker}: {e}")

