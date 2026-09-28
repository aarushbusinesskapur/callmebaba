import pandas as pd
from typing import List, Dict
import warnings
import os
import json
import time
import requests
import ccxt
warnings.filterwarnings('ignore')

from skills.base import BaseSignalSkill, SignalResult
from skills.triple_rsi_mean_reversion import TripleRSI_MeanReversion
from skills.bb_rsi_mean_reversion import BB_RSI_MeanReversion
from skills.vwap_mean_reversion import VWAP_MeanReversion
from skills.opening_range_breakout_pro import OpeningRangeBreakout_Pro
from skills.high_probability_confluence import HighProbability_Confluence

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "master_state.json"

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

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

class MasterScanner:
    def __init__(self):
        # SKILLS REMAIN 100% UNTOUCHED
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
                        "target_price": res.target_price,
                        "timestamp": str(df.index[-1])
                    })
            except Exception as e:
                print(f"[WARN] {skill_name} failed: {e}")
                
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        if dry_run:
            print(f"Analyzed {ticker}. Found {len(results)} signals.")
        else:
            state = load_state()
            for r in results:
                # Create a unique ID for this exact signal on this exact candle
                sig_id = f"{ticker}_{r['skill']}_{r['timestamp']}"
                
                # Only send if we haven't sent this exact signal already
                if sig_id not in state:
                    msg = (
                        f"?? <b>QUANT SYSTEM ALERT ({ticker})</b> ??\n\n"
                        f"<b>Skill:</b> {r['skill']}\n"
                        f"<b>Signal:</b> {r['signal']}\n"
                        f"<b>Confidence:</b> {r['confidence']:.1f}%\n"
                        f"<b>Reason:</b> {r['reason']}\n\n"
                        f"<b>Stop Loss:</b> {r['stop_price']:.2f}\n"
                        f"<b>Target:</b> {r['target_price']:.2f}\n"
                        f"<b>Time:</b> {r['timestamp']}"
                    )
                    send_telegram_alert(msg)
                    state[sig_id] = True
            
            # Keep state file from growing infinitely by removing very old entries
            if len(state) > 1000:
                state = dict(list(state.items())[-500:])
            save_state(state)
                
        return results

if __name__ == "__main__":
    print("Starting Multi-Coin Crypto Scan...")
    exchange = ccxt.bybit({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
    
    # 50+ Top Crypto Coins
    TICKERS = [
    "BUSD/USDT", "TUSD/USDT", "ZEC/USDT", "BTC/USDT", "SOL/USDT", "SUI/USDT", "XRP/USDT", "FLOKI8/USDT", "BOND/USDT", "UST/USDT", "ETH/USDT", "DAI/USDT", "JASMY/USDT", "QNT/USDT", "HNT/USDT", "MKR/USDT", "SRM/USDT", "MATIC/USDT", "POLY/USDT", "OXT/USDT", "VITE/USDT", "OMG/USDT", "FTM/USDT", "EOS/USDT", "LTO/USDT", "CUDOS/USDT", "POND/USDT", "REN/USDT", "KDA/USDT", "SPELL/USDT", "LOOM/USDT", "NEAR/USDT", "ANT/USDT", "DAR/USDT", "DOGE/USDT", "LRC/USDT", "LOKA/USDT", "STG/USDT", "GAL/USDT", "WAVES/USDT", "RNDR/USDT", "PENGU/USDT", "CLV/USDT", "LTC/USDT", "BAL/USDT", "A2Z/USDT", "USDC/USDT", "DASH/USDT", "PUMP/USDT", "STMX/USDT", "D/USDT", "MXC/USDT", "DATA/USDT", "JAM/USDT", "LINK/USDT", "ADA/USDT", "UNI/USDT", "HYPE/USDT", "AVAX/USDT", "BNB/USDT", "PEPE/USDT", "ENA/USDT", "ICX/USDT", "XLM/USDT", "DOT/USDT", "FET/USDT", "ONDO/USDT", "HBAR/USDT", "WLD/USDT", "ARB/USDT", "TROLL/USDT", "ICP/USDT", "ONE/USDT", "DUSK/USDT", "DGB/USDT", "BCH/USDT", "POL/USDT", "VET/USDT", "VELO/USDT", "GRAM/USDT", "ATOM/USDT", "ASTER/USDT", "AAVE/USDT", "SKY/USDT", "JUP/USDT", "RHEA/USDT", "GRT/USDT", "RENDER/USDT", "XDC/USDT", "ALGO/USDT", "INJ/USDT", "SHIB/USDT", "VTHO/USDT", "TRX/USDT", "REEF/USDT", "APT/USDT", "XEC/USDT", "ROSE/USDT", "TFUEL/USDT", "IOTA/USDT"
]
    
    scanner = MasterScanner()
    
    for ticker in TICKERS:
        try:
            # Fetch 15-minute bars using CCXT (500 bars limit fits all indicator lookbacks)
            bars = exchange.fetch_ohlcv(ticker, timeframe='15m', limit=500)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.astype(float)
            
            # Run Live (dry_run=False triggers Telegram & State tracking)
            scanner.scan(df, ticker=ticker, dry_run=False)
            
            # Sleep briefly to respect Binance API limits
            time.sleep(0.5)
        except Exception as e:
            print(f"Failed to fetch/scan {ticker}: {e}")
            time.sleep(2)

