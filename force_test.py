import pandas as pd
import datetime
from skills.base import SignalResult
import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or "8900720623:AAEsfrm2d7sLPWPx47S4yRXLxsNlVqdGKdM"
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID") or "745457169"

def send_telegram_alert(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    requests.post(url, json=payload, timeout=10)

ticker = "BTC/USDT"
msg = (
    f"?? <b>QUANT SYSTEM ALERT ({ticker})</b> ??\n\n"
    f"<b>Skill:</b> HighProbability_Confluence\n"
    f"<b>Signal:</b> BUY\n"
    f"<b>Confidence:</b> 76.5%\n"
    f"<b>Reason:</b> Long Confluence (4/5) [FORCED LIVE TEST]\n\n"
    f"<b>Stop Loss:</b> 63250.00\n"
    f"<b>Target:</b> 65400.00\n"
    f"<b>Time:</b> {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
)
send_telegram_alert(msg)
print("Forced live signal sent!")
