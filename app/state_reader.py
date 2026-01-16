import json
import os

# v70 engine writes here
STATE_PATH = os.path.expanduser("~/v69_app_data/state.json")

def latest_signal():
    """
    Returns a dict ONLY when action is BUY or SELL.
    Otherwise returns None.
    """
    if not os.path.exists(STATE_PATH):
        return None

    try:
        with open(STATE_PATH, "r") as f:
            state = json.load(f)
    except Exception:
        return None

    decision = state.get("decision") or {}
    action = decision.get("action")
    reason = decision.get("reason")

    if action in ("BUY", "SELL"):
        primary = state.get("primary") or {}
        return {
            "action": action,
            "reason": reason,
            "price": primary.get("price"),
            "symbol": primary.get("symbol"),
            "ts": state.get("ts"),
        }

    return None
