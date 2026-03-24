from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict


def now_day_key() -> str:
    return time.strftime("%Y-%m-%d")


def default_state(primary_symbol: str) -> Dict[str, Any]:
    # Asset-agnostic: cash is global; holdings are per-symbol.
    return {
        "cash_usd": 1500.0,
        "holdings": {primary_symbol: 0.0},
        "position": {},  # per symbol
        "stats": {
            "equity_peak": 1500.0,
            "drawdown_pct": 0.0,
            "day_key": now_day_key(),
            "daily_pnl_usd": 0.0,
            "disabled_until_day": None,
            "disabled_reason": None,
        },
        "cooldowns": {},  # per symbol
        "last_event_id": None,
        "version": "ezcore_v1",
    }


@dataclass
class StateStore:
    path: str
    primary_symbol: str

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.path):
            st = default_state(self.primary_symbol)
            self.save(st)
            return st

        with open(self.path, "r", encoding="utf-8") as f:
            st = json.load(f)

        # minimal schema healing
        st.setdefault("cash_usd", 1500.0)
        st.setdefault("holdings", {})
        st["holdings"].setdefault(self.primary_symbol, 0.0)
        st.setdefault("position", {})
        st.setdefault("cooldowns", {})
        st.setdefault("stats", {})
        st["stats"].setdefault("equity_peak", st.get("cash_usd", 0.0))
        st["stats"].setdefault("drawdown_pct", 0.0)
        st["stats"].setdefault("day_key", now_day_key())
        st["stats"].setdefault("daily_pnl_usd", 0.0)
        st["stats"].setdefault("disabled_until_day", None)
        st["stats"].setdefault("disabled_reason", None)
        st.setdefault("version", "ezcore_v1")
        return st

    def save(self, st: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)
