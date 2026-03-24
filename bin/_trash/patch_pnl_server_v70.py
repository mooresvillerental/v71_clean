from pathlib import Path
import re, time, sys, shutil, subprocess, json

TARGET = Path("app/server.py")
if not TARGET.exists():
    print("ERROR: app/server.py not found. Are you in ~/v70_host ?")
    sys.exit(1)

src = TARGET.read_text()
bak = TARGET.with_suffix(f".py.bak_PNL_{int(time.time())}")
shutil.copy2(TARGET, bak)
print("Backup:", bak)

# --- helpers to inject (idempotent) ---
HELPERS = r'''
# --- PNL TRACKING (server-side, safe) ---
from pathlib import Path as _Path
import json as _json
import time as _time

PNL_FEE_RATE = 0.01  # 1% per side (BUY and SELL) - user preference

def _read_json(path: _Path, default=None):
    try:
        if not path.exists():
            return default
        return _json.loads(path.read_text())
    except Exception:
        return default

def _write_json(path: _Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(obj, indent=2, sort_keys=True))

def _engine_app_state_path():
    return _Path.home() / "v69_app_data" / "app_state.json"

def _pnl_path():
    return _Path.home() / "v70_app_data" / "pnl.json"

def _get_cash_and_qty(app_state: dict, symbol: str):
    cash = float(app_state.get("cash_usd", 0.0))
    holdings = app_state.get("holdings", {}) or {}
    qty = float(holdings.get(symbol, 0.0))
    return cash, qty

def _pnl_apply_delta(pnl: dict, symbol: str, action: str, price: float, delta_cash: float, delta_qty: float):
    # pnl structure per symbol:
    # {position_qty, avg_entry, realized_usd, fees_usd, last_price, last_ts, last_action}
    p = pnl.get(symbol) or {}
    pos = float(p.get("position_qty", 0.0))
    avg = p.get("avg_entry", None)
    avg = float(avg) if avg is not None else None
    realized = float(p.get("realized_usd", 0.0))
    fees = float(p.get("fees_usd", 0.0))

    now_ts = _time.strftime("%Y-%m-%d %I:%M:%S %p")

    if action == "BUY":
        # Expect: delta_qty > 0, delta_cash < 0
        qty_bought = max(0.0, delta_qty)
        spend = max(0.0, -delta_cash)
        if qty_bought > 0 and spend > 0:
            entry = spend / qty_bought
            # weighted avg
            if pos <= 0 or avg is None:
                avg = entry
                pos = qty_bought
            else:
                new_pos = pos + qty_bought
                avg = ((avg * pos) + (entry * qty_bought)) / new_pos
                pos = new_pos
            fees += spend * PNL_FEE_RATE

    elif action == "SELL":
        # Expect: delta_qty < 0, delta_cash > 0
        qty_sold = max(0.0, -delta_qty)
        proceeds = max(0.0, delta_cash)
        if qty_sold > 0 and proceeds > 0:
            # fee on proceeds
            fee = proceeds * PNL_FEE_RATE
            fees += fee
            # realized P&L uses avg_entry if known
            if avg is None:
                # If we don't have avg yet, treat as unknown basis (still record fee + position)
                pass
            else:
                realized += (proceeds - fee) - (qty_sold * avg)
            pos = max(0.0, pos - qty_sold)
            if pos == 0.0:
                # reset avg when flat
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

def _pnl_update_after_confirm(symbol: str, action: str, price: float, pre_cash: float, pre_qty: float, pre_mtime: float):
    # Wait for engine to process confirm by watching app_state.json mtime.
    p_app = _engine_app_state_path()
    deadline = _time.time() + 8.0
    post_state = None
    post_mtime = pre_mtime
    while _time.time() < deadline:
        try:
            if p_app.exists():
                mt = p_app.stat().st_mtime
                if mt != pre_mtime:
                    post_mtime = mt
                    post_state = _read_json(p_app, {}) or {}
                    break
        except Exception:
            pass
        _time.sleep(0.25)

    if post_state is None:
        # Engine didn't update in time; don't break anything—just skip P&L update.
        return {"ok": False, "note": "engine_not_updated_yet"}

    post_cash, post_qty = _get_cash_and_qty(post_state, symbol)
    delta_cash = post_cash - pre_cash
    delta_qty = post_qty - pre_qty

    pnl_file = _pnl_path()
    pnl = _read_json(pnl_file, {}) or {}
    pnl = _pnl_apply_delta(pnl, symbol, action, price, delta_cash, delta_qty)
    _write_json(pnl_file, pnl)

    return {
        "ok": True,
        "symbol": symbol,
        "action": action,
        "price": price,
        "delta_cash": round(delta_cash, 2),
        "delta_qty": round(delta_qty, 12),
        "pnl_path": str(pnl_file),
    }
# --- END PNL TRACKING ---
'''

# 1) Inject helpers once (near imports). If already present, skip.
if "PNL TRACKING (server-side, safe)" not in src:
    # Put helpers after the first import block (best-effort)
    m = re.search(r'^(import[^\n]*\n|from[^\n]*\n)+', src, re.M)
    if m:
        insert_at = m.end()
        src = src[:insert_at] + "\n" + HELPERS + "\n" + src[insert_at:]
    else:
        src = HELPERS + "\n" + src

# 2) Add /pnl endpoint (idempotent).
if '"/pnl"' not in src and "def pnl_endpoint" not in src:
    # Insert into handler routing area by matching existing path checks.
    # server.py in this repo uses a BaseHTTPRequestHandler router; we add a small branch where other GET routes are.
    # We'll look for a GET route for "/health" or "/signal" and insert adjacent.
    # Best anchor: a line like: if path == "/health":
    anchor = re.search(r'(\n\s*if\s+path\s*==\s*"/health"\s*:\s*\n)', src)
    if not anchor:
        print("ERROR: Could not find GET router anchor (if path == \"/health\").")
        TARGET.write_text(src)
        sys.exit(1)

    add = r'''
        if path == "/pnl":
            pnl = _read_json(_pnl_path(), {}) or {}
            return self._send_json(200, {"ok": True, "pnl": pnl})
'''
    pos = anchor.end()
    src = src[:pos] + add + src[pos:]

# 3) Hook into POST /confirm to compute P&L deltas after engine processes confirm.
# We need to find where /confirm POST is handled.
# Anchor: a line containing: if path == "/confirm":
confirm_anchor = re.search(r'(\n\s*if\s+path\s*==\s*"/confirm"\s*:\s*\n)', src)
if not confirm_anchor:
    print("ERROR: Could not find POST /confirm handler anchor.")
    TARGET.write_text(src)
    sys.exit(1)

# We only add the hook once.
if "PNL_AFTER_CONFIRM_HOOK" not in src:
    hook = r'''
            # --- PNL_AFTER_CONFIRM_HOOK ---
            try:
                # capture pre-state (engine app_state.json)
                _p_app = _engine_app_state_path()
                _pre = _read_json(_p_app, {}) or {}
                _pre_mtime = _p_app.stat().st_mtime if _p_app.exists() else 0.0
                _sym = (sig.get("symbol") or "BTC-USD")
                _price = float(sig.get("price") or 0.0)
                _pre_cash, _pre_qty = _get_cash_and_qty(_pre, _sym)
            except Exception:
                _pre_cash = 0.0
                _pre_qty = 0.0
                _pre_mtime = 0.0
                _sym = (sig.get("symbol") or "BTC-USD") if isinstance(sig, dict) else "BTC-USD"
                _price = float(sig.get("price") or 0.0) if isinstance(sig, dict) else 0.0
            # --- END PNL_AFTER_CONFIRM_HOOK ---
'''
    # Insert hook shortly AFTER sig is computed in confirm handler.
    # Common pattern in this server: sig = load_signal() or similar; we search for "sig =" within this block.
    block_start = confirm_anchor.end()
    # Find the first "sig =" after block_start
    m_sig = re.search(r'\n(\s*)sig\s*=\s*[^\n]+\n', src[block_start:])
    if not m_sig:
        print("ERROR: Could not locate 'sig =' line inside /confirm block.")
        TARGET.write_text(src)
        sys.exit(1)
    indent = m_sig.group(1)
    # Ensure hook indentation matches block
    hook_indented = "\n".join((indent + line if line.strip() else line) for line in hook.splitlines())
    insert_at = block_start + m_sig.end()
    src = src[:insert_at] + hook_indented + "\n" + src[insert_at:]

    # Now add the "after confirm write" update, just before the handler returns success JSON.
    # Anchor for return success in confirm: return self._send_json(200, {...}) or similar.
    # We'll add right before the first occurrence of "_send_json(200" after confirm block start.
    m_ret = re.search(r'\n(\s*)return\s+self\._send_json\(\s*200\s*,', src[block_start:])
    if not m_ret:
        print("ERROR: Could not locate success return in /confirm block.")
        TARGET.write_text(src)
        sys.exit(1)
    ret_indent = m_ret.group(1)
    after = r'''
            try:
                _pnlr = _pnl_update_after_confirm(_sym, action, _price, _pre_cash, _pre_qty, _pre_mtime)
            except Exception as _e:
                _pnlr = {"ok": False, "note": "pnl_exception", "detail": str(_e)}
'''
    after_indented = "\n".join((ret_indent + line if line.strip() else line) for line in after.splitlines())
    insert_at2 = block_start + m_ret.start()
    src = src[:insert_at2] + after_indented + "\n" + src[insert_at2:]

# Write + compile check
TARGET.write_text(src)
r = subprocess.run([sys.executable, "-m", "py_compile", str(TARGET)], capture_output=True, text=True)
if r.returncode != 0:
    print("COMPILE FAILED - restoring backup.")
    TARGET.write_text(bak.read_text())
    print((r.stderr or r.stdout).strip())
    sys.exit(1)

print("OK: P&L patch installed (server-side) + syntax OK.")
print("Next: restart server (engine can stay running).")
