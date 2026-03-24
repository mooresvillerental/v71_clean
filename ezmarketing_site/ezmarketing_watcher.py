import json
import time
from pathlib import Path
from datetime import datetime

TRADE_FILE = Path("signals/assistant_trade_history.json")
OUT_DIR = Path("marketing_posts")
STATE_FILE = Path("marketing_posts/.last_trade_state.json")

OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def format_trade_post(trade: dict) -> str:
    symbol = trade.get("symbol", "--")
    action = trade.get("action", "--")
    price = float(trade.get("price", 0) or 0)
    size_usd = float(trade.get("size_usd", 0) or 0)
    filled_qty = float(trade.get("filled_qty", 0) or 0)
    ts = trade.get("timestamp")

    if ts:
        dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %I:%M:%S %p")
    else:
        dt = "Unknown time"

    return (
        "EZTrader Trade Executed\n\n"
        f"{action} {symbol}\n"
        f"Price: ${price:,.2f}\n"
        f"Size: ${size_usd:,.2f}\n"
        f"Filled Qty: {filled_qty:.6f}\n"
        f"Time: {dt}\n\n"
        "Generated automatically by EZTrader Live Engine.\n"
    )

def write_post(trade: dict):
    ts = trade.get("timestamp") or int(time.time())
    dt = datetime.fromtimestamp(ts)
    filename = OUT_DIR / f"trade_event_{dt.strftime('%Y%m%d_%H%M%S')}.txt"
    filename.write_text(format_trade_post(trade), encoding="utf-8")
    print(f"[EZMarketing] Created {filename}")

def main():
    last_state = load_json(STATE_FILE, {"last_timestamp": None, "last_len": 0})

    print("[EZMarketing] Watching assistant trade history...")
    while True:
        trades = load_json(TRADE_FILE, [])
        if isinstance(trades, list) and trades:
            latest = trades[-1]
            latest_ts = latest.get("timestamp")
            trade_len = len(trades)

            is_new = (
                latest_ts != last_state.get("last_timestamp")
                or trade_len != last_state.get("last_len")
            )

            if is_new:
                write_post(latest)
                last_state = {
                    "last_timestamp": latest_ts,
                    "last_len": trade_len,
                }
                save_json(STATE_FILE, last_state)

        time.sleep(5)

if __name__ == "__main__":
    main()
