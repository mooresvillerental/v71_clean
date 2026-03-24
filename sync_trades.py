import json
from pathlib import Path
from datetime import datetime

src = Path("/data/data/com.termux/files/home/v71_clean/signals/assistant_trade_history.json")
dst = Path("/data/data/com.termux/files/home/v71_clean/trades.json")

with src.open("r", encoding="utf-8") as f:
    trades = json.load(f)

public = []

for t in trades[-5:][::-1]:
    ts = t.get("timestamp")
    when = ""
    if ts:
        try:
            when = datetime.fromtimestamp(ts).strftime("%b %d %I:%M %p")
        except Exception:
            when = str(ts)

    public.append({
        "symbol": t.get("symbol", "BTC-USD"),
        "action": t.get("action", ""),
        "price": t.get("price", 0),
        "size_usd": t.get("size_usd", 0),
        "filled_qty": t.get("filled_qty", 0),
        "time": when
    })

with dst.open("w", encoding="utf-8") as f:
    json.dump(public, f, indent=2)

print("Wrote", dst)
print(json.dumps(public, indent=2))
