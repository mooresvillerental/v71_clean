import json
from pathlib import Path
from collections import defaultdict

ASSISTANT_HISTORY = Path("signals/assistant_trade_history.json")
SHADOW_CLOSED = Path("signals/shadow_trades_closed.jsonl")
SHADOW_OPEN = Path("signals/shadow_trades_open.jsonl")
SHADOW_BLOCKED = Path("signals/shadow_trades_blocked.jsonl")

def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default

def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows

def pct(x):
    return f"{x:.2f}%"

def summarize_shadow(rows):
    by_strategy = defaultdict(lambda: {
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "avg_pnl_pct": 0.0,
        "total_pnl_pct": 0.0,
        "blocked": 0,
    })

    for r in rows:
        strat = r.get("winning_strategy") or r.get("strategy") or "UNKNOWN"
        pnl = float(r.get("pnl_pct", 0.0) or 0.0)
        outcome = r.get("outcome", "")
        blocked = bool(r.get("blocked_by_bot", False))

        s = by_strategy[strat]
        s["trades"] += 1
        s["total_pnl_pct"] += pnl
        if blocked:
            s["blocked"] += 1
        if outcome == "WIN":
            s["wins"] += 1
        else:
            s["losses"] += 1

    for strat, s in by_strategy.items():
        if s["trades"] > 0:
            s["avg_pnl_pct"] = s["total_pnl_pct"] / s["trades"]

    return by_strategy

def summarize_assistant(hist):
    sells = [x for x in hist if x.get("action") == "SELL"]
    buys = [x for x in hist if x.get("action") == "BUY"]
    realized = sum(float(x.get("realized_pnl_usd", 0.0) or 0.0) for x in sells)
    wins = sum(1 for x in sells if float(x.get("realized_pnl_usd", 0.0) or 0.0) > 0)
    losses = sum(1 for x in sells if float(x.get("realized_pnl_usd", 0.0) or 0.0) <= 0)
    return {
        "accepted_trades": len(hist),
        "buys": len(buys),
        "completed_sells": len(sells),
        "wins": wins,
        "losses": losses,
        "realized_pnl_usd": realized,
        "win_rate": (wins / len(sells) * 100.0) if sells else 0.0,
    }

def main():
    assistant_hist = load_json(ASSISTANT_HISTORY, [])
    shadow_closed = load_jsonl(SHADOW_CLOSED)
    shadow_open = load_jsonl(SHADOW_OPEN)
    shadow_blocked = load_jsonl(SHADOW_BLOCKED)

    assistant = summarize_assistant(assistant_hist)
    shadow = summarize_shadow(shadow_closed)

    print("\n===== EZTRADER PERFORMANCE SCOREBOARD =====\n")

    print("Assistant Trades")
    print("----------------")
    print(f"Accepted trades : {assistant['accepted_trades']}")
    print(f"BUY entries     : {assistant['buys']}")
    print(f"Completed sells : {assistant['completed_sells']}")
    print(f"Wins / Losses   : {assistant['wins']} / {assistant['losses']}")
    print(f"Win rate        : {pct(assistant['win_rate'])}")
    print(f"Realized P/L    : ${assistant['realized_pnl_usd']:.2f}")

    print("\nShadow Trades")
    print("-------------")
    print(f"Open shadow trades     : {len(shadow_open)}")
    print(f"Closed shadow trades   : {len(shadow_closed)}")
    print(f"Blocked candidates log : {len(shadow_blocked)}")

    print("\nStrategy Scoreboard")
    print("-------------------")
    if not shadow:
        print("No closed shadow trades yet.")
    else:
        for strat, s in sorted(shadow.items(), key=lambda kv: kv[1]["total_pnl_pct"], reverse=True):
            win_rate = (s["wins"] / s["trades"] * 100.0) if s["trades"] else 0.0
            print(f"{strat}")
            print(f"  Trades       : {s['trades']}")
            print(f"  Wins/Losses  : {s['wins']} / {s['losses']}")
            print(f"  Win rate     : {pct(win_rate)}")
            print(f"  Avg P/L      : {pct(s['avg_pnl_pct'])}")
            print(f"  Total P/L    : {pct(s['total_pnl_pct'])}")
            print(f"  Blocked count : {s['blocked']}")
            print()

if __name__ == "__main__":
    main()
