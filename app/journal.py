import json, time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from app.paths import ensure_dirs
except Exception:
    ensure_dirs = None  # fallback if import order weird during tests


def _now_ts() -> int:
    return int(time.time())


def _safe_mkdir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def append_event(path: Path, event: Dict[str, Any]) -> None:
    """
    Append JSONL line to a journal file. Never overwrites.
    """
    _safe_mkdir(path)
    event = dict(event or {})
    event.setdefault("ts", _now_ts())
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_last_event(path: Path, max_bytes: int = 100_000) -> Optional[Dict[str, Any]]:
    """
    Read last JSONL record (best-effort). Returns None if empty/unreadable.
    """
    try:
        if not path.exists():
            return None
        # Read tail-ish to avoid huge memory
        data = path.read_bytes()
        if len(data) > max_bytes:
            data = data[-max_bytes:]
        lines = data.splitlines()
        for raw in reversed(lines):
            raw = raw.strip()
            if not raw:
                continue
            try:
                return json.loads(raw.decode("utf-8", errors="ignore"))
            except Exception:
                continue
        return None
    except Exception:
        return None
