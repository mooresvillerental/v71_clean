import json
from pathlib import Path

API_FILE = Path("api_server_stdlib.py")

code = API_FILE.read_text()

insert = '''

def portfolio_value(portfolio, price):
    cash = float(portfolio.get("cash_usd",0))
    holdings = portfolio.get("holdings",{})
    btc = float((holdings.get("BTC-USD") or {}).get("qty",0))

    return cash + btc * price
'''

if "portfolio_value(" not in code:
    code = code.replace("def apply_trade(signal):", insert + "\n\ndef apply_trade(signal):")

API_FILE.write_text(code)

print("Portfolio value helper added")
