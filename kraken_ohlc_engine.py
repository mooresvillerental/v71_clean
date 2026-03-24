import websocket
import json
from pathlib import Path

OHLC_FILE = Path("signals/ohlc_live.json")
PRICE_FILE = Path("signals/latest_price.json")

highs=[]
lows=[]
closes=[]
volumes=[]

def save_ohlc():
    data={
        "highs":highs[-300:],
        "lows":lows[-300:],
        "closes":closes[-300:],
        "volumes":volumes[-300:]
    }
    OHLC_FILE.write_text(json.dumps(data,indent=2))

    if closes:
        PRICE_FILE.write_text(json.dumps({
            "symbol": "BTC-USD",
            "price": closes[-1]
        }, indent=2))

def on_message(ws,message):
    msg=json.loads(message)

    if isinstance(msg,list) and len(msg)>1 and isinstance(msg[1],list):

        try:
            candle=msg[1]

            high=float(candle[2])
            low=float(candle[3])
            close=float(candle[4])
            volume=float(candle[6])

            highs.append(high)
            lows.append(low)
            closes.append(close)
            volumes.append(volume)

            save_ohlc()

            print("Candle close:",close)

        except Exception as e:
            print("Parse error:",e)

def on_open(ws):
    sub={
        "event":"subscribe",
        "pair":["XBT/USD"],
        "subscription":{
            "name":"ohlc",
            "interval":1
        }
    }

    ws.send(json.dumps(sub))
    print("Subscribed to Kraken OHLC 1m feed")

ws=websocket.WebSocketApp(
    "wss://ws.kraken.com",
    on_open=on_open,
    on_message=on_message
)

print("Connecting to Kraken OHLC feed...")
ws.run_forever()
