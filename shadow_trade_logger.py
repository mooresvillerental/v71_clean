import json
from pathlib import Path

SIGNAL_FILE = Path("signals/latest_signal.json")
OPEN_LOG = Path("signals/shadow_trades_open.jsonl")

BLOCKED_LOG = Path("signals/shadow_trades_blocked.jsonl")

LOCK_FILE = Path("signals/shadow_signal_lock.json")

DEDUP_SECONDS = 20 * 60
MIN_PRICE_MOVE_PCT = 0.35

def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None

def append_jsonl(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, separators=(",", ":")) + "\n")

def load_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows

def main():
    sig = load_json(SIGNAL_FILE)
    
    # --- log blocked trade candidates ---
    raw_b = sig.get("strategy_b_action")
    raw_a = sig.get("strategy_a_action")

    raw_action = None
    if raw_b in ("BUY","SELL"):
        raw_action = raw_b
    elif raw_a in ("BUY","SELL"):
        raw_action = raw_a

    if raw_action and sig.get("quality_blocked"):
        row = {
            "timestamp": sig.get("timestamp"),
            "symbol": sig.get("symbol"),
            "action": raw_action,
            "strategy": sig.get("winning_strategy") or sig.get("strategy"),
            "confidence": sig.get("confidence"),
            "entry_price": sig.get("price"),
            "regime": sig.get("regime"),
            "reason": "blocked_by_quality_gate",
        }
        append_jsonl(BLOCKED_LOG, row)
        print("Logged BLOCKED shadow candidate:", row)

    if not sig:
        print("No latest signal found.")
        return

    action = sig.get("action", "NONE")
    if action not in ("BUY", "SELL"):
        print("No tradable signal.")
        return

    blocked_by_bot = False

    if sig.get("quality_blocked", False) or not sig.get("trade_eligible", False):
        blocked_by_bot = True
        print("Signal blocked by bot — shadow logging anyway.")

    lock = load_json(LOCK_FILE) or {}
    signal_key = {
        "timestamp": sig.get("timestamp"),
        "symbol": sig.get("symbol"),
        "action": action,
        "strategy": sig.get("strategy"),
        "price": sig.get("price"),
    }

    if lock == signal_key:
        print("Shadow trade already logged for this signal.")
        return

    # Dedupe near-identical open shadow trades
    open_rows = load_jsonl(OPEN_LOG)
    now_ts = int(sig.get("timestamp") or 0)
    cur_price = float(sig.get("price") or 0)
    cur_strategy = sig.get("winning_strategy") or sig.get("strategy")

    for t in reversed(open_rows):
        try:
            if t.get("status") != "OPEN":
                continue
            if t.get("symbol") != sig.get("symbol"):
                continue
            if t.get("action") != action:
                continue
            if (t.get("winning_strategy") or t.get("strategy")) != cur_strategy:
                continue

            opened_ts = int(t.get("opened_timestamp") or 0)
            entry_price = float(t.get("entry_price") or 0)

            age = now_ts - opened_ts
            move_pct = abs((cur_price - entry_price) / entry_price) * 100 if entry_price > 0 else 999

            if age < DEDUP_SECONDS and move_pct < MIN_PRICE_MOVE_PCT:
                print(f"Skipped duplicate shadow trade: age={age}s move={move_pct:.4f}%")
                return
        except Exception:
            continue

    row = {
        "opened_timestamp": sig.get("timestamp"),
        "symbol": sig.get("symbol"),
        "action": action,
        "strategy": sig.get("strategy"),
        "winning_strategy": sig.get("winning_strategy"),
        "regime": sig.get("regime"),
        "confidence": sig.get("confidence"),
        "entry_price": sig.get("price"),
        "status": "OPEN",
          "blocked_by_bot": blocked_by_bot,
        "horizon_minutes": 60,
    }

    append_jsonl(OPEN_LOG, row)
    LOCK_FILE.write_text(json.dumps(signal_key, indent=2) + "\n", encoding="utf-8")
    print("Logged shadow trade:", row)

if __name__ == "__main__":
    main()
