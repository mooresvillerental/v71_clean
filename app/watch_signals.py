import time
import os
from app.state_reader import latest_signal

POLL_SECONDS = 2.0
_last_key = None
_last_actionable = None

def speak(text: str):
    os.system(f'termux-tts-speak "{text}"')

def notify(title: str, content: str):
    os.system(f'termux-notification --title "{title}" --content "{content}"')

def main():
    global _last_key, _last_actionable
    print(f"Watching for final BUY/SELL signals every {POLL_SECONDS:.1f}s...")

    while True:
        sig = latest_signal()

        if sig:
            action = sig.get("action", "NONE")
            quality_blocked = bool(sig.get("quality_blocked", False))
            trade_eligible = bool(sig.get("trade_eligible", False))

            if action in ("BUY", "SELL") and (not quality_blocked) and trade_eligible:
                key = "|".join([
                    str(sig.get("timestamp")),
                    str(sig.get("symbol")),
                    str(action),
                    str(sig.get("strategy")),
                    str(sig.get("price")),
                ])

                if key != _last_key:
                    _last_key = key

                    symbol = sig.get("symbol", "")
                    price = sig.get("price", "")
                    confidence = sig.get("confidence", "")
                    strategy = sig.get("winning_strategy") or sig.get("strategy") or ""
                    regime = sig.get("regime", "UNKNOWN")
                      suggested = sig.get("suggested_trade_usd",0)

                    print("ALERT:", sig)

                    if action == "BUY" and float(suggested or 0) > 0:

                        speak(f"{action} signal. {symbol} at {price}. Suggested trade {suggested} dollars. Strategy {strategy}. Regime {regime}.")

                    elif action == "SELL":

                        speak(f"{action} signal. {symbol} at {price}. Strategy {strategy}. Regime {regime}.")

                    else:

                        speak(f"{action} signal. {symbol} at {price}. Strategy {strategy}. Regime {regime}.")
                    notify(
                        "EZTRADER Signal",
                        f"{action} {symbol} @ {price} | conf {confidence} | {strategy} | {regime}"
                    )

        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
