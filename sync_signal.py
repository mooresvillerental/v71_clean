import json
from pathlib import Path
from urllib.request import urlopen, Request

dst = Path("/data/data/com.termux/files/home/v71_clean/signal.json")
SIGNAL_URL = "http://127.0.0.1:18093/signal"

def fetch_live_signal():
    req = Request(SIGNAL_URL, headers={"Cache-Control": "no-cache"})
    with urlopen(req, timeout=5) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    sig = raw.get("signal", {}) if isinstance(raw, dict) else {}
    return sig

sig = fetch_live_signal()

action_raw = str(sig.get("action") or "HOLD").upper()
action = "HOLD" if action_raw in ("NONE", "") else action_raw

public = {
    "symbol": sig.get("symbol", "BTC-USD"),
    "action": action,
    "final_action": action,
    "confidence": sig.get("confidence", 0),
    "status": "Engine Online",
    "price": sig.get("price", 0),
    "strategy": sig.get("strategy", ""),
    "preferred_strategy": sig.get("strategy", ""),
    "regime": sig.get("regime", ""),
    "trend": sig.get("trend", ""),
    "risk_level": sig.get("risk_level", "Monitoring"),
    "trade_eligible": sig.get("trade_eligible", False),
    "eligibility_reason": sig.get("reason", "No valid setup detected."),
    "quality_blocked": sig.get("quality_blocked", False),
    "quality_reason": sig.get("quality_reason", ""),
    "rsi": sig.get("rsi"),
    "suggested_trade_usd": sig.get("suggested_trade_usd", 0),
}

with dst.open("w", encoding="utf-8") as f:
    json.dump(public, f, indent=2)

print("Wrote", dst)
print(json.dumps(public, indent=2))
