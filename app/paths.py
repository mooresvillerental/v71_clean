# app/paths.py
# Single source of truth for EZTrader file paths (v71+)

import os
from pathlib import Path

HOME = str(Path.home())

def _dflt(name: str, fallback: str) -> str:
    v = os.environ.get(name)
    return v if (v is not None and str(v).strip() != "") else fallback

# Canonical v71 defaults (can be overridden only via EZ_* env vars)
EZ_ENGINE_DATA_DIR = _dflt("EZ_ENGINE_DATA_DIR", os.path.join(HOME, "v71_engine_data"))
EZ_APP_DATA_DIR    = _dflt("EZ_APP_DATA_DIR",    os.path.join(HOME, "v71_app_data"))

ENGINE_STATE_PATH  = _dflt("EZ_ENGINE_STATE_PATH", os.path.join(EZ_ENGINE_DATA_DIR, "state.json"))
APP_STATE_PATH     = _dflt("EZ_APP_STATE_PATH",    os.path.join(EZ_APP_DATA_DIR,    "state.json"))
CONFIRM_PATH       = _dflt("EZ_CONFIRM_PATH",      os.path.join(EZ_APP_DATA_DIR,    "confirm.json"))
SETTINGS_PATH      = _dflt("EZ_SETTINGS_PATH",     os.path.join(EZ_APP_DATA_DIR,    "settings.json"))
ALERTS_PATH        = _dflt("EZ_ALERTS_PATH",       os.path.join(EZ_APP_DATA_DIR,    "alerts.json"))

def ensure_dirs() -> None:
    # Ensure parent directories exist for app storage
    for p in (ENGINE_STATE_PATH, APP_STATE_PATH, CONFIRM_PATH, SETTINGS_PATH, ALERTS_PATH):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
        except Exception:
            pass
