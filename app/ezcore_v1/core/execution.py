from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .config import CoreConfig


@dataclass
class Fill:
    filled: bool
    price: float
    qty: float
    fee_usd: float
    notes: str


class ExecutionLayer:
    """v1: paper execution. Live wiring will adapt this interface later without touching strategies/risk."""

    def __init__(self, cfg: CoreConfig, log):
        self.cfg = cfg
        self.log = log

    def _fee(self, notional_usd: float) -> float:
        return notional_usd * (self.cfg.fee_bps / 10000.0)

    def paper_buy(self, st: Dict[str, Any], symbol: str, price: float, trade_usd: float) -> Fill:
        fee = self._fee(trade_usd)
        effective_usd = max(0.0, trade_usd - fee)
        qty = 0.0 if price <= 0 else (effective_usd / price)

        if trade_usd > float(st.get("cash_usd", 0.0)) + 1e-9:
            return Fill(False, price, 0.0, 0.0, "Insufficient cash")

        st["cash_usd"] = float(st.get("cash_usd", 0.0)) - trade_usd
        st.setdefault("holdings", {})
        st["holdings"][symbol] = float(st["holdings"].get(symbol, 0.0)) + qty
        return Fill(True, price, qty, fee, "Paper BUY fill")

    def paper_sell_all(self, st: Dict[str, Any], symbol: str, price: float) -> Fill:
        qty = float(st.get("holdings", {}).get(symbol, 0.0))
        if qty <= 0.0:
            return Fill(False, price, 0.0, 0.0, "No holdings")

        gross = qty * price
        fee = self._fee(gross)
        net = max(0.0, gross - fee)

        st["cash_usd"] = float(st.get("cash_usd", 0.0)) + net
        st["holdings"][symbol] = 0.0
        return Fill(True, price, qty, fee, "Paper SELL fill")
