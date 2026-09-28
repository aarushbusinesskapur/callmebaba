import os
import sys
import time
import requests
import pandas as pd
import ccxt
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.strategies.phase5 import Phase5Strategy

class LiveExecutor:
    def __init__(self, telegram_token=None, telegram_chat_id=None):
        # Use Binance Futures to fetch funding rates, but we trade Spot/Perp hybrids
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        self.telegram_token = telegram_token or os.getenv("TELEGRAM_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        
    def send_telegram(self, message):
        print(f"\n[ALERT] {message}")
        if self.telegram_token and self.telegram_chat_id:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "Markdown"}
            try:
                requests.post(url, json=payload, timeout=5)
            except Exception as e:
                print(f"Telegram Error: {e}")

    def fetch_live_data(self, symbol):
        """Fetches the required OHLCV and 30-day Funding Rate data for Phase 5"""
        print(f"Fetching live data for {symbol}...")
        
        # 1. Fetch 1H OHLCV (Need 100+ for BB Width percentile)
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df.set_index('timestamp', inplace=True)
        
        # 2. Fetch Funding Rates (Need 720 hours / 30 days for Z-Score)
        # CCXT fetch_funding_rate_history returns recent history. Binance limits to 100-500.
        # We loop to get 30 days.
        since = self.exchange.milliseconds() - (35 * 24 * 60 * 60 * 1000) # 35 days ago
        funding_data = []
        
        try:
            while since < self.exchange.milliseconds():
                history = self.exchange.fetch_funding_rate_history(symbol, since=since, limit=1000)
                if not history:
                    break
                funding_data.extend(history)
                since = history[-1]['timestamp'] + 1
                time.sleep(0.5) # rate limit safe
        except Exception as e:
            print(f"Error fetching funding for {symbol}: {e}")
            return None
            
        if not funding_data:
            return None
            
        df_fund = pd.DataFrame(funding_data)
        df_fund['timestamp'] = pd.to_datetime(df_fund['timestamp'], unit='ms', utc=True)
        df_fund.set_index('timestamp', inplace=True)
        
        # Merge exactly like our backtester
        df = df.join(df_fund[['fundingRate']], how='left')
        df['fundingRate'] = df['fundingRate'].ffill()
        df.reset_index(inplace=True)
        
        return df

    def scan_market(self, symbols):
        for symbol in symbols:
            df = self.fetch_live_data(symbol)
            if df is None or df.empty:
                continue
                
            strat = Phase5Strategy(f"Phase5_Live", "1.0", {})
            signals = strat.generate_signals(df)
            
            latest = signals.iloc[-1]
            prev = signals.iloc[-2]
            
            # Check if a new signal just fired on the most recently closed bar
            direction = latest.get('entry_signal', 0)
            
            if direction != 0:
                side = "🟢 LONG" if direction == 1 else "🔴 SHORT"
                price = latest['close']
                sl = latest['sl']
                z_score = latest['fund_z']
                bb_pct = prev['bb_width_pct']
                
                msg = (f"⚡ **PHASE 5 ALERT: {symbol}** ⚡\n\n"
                       f"**Action:** {side}\n"
                       f"**Entry Price:** ${price:,.4f}\n"
                       f"**Stop Loss:** ${sl:,.4f} (Wide Invalidation)\n"
                       f"**Exit:** Fixed 48-Hour Hold\n\n"
                       f"📊 **Context:**\n"
                       f"- Funding Z-Score: {z_score:.2f}\n"
                       f"- BB Compression (Prev): {bb_pct:.2%} percentile\n"
                       f"- *Anticipating Liquidation Cascade*")
                self.send_telegram(msg)
            else:
                print(f"[{symbol}] No signal. Fund Z: {latest['fund_z']:.2f}, BB Pct: {latest['bb_width_pct']:.2%}")

if __name__ == "__main__":
    executor = LiveExecutor()
    # E.g. Run once per hour via cron, evaluating the last closed hourly candle
    executor.scan_market(['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT'])
