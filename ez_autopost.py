
import json
import os
import time
import requests

BOT_TOKEN = os.environ.get("EZTRADER_TG_BOT_TOKEN", "").strip()
CHANNEL_ID = os.environ.get("EZTRADER_TG_CHANNEL", "").strip()

SIGNAL_URL = "http://127.0.0.1:18093/signal"
STATE_FILE = "/data/data/com.termux/files/home/v71_clean/last_signal.txt"


def load_last_signal():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def save_last_signal(signal_id):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(signal_id)


def load_signal():
    try:
        r = requests.get(SIGNAL_URL, timeout=5)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            return None
        return data.get("signal")
    except Exception:
        return None


def send_telegram(message):
    if not BOT_TOKEN:
        raise RuntimeError("Missing EZTRADER_TG_BOT_TOKEN")
    if not CHANNEL_ID:
        raise RuntimeError("Missing EZTRADER_TG_CHANNEL")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    resp = requests.post(url, data=data, timeout=15)
    resp.raise_for_status()

    payload = resp.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")



def speak_alert(action, symbol, strength, suggested_text):
    try:
        spoken_symbol = str(symbol).replace("-", " ")
        spoken_size = str(suggested_text).replace("$", "").replace(",", "")

        base_msg = f"EZTrader. {strength} {action.lower()} {spoken_symbol}. Size {spoken_size} dollars."

        # Voice tuning
        if action == "BUY":
            rate = 1.1
            pitch = 1.1
        else:
            rate = 0.9
            pitch = 0.9

        # Strong signal emphasis
        repeat = 2 if strength == "STRONG" else 1

        for _ in range(repeat):
            os.system(f'termux-tts-speak "{base_msg}" >/dev/null 2>/dev/null')
    except Exception:
        pass

def pretty_strategy(raw):
    s = str(raw or "").upper()
    if s == "NO_SIGNAL":
        return "Waiting for Setup"
    if s == "A_ONLY":
        return "Strategy A Only"
    if s == "B_VOL_BREAKOUT":
        return "Volatility Breakout"
    if s == "A_TREND_PULLBACK":
        return "Trend Pullback"
    if s in ("NONE", ""):
        return "Standby"
    return str(raw)


while True:
    try:
        signal = load_signal()
        if not signal:
            time.sleep(10)
            continue

        action = str(signal.get("final_action") or signal.get("action") or "").upper()
        trade_eligible = bool(signal.get("trade_eligible", False))
        quality_blocked = bool(signal.get("quality_blocked", False))

        if action not in ["BUY", "SELL"] or not trade_eligible or quality_blocked:
            time.sleep(10)
            continue

        price = signal.get("live_price") or signal.get("price") or "N/A"
        confidence = signal.get("confidence", "--")
        strategy = pretty_strategy(signal.get("preferred_strategy") or signal.get("strategy"))
        regime = signal.get("regime", "--")
        symbol = signal.get("symbol", "BTC-USD")
        ts = signal.get("timestamp", "")
        
        # --- Dynamic Trade Sizing (REAL BALANCE) ---
        try:
            import requests
            r = requests.get("http://127.0.0.1:18093/portfolio", timeout=2)
            j = r.json()
            base_account = float(j.get("cash_usd", 0) or 0)
        except:
            base_account = 0

        try:
            conf_val = float(confidence)
        except:
            conf_val = 0

        if conf_val >= 80:
            size_pct = 0.25
        elif conf_val >= 70:
            size_pct = 0.18
        elif conf_val >= 60:
            size_pct = 0.12
        elif conf_val >= 50:
            size_pct = 0.08
        else:
            size_pct = 0.05

        suggested = round(base_account * size_pct, 2)


        try:
            suggested_text = f"${float(suggested):,.0f}" if float(suggested) > 0 else "—"
        except Exception:
            suggested_text = "—"

        signal_id = f"{symbol}_{action}_{price}_{confidence}_{suggested}_{ts}"
        last_signal = load_last_signal()

        if signal_id != last_signal:
                                                # --- Signal Strength + Reason + Risk ---
            try:
                conf_val = float(confidence)
            except:
                conf_val = 0

            if conf_val >= 80:
                strength = "STRONG"
            elif conf_val >= 65:
                strength = "MODERATE"
            else:
                strength = "LIGHT"

            emoji = "🚀" if action == "BUY" else "🔻"

            reason = (
                signal.get("eligibility_reason")
                or signal.get("quality_reason")
                or "Setup conditions aligned"
            )

            risk = signal.get("risk_level", "—")

            try:
                entry = f"${float(price):,.0f}"
            except:
                entry = str(price)

            message = f"""
{emoji} <b>{strength} {action} — {symbol}</b>

💰 <b>Price:</b> ${price}
🎯 <b>Entry:</b> {entry}
🪙 <b>Size:</b> {suggested_text}
📊 <b>Confidence:</b> {confidence}%

⚠️ <b>Risk:</b> {risk}

🧠 <b>Strategy:</b> {strategy}
🌐 <b>Market:</b> {regime}

🧾 <b>Reason:</b>
{reason}

━━━━━━━━━━━━━━━
🔗 https://geteztrader.com
""".strip()

            send_telegram(message)
            save_last_signal(signal_id)
            print("Sent:", signal_id)

    except Exception as e:
        print("Error:", e)

    time.sleep(10)
