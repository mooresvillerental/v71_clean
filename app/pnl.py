from __future__ import annotations
from pathlib import Path
import json
import time
from typing import Dict, Any, Tuple, Optional

# 1% per side (BUY + SELL) — your preference
PNL_FEE_RATE_DEFAULT = 0.01

def _now_ts() -> str:
    return time.strftime("%Y-%m-%d %I:%M:%S %p")

def read_json(path: Path, default=None):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text())
    except Exception:
        return default

def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True))

def engine_app_state_path(home: Optional[Path] = None) -> Path:
    home = home or Path.home()
    return home / "v69_app_data" / "app_state.json"

def pnl_path(home: Optional[Path] = None) -> Path:
    home = home or Path.home()
    return home / "v70_app_data" / "pnl.json"

def get_cash_and_qty(app_state: dict, symbol: str) -> Tuple[float, float]:
    cash = float(app_state.get("cash_usd", 0.0))
    holdings = app_state.get("holdings", {}) or {}
    qty = float(holdings.get(symbol, 0.0))
    return cash, qty

def apply_delta(
    pnl: Dict[str, Any],
    symbol: str,
    action: str,
    price: float,
    delta_cash: float,
    delta_qty: float,
    fee_rate: float = PNL_FEE_RATE_DEFAULT,
) -> Dict[str, Any]:
    """
    pnl per symbol:
      {
        position_qty, avg_entry, realized_usd, fees_usd,
        last_price, last_ts, last_action
      }
    """
    p = pnl.get(symbol) or {}
    pos = float(p.get("position_qty", 0.0))
    avg = p.get("avg_entry", None)
    avg = float(avg) if avg is not None else None
    realized = float(p.get("realized_usd", 0.0))
    fees = float(p.get("fees_usd", 0.0))

    now_ts = _now_ts()
    action = (action or "").upper()

    if action == "BUY":
        qty_bought = max(0.0, delta_qty)
        spend = max(0.0, -delta_cash)
        if qty_bought > 0 and spend > 0:
            entry = spend / qty_bought
            if pos <= 0 or avg is None:
                avg = entry
                pos = qty_bought
            else:
                new_pos = pos + qty_bought
                avg = ((avg * pos) + (entry * qty_bought)) / new_pos
                pos = new_pos
            fees += spend * fee_rate

    elif action == "SELL":
        qty_sold = max(0.0, -delta_qty)
        proceeds = max(0.0, delta_cash)
        if qty_sold > 0 and proceeds > 0:
            fee = proceeds * fee_rate
            fees += fee
            if avg is not None:
                realized += (proceeds - fee) - (qty_sold * avg)
            pos = max(0.0, pos - qty_sold)
            if pos == 0.0:
                avg = None

    pnl[symbol] = {
        "position_qty": round(pos, 12),
        "avg_entry": (round(avg, 2) if avg is not None else None),
        "realized_usd": round(realized, 2),
        "fees_usd": round(fees, 2),
        "last_price": round(float(price), 2),
        "last_ts": now_ts,
        "last_action": action,
    }
    return pnl

def wait_for_engine_update(pre_mtime: float, timeout_sec: float = 8.0, home: Optional[Path] = None) -> Optional[dict]:
    p_app = engine_app_state_path(home)
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            if p_app.exists():
                mt = p_app.stat().st_mtime
                if mt != pre_mtime:
                    return read_json(p_app, {}) or {}
        except Exception:
            pass
        time.sleep(0.25)
    return None


def trade_log_path(home: Optional[Path] = None) -> Path:
    h = Path.home() if home is None else home
    return h / "v71_clean" / "signals" / "trade_history.jsonl"


def append_trade_log(row: Dict[str, Any], home: Optional[Path] = None) -> None:
    p = trade_log_path(home)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def update_after_confirm(
    symbol: str,
    action: str,
    price: float,
    pre_cash: float,
    pre_qty: float,
    pre_mtime: float,
    fee_rate: float = PNL_FEE_RATE_DEFAULT,
    home: Optional[Path] = None,
) -> Dict[str, Any]:
    post_state = wait_for_engine_update(pre_mtime, timeout_sec=8.0, home=home)
    if post_state is None:
        return {"ok": False, "note": "engine_not_updated_yet"}

    post_cash, post_qty = get_cash_and_qty(post_state, symbol)
    delta_cash = post_cash - pre_cash
    delta_qty = post_qty - pre_qty

    pf = pnl_path(home)
    pnl = read_json(pf, {}) or {}
    pnl = apply_delta(pnl, symbol, action, price, delta_cash, delta_qty, fee_rate=fee_rate)
    write_json(pf, pnl)

    trade_row = {
        "timestamp": int(time.time()),
        "symbol": symbol,
        "action": action,
        "price": float(price),
        "pre_cash": round(pre_cash, 2),
        "post_cash": round(post_cash, 2),
        "delta_cash": round(delta_cash, 2),
        "pre_qty": round(pre_qty, 12),
        "post_qty": round(post_qty, 12),
        "delta_qty": round(delta_qty, 12),
        "fee_rate": float(fee_rate),
        "pnl_path": str(pf),
    }
    try:
        append_trade_log(trade_row, home=home)
    except Exception:
        pass

    return {
        "ok": True,
        "symbol": symbol,
        "action": action,
        "price": float(price),
        "delta_cash": round(delta_cash, 2),
        "delta_qty": round(delta_qty, 12),
        "pnl_path": str(pf),
    }
