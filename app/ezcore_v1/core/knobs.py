from __future__ import annotations
import json, os
from typing import Any, Dict

DEFAULT_PATH = "logs/ezcore_v1_knobs.json"

def load_knobs(path: str = DEFAULT_PATH) -> Dict[str, Any]:
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}

def save_knobs(knobs: Dict[str, Any], path: str = DEFAULT_PATH) -> None:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        # MERGE with existing file so partial updates don't wipe other knobs
        base: Dict[str, Any] = {}
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    base = json.load(f) or {}
            if not isinstance(base, dict):
                base = {}
        except Exception:
            base = {}

        if isinstance(knobs, dict):
            base.update(knobs)

        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(base, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        # never let persistence break trading loop
        return
