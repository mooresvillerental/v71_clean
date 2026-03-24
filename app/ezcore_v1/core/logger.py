from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class EventLogger:
    log_path: str
    events_path: str


    def __post_init__(self) -> None:
        # Ensure directories exist and both files are created even if nothing logs yet
        self._ensure_dirs()
        try:
            with open(self.events_path, "a", encoding="utf-8"):
                pass
        except Exception:
            pass

    def _ensure_dirs(self) -> None:
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        # ensure log file exists even if nothing logs yet
        try:
            with open(self.log_path, "a", encoding="utf-8") as _f:
                if _f.tell() == 0:
                    _f.write("[INIT] log created\n")
        except Exception:
            pass

        os.makedirs(os.path.dirname(self.events_path) or ".", exist_ok=True)


        # ensure events file exists even if no events are written

        try:

            with open(self.events_path, "a", encoding="utf-8") as _f:

                pass

        except Exception:

            pass

    def line(self, msg: str) -> None:
        self._ensure_dirs()
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{_ts()}] {msg}\n")

    def event(self, kind: str, payload: Dict[str, Any], event_id: Optional[str] = None) -> None:
        self._ensure_dirs()
        rec = {
            "ts": _ts(),
            "kind": kind,
            "event_id": event_id,
            "payload": payload,
        }
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
