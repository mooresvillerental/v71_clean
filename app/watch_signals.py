import time
import os
from app.state_reader import latest_signal

POLL_SECONDS = 2.0
_last_key = None

def speak(text):
    os.system(f'termux-tts-speak "{text}"')

def notify(title, content):
    os.system(f'termux-notification --title "{title}" --content "{content}"')

def main():
    global _last_key
    print(f"Watching for BUY/SELL signals every {POLL_SECONDS:.1f}s...")

    while True:
        sig = latest_signal()

        if sig:
            key = f"{sig.get('action')}|{sig.get('reason')}|{sig.get('ts')}"

            if key != _last_key:
                _last_key = key

                print("ALERT:", sig)

                action = sig.get("action")
                symbol = sig.get("symbol")
                price = sig.get("price")
                reason = sig.get("reason")

                speak(f"{action} signal. {symbol} at {price}. Reason {reason}.")
                notify(
                    "V70 Host Signal",
                    f"{action} {symbol} @ {price} ({reason})"
                )

        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
