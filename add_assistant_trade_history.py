import json
from pathlib import Path

API_FILE = Path("api_server_stdlib.py")
code = API_FILE.read_text()

insert = '''

TRADE_HISTORY_PATH = Path("signals/assistant_trade_history.json")

def load_trade_history():
    if not TRADE_HISTORY_PATH.exists():
        return []
    return json.loads(TRADE_HISTORY_PATH.read_text())

def save_trade_history(history):
    TRADE_HISTORY_PATH.write_text(json.dumps(history, indent=2))
'''

if "assistant_trade_history" not in code:
    code = insert + "\n" + code
    API_FILE.write_text(code)
    print("Trade history helpers added")
else:
    print("Trade history already exists")
