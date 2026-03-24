import websocket
import json
from pathlib import Path

PRICE_FILE = Path("signals/latest_price.json")

def save_price(price):
    data = {"symbol":"BTC-USD","price":price}
    PRICE_FILE.write_text(json.dumps(data))

def on_message(ws, message):
    msg = json.loads(message)

    if isinstance(msg, list) and len(msg) > 1:
        try:
            price = float(msg[1]["c"][0])
            save_price(price)
            print("BTC price:", price)
        except:
            pass

def on_open(ws):
    sub = {
        "event":"subscribe",
        "pair":["XBT/USD"],
        "subscription":{"name":"ticker"}
    }
    ws.send(json.dumps(sub))

ws = websocket.WebSocketApp(
    "wss://ws.kraken.com",
    on_open=on_open,
    on_message=on_message
)

print("Connecting to Kraken price feed...")
ws.run_forever()
