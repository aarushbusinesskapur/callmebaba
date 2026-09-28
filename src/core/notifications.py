import os
import requests
from abc import ABC, abstractmethod
from src.core.logger import logger

class NotificationProvider(ABC):
    @abstractmethod
    def send(self, message: str):
        pass

class ConsoleProvider(NotificationProvider):
    def send(self, message: str):
        print("\n" + message + "\n")

class TelegramProvider(NotificationProvider):
    def __init__(self):
        # API keys safely injected via environment variables
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
    def send(self, message: str):
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not found. Skipping Telegram alert.")
            return
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": f"<pre>{message}</pre>", # Use HTML parse mode for monospace formatting
            "parse_mode": "HTML"
        }
        try:
            # Wrapped in try-except to ensure notification failure never crashes the trading engine
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Successfully sent Telegram alert.")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
