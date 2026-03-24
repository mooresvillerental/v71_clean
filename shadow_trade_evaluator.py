import json
import time
from pathlib import Path

OPEN_FILE = Path("signals/shadow_trades_open.jsonl")
CLOSED_FILE = Path("signals/shadow_trades_closed.jsonl")
PRICE_FILE = Path("signals/latest_price.json")

HORIZON_SECONDS = 60 * 60  # 60 minutes


def load_price():
    if not PRICE_FILE.exists():
        return None
    try:
        data = json.loads(PRICE_FILE.read_text())
        return float(data["price"])
    except Exception:
        return None


def append_jsonl(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, separators=(",", ":")) + "\n")


def main():
    if not OPEN_FILE.exists():
        print("No open shadow trades.")
        return

    price = load_price()
    if price is None:
        print("No price available.")
        return

    now = int(time.time())
    remaining = []

    with OPEN_FILE.open() as f:
        for line in f:
            try:
                t = json.loads(line)
            except:
                continue

            opened = t.get("opened_timestamp", 0)

            if now - opened < HORIZON_SECONDS:
                remaining.append(t)
                continue

            entry = float(t["entry_price"])
            action = t["action"]

            if action == "BUY":
                pnl = (price - entry) / entry * 100
            else:
                pnl = (entry - price) / entry * 100

            outcome = "WIN" if pnl > 0 else "LOSS"

            closed = dict(t)
            closed["exit_timestamp"] = now
            closed["exit_price"] = price
            closed["pnl_pct"] = round(pnl, 4)
            closed["outcome"] = outcome
            closed["status"] = "CLOSED"

            append_jsonl(CLOSED_FILE, closed)

            print("Closed shadow trade:", closed)

    OPEN_FILE.write_text(
        "\n".join(json.dumps(x, separators=(",", ":")) for x in remaining) + ("\n" if remaining else "")
    )


if __name__ == "__main__":
    main()
