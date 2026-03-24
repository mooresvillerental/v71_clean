from pathlib import Path
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

SIGNAL_PATH = Path("signals/latest_signal.json")
PORTFOLIO_PATH = Path("signals/assistant_portfolio.json")
LOCK_PATH = Path("signals/assistant_signal_lock.json")
TRADE_HISTORY_PATH = Path("signals/assistant_trade_history.json")
UI_PATH = Path("ui/index.html")

def load_json(path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except:
        return default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))

def load_signal():
    return load_json(SIGNAL_PATH)

def load_portfolio():
    return load_json(PORTFOLIO_PATH, {"cash_usd": 0.0, "holdings": {}})

def save_portfolio(p):
    save_json(PORTFOLIO_PATH, p)

def load_lock():
    return load_json(LOCK_PATH, {})

def save_lock(lock):
    save_json(LOCK_PATH, lock)

def load_trade_history():
    return load_json(TRADE_HISTORY_PATH, [])

def save_trade_history(history):
    save_json(TRADE_HISTORY_PATH, history)

def append_trade_history(entry):
    hist = load_trade_history()
    hist.append(entry)
    save_trade_history(hist)

def apply_trade(signal):
    portfolio = load_portfolio()

    symbol = signal["symbol"]
    action = signal["action"]
    price = float(signal["price"])
    usd = float(signal.get("suggested_trade_usd", 0) or 0)

    before_cash = float(portfolio.get("cash_usd", 0.0))
    holdings = portfolio.setdefault("holdings", {})
    asset = holdings.setdefault(symbol, {"qty": 0.0, "avg_price": 0.0})

    before_qty = float(asset.get("qty", 0.0))
    before_avg = float(asset.get("avg_price", 0.0))

    trade_entry = {
        "symbol": symbol,
        "action": action,
        "price": price,
        "timestamp": signal.get("timestamp"),
        "before_cash_usd": before_cash,
        "before_qty": before_qty,
        "before_avg_price": before_avg,
    }

    if action == "BUY":
        qty = usd / price if price > 0 else 0.0
        portfolio["cash_usd"] = before_cash - usd

        new_qty = before_qty + qty
        new_avg = before_avg
        if new_qty > 0:
            new_avg = ((before_avg * before_qty) + (price * qty)) / new_qty

        asset["qty"] = new_qty
        asset["avg_price"] = new_avg

        trade_entry.update({
            "size_usd": usd,
            "filled_qty": qty,
            "after_cash_usd": float(portfolio["cash_usd"]),
            "after_qty": float(asset["qty"]),
            "after_avg_price": float(asset["avg_price"]),
        })

    elif action == "SELL":
        qty = before_qty
        proceeds = qty * price
        realized_pnl = (price - before_avg) * qty if qty > 0 else 0.0

        portfolio["cash_usd"] = before_cash + proceeds
        asset["qty"] = 0.0
        asset["avg_price"] = 0.0

        trade_entry.update({
            "filled_qty": qty,
            "proceeds_usd": proceeds,
            "realized_pnl_usd": realized_pnl,
            "after_cash_usd": float(portfolio["cash_usd"]),
            "after_qty": 0.0,
            "after_avg_price": 0.0,
        })

    save_portfolio(portfolio)
    append_trade_history(trade_entry)
    return portfolio

def compute_assistant_performance():
    hist = load_trade_history()
    portfolio = load_portfolio()
    signal = load_signal() or {}
    current_price = float(signal.get("price", 0) or 0)

    if not hist:
        current_value = float(portfolio.get("cash_usd", 0.0))
        return {
            "accepted_trades": 0,
            "completed_sells": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "realized_pnl_usd": 0.0,
            "current_portfolio_value": round(current_value, 2),
        }

    first_cash = hist[0].get("before_cash_usd", 0.0)
    first_qty = hist[0].get("before_qty", 0.0)
    first_avg = hist[0].get("before_avg_price", 0.0)
    start_value = float(first_cash) + float(first_qty) * float(first_avg)

    current_cash = float(portfolio.get("cash_usd", 0.0))
    current_holdings = (portfolio.get("holdings", {}) or {}).get("BTC-USD", {}) or {}
    current_qty = float(current_holdings.get("qty", 0.0))
    current_value = current_cash + current_qty * current_price

    sells = [x for x in hist if x.get("action") == "SELL"]
    wins = sum(1 for x in sells if float(x.get("realized_pnl_usd", 0.0)) > 0)
    losses = sum(1 for x in sells if float(x.get("realized_pnl_usd", 0.0)) <= 0)
    realized = sum(float(x.get("realized_pnl_usd", 0.0)) for x in sells)
    win_rate = (wins / len(sells) * 100.0) if sells else 0.0
    return_pct = ((current_value - start_value) / start_value * 100.0) if start_value > 0 else 0.0

    return {
        "accepted_trades": len(hist),
        "completed_sells": len(sells),
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "realized_pnl_usd": round(realized, 2),
        "starting_portfolio_value": round(start_value, 2),
        "current_portfolio_value": round(current_value, 2),
        "return_pct": round(return_pct, 2),
    }

class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(body)


    def send_html(self, html, code=200):
        body = html.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/", "/dashboard"):
            try:
                return self.send_html(UI_PATH.read_text(encoding="utf-8"))
            except Exception as e:
                return self.send_json({"error": "ui_not_found", "detail": str(e)}, 500)

        if self.path == "/dashboard-data":
            return self.send_json({
                "latest_signal": load_signal(),
                "assistant_portfolio": load_portfolio(),
                "assistant_performance": compute_assistant_performance(),
            })

        if self.path == "/assistant-portfolio":
            return self.send_json(load_portfolio())

        if self.path == "/assistant-performance":
            return self.send_json(compute_assistant_performance())

        if self.path == "/assistant-trade-history":
            return self.send_json(load_trade_history())

        if self.path == "/latest-signal":
            sig = load_signal() or {}
            try:
                price_data = load_json(Path("signals/latest_price.json"), {})
                sig["live_price"] = price_data.get("price")
            except Exception:
                sig["live_price"] = None
            return self.send_json(sig)

        if self.path == "/shadow-stats":
            def read_jsonl(path):
                rows = []
                p = Path(path)
                if not p.exists():
                    return rows
                for line in p.read_text(encoding="utf-8").splitlines():
                    line=line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except:
                        pass
                return rows

            open_rows = read_jsonl("signals/shadow_trades_open.jsonl")
            closed_rows = read_jsonl("signals/shadow_trades_closed.jsonl")
            blocked_rows = read_jsonl("signals/shadow_trades_blocked.jsonl")

            wins = len([r for r in closed_rows if float(r.get("pnl_pct",0) or 0) > 0])
            losses = len([r for r in closed_rows if float(r.get("pnl_pct",0) or 0) <= 0])

            avg = 0
            if closed_rows:
                avg = sum(float(r.get("pnl_pct",0) or 0) for r in closed_rows)/len(closed_rows)

            last = closed_rows[-1] if closed_rows else None

            return self.send_json({
                "open_count": len(open_rows),
                "closed_count": len(closed_rows),
                "blocked_count": len(blocked_rows),
                "wins": wins,
                "losses": losses,
                "win_rate_pct": (wins/len(closed_rows)*100) if closed_rows else 0,
                "avg_pnl_pct": avg,
                "last_closed": last
            })
        if self.path == "/strategy-stats":
            def read_jsonl(path):
                rows = []
                p = Path(path)
                if not p.exists():
                    return rows
                for line in p.read_text().splitlines():
                    line=line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except:
                        pass
                return rows

            closed_rows = read_jsonl("signals/shadow_trades_closed.jsonl")

            stats = {}

            for r in closed_rows:
                strat = r.get("winning_strategy") or r.get("strategy") or "UNKNOWN"
                pnl = float(r.get("pnl_pct",0) or 0)

                if strat not in stats:
                    stats[strat] = {"trades":0,"wins":0,"pnl_total":0}

                stats[strat]["trades"] += 1
                stats[strat]["pnl_total"] += pnl

                if pnl > 0:
                    stats[strat]["wins"] += 1

            result = []

            for strat,data in stats.items():
                trades = data["trades"]
                wins = data["wins"]
                pnl_total = data["pnl_total"]

                result.append({
                    "strategy": strat,
                    "trades": trades,
                    "wins": wins,
                    "win_rate": (wins/trades*100) if trades else 0,
                    "avg_pnl": (pnl_total/trades) if trades else 0
                })

            return self.send_json(result)

        if self.path == "/assistant-lock":
            return self.send_json(load_lock())

        
        if self.path == "/assistant-reset-session":
            save_portfolio({"cash_usd":1500,"holdings":{"BTC-USD":{"qty":0.01,"avg_price":45000}}})
            save_trade_history([])
            save_lock({})
            return self.send_json({"status":"session_reset"})

        return self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/assistant-set-portfolio":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode())
            save_portfolio(data)
            return self.send_json({
                "status": "portfolio_updated",
                "portfolio": data
            })

        if self.path == "/assistant-confirm":
            signal = load_signal()
            if not signal:
                return self.send_json({"error": "no signal"}, 400)

            signal_id = str(signal.get("timestamp"))
            lock = load_lock()

            if lock.get(signal_id):
                return self.send_json({
                    "status": "blocked",
                    "reason": "signal already executed",
                    "signal_id": signal_id
                })

            portfolio = apply_trade(signal)
            lock[signal_id] = True
            save_lock(lock)

            return self.send_json({
                "status": "trade_applied",
                "signal_id": signal_id,
                "portfolio": portfolio
            })

        
        if self.path == "/assistant-reset-session":
            save_portfolio({"cash_usd":1500,"holdings":{"BTC-USD":{"qty":0.01,"avg_price":45000}}})
            save_trade_history([])
            save_lock({})
            return self.send_json({"status":"session_reset"})

        return self.send_json({"error": "not found"}, 404)

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    print("EZTRADER API running on port 8000")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
