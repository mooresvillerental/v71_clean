from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pathlib import Path
import json

app = FastAPI(title="EZTRADER API", version="1.0")

SIGNAL_PATH = Path("signals/latest_signal.json")

@app.get("/")
def root():
    return {"status": "ok", "service": "eztrader-api"}

@app.get("/signal")
def get_signal():
    if not SIGNAL_PATH.exists():
        return JSONResponse(status_code=404, content={"error": "no_signal"})
    try:
        data = json.loads(SIGNAL_PATH.read_text())
        return {"ok": True, "signal": data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
