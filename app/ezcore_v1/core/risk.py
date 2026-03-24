from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .config import CoreConfig
from .state import now_day_key


@dataclass
class RiskDecision:
    allow: bool
    reason: str
    trade_usd: float = 0.0


class RiskManager:
    def __init__(self, cfg: CoreConfig, log):
        self.cfg = cfg
        self.log = log

    def _equity(self, st: Dict[str, Any], price: float, symbol: str) -> float:
        cash = float(st.get("cash_usd", 0.0))
        qty = float(st.get("holdings", {}).get(symbol, 0.0))
        return cash + (qty * price)

    def _roll_day(self, st: Dict[str, Any]) -> None:
        dk = now_day_key()
        if st.get("stats", {}).get("day_key") != dk:
            st.setdefault("stats", {})
            st["stats"]["day_key"] = dk
            st["stats"]["daily_pnl_usd"] = 0.0
            st["stats"]["disabled_until_day"] = None
            st["stats"]["disabled_reason"] = None

    def _update_drawdown(self, st: Dict[str, Any], equity: float) -> None:
        st.setdefault("stats", {})
        peak = float(st["stats"].get("equity_peak", equity))
        if equity > peak:
            peak = equity
        dd = 0.0 if peak <= 0 else max(0.0, (peak - equity) / peak)
        st["stats"]["equity_peak"] = peak
        st["stats"]["drawdown_pct"] = dd

    def check_killswitch(self, st: Dict[str, Any], equity: float) -> Optional[str]:
        self._roll_day(st)
        self._update_drawdown(st, equity)

        stats = st.get("stats", {})
        dd = float(stats.get("drawdown_pct", 0.0))
        if dd >= self.cfg.max_drawdown_pct:
            stats["disabled_until_day"] = "MANUAL_RESET"
            stats["disabled_reason"] = f"Max drawdown hit ({dd*100:.2f}%)"
            return stats["disabled_reason"]

        daily_pnl = float(stats.get("daily_pnl_usd", 0.0))
        peak = float(stats.get("equity_peak", equity))
        if peak > 0 and (-daily_pnl / peak) >= self.cfg.max_daily_loss_pct:
            stats["disabled_until_day"] = now_day_key()
            stats["disabled_reason"] = f"Max daily loss hit ({(-daily_pnl/peak)*100:.2f}%)"
            return stats["disabled_reason"]

        if stats.get("disabled_until_day") in (now_day_key(), "MANUAL_RESET"):
            return stats.get("disabled_reason") or "Trading disabled"

        return None

    def size_trade_usd(self, st: Dict[str, Any], price: float, symbol: str) -> float:
        equity = self._equity(st, price, symbol)
        raw = equity * self.cfg.position_size_pct_equity
        raw = max(self.cfg.min_trade_usd, min(self.cfg.max_trade_usd, raw))
        return float(raw)

    def allow_action(self, st: Dict[str, Any], action: str, symbol: str, price: float) -> RiskDecision:
        equity = self._equity(st, price, symbol)
        ks = self.check_killswitch(st, equity)
        if ks:
            return RiskDecision(False, ks, 0.0)

        cash = float(st.get("cash_usd", 0.0))
        qty = float(st.get("holdings", {}).get(symbol, 0.0))

        if action == "BUY":
            if cash < self.cfg.min_cash_usd:
                return RiskDecision(False, f"BUY blocked: cash_usd {cash:.2f} < min {self.cfg.min_cash_usd}", 0.0)
            trade_usd = min(self.size_trade_usd(st, price, symbol), cash)
            if trade_usd < self.cfg.min_trade_usd:
                return RiskDecision(False, f"BUY blocked: trade_usd {trade_usd:.2f} < min {self.cfg.min_trade_usd}", 0.0)
            return RiskDecision(True, "OK", trade_usd)

        if action == "SELL":
            if qty < self.cfg.min_base_qty:
                return RiskDecision(False, f"SELL blocked: holdings {qty:.10f} < min {self.cfg.min_base_qty}", 0.0)
            return RiskDecision(True, "OK", 0.0)

        return RiskDecision(False, "No action", 0.0)
