from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pathlib import Path
import json
import os
import uvicorn
from urllib.request import urlopen, Request

app = FastAPI(title="EZTRADER API", version="1.1")

SIGNAL_URL = "http://127.0.0.1:18093/signal"
FALLBACK_SIGNAL_PATH = Path("signals/latest_signal.json")

@app.get("/")
def root():
    return {"status": "ok", "service": "eztrader-api"}

@app.get("/signal")
def get_signal():
    try:
        req = Request(SIGNAL_URL, headers={"Cache-Control": "no-cache"})
        with urlopen(req, timeout=5) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        sig = raw.get("signal", {}) if isinstance(raw, dict) else {}
        return {"ok": True, "signal": sig}
    except Exception:
        if not FALLBACK_SIGNAL_PATH.exists():
            return JSONResponse(status_code=404, content={"error": "no_signal"})
        try:
            data = json.loads(FALLBACK_SIGNAL_PATH.read_text(encoding="utf-8"))
            return {"ok": True, "signal": data, "fallback": True}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
