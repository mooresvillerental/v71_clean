import json
import time
import os
import urllib.request
import urllib.parse

TOKEN = "8779109351:AAEDp3dt2NN9wQpuIV934n7DaOe__JQJsOE"
CHANNEL_ID = "-1003818142639"
SITE_URL = "https://geteztrader.com"

SIGNAL_FILE = "signals/latest_signal.json"
TRADE_FILE = "signals/assistant_trade_history.json"

last_trade_time = None
last_signal_action = None


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def telegram_post(text):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": CHANNEL_ID,
        "text": text
    }).encode()

    req = urllib.request.Request(url, data=data)

    try:
        urllib.request.urlopen(req)
        print("Posted to Telegram")
    except Exception as e:
        print("Telegram post failed:", e)


while True:

    signal = load_json(SIGNAL_FILE)
    trades = load_json(TRADE_FILE)

    if signal:
        action = signal.get("action")

        if action != last_signal_action:

            display_action = action
            if action == "NONE":
                display_action = "Monitoring Market"

            message = f"""EZTrader AI Update

Market: {signal.get("symbol")}
Signal: {display_action}
Confidence: {signal.get("confidence")}%
Strategy: {signal.get("strategy")}
Regime: {signal.get("regime")}

Live Engine:
{SITE_URL}
"""

            telegram_post(message)
            last_signal_action = action

    if trades:
        latest = trades[-1]
        t = latest.get("timestamp")

        if t != last_trade_time:

            message = f"""EZTrader AI Trade

{latest.get("action")} {latest.get("symbol")}
Price: ${latest.get("price")}
Size: ${latest.get("size_usd")}

Live Dashboard:
{SITE_URL}
"""

            telegram_post(message)
            last_trade_time = t

    time.sleep(60)
