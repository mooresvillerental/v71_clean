import json
from pathlib import Path

portfolio_src = Path("/data/data/com.termux/files/home/v71_clean/signals/assistant_portfolio.json")
signal_src = Path("/data/data/com.termux/files/home/v71_clean/signals/latest_signal.json")
portfolio_dst = Path("/data/data/com.termux/files/home/v71_clean/portfolio.json")

with portfolio_src.open("r", encoding="utf-8") as f:
    p = json.load(f)

with signal_src.open("r", encoding="utf-8") as f:
    s = json.load(f)

cash = float(p.get("cash_usd", 0))
holding = p.get("holdings", {}).get("BTC-USD", {})
qty = float(holding.get("qty", 0))
avg_price = float(holding.get("avg_price", 0))
current_price = float(s.get("price", 0))

portfolio_value = cash + (qty * current_price)
unrealized_pl = (current_price - avg_price) * qty

public = {
    "cash_usd": round(cash, 2),
    "btc_qty": qty,
    "avg_price": round(avg_price, 2),
    "current_price": round(current_price, 2),
    "portfolio_value": round(portfolio_value, 2),
    "unrealized_pl": round(unrealized_pl, 2)
}

with portfolio_dst.open("w", encoding="utf-8") as f:
    json.dump(public, f, indent=2)

print("Wrote", portfolio_dst)
print(json.dumps(public, indent=2))
