import requests

TELEGRAM_TOKEN = "8900720623:AAEsfrm2d7sLPWPx47S4yRXLxsNlVqdGKdM"
TELEGRAM_CHAT_ID = "745457169"

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
msg = (
    "? <b>Master Scanner Connected!</b>\n\n"
    "This is a test message to confirm that your High-Probability "
    "Trading Skills System is successfully wired up. "
    "You will now receive live signals here."
)

payload = {
    "chat_id": TELEGRAM_CHAT_ID, 
    "text": msg, 
    "parse_mode": "HTML"
}

try:
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Successfully sent test message to Telegram!")
    else:
        print(f"Failed to send. Status Code: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
