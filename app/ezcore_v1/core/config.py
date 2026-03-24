from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CoreConfig:
    # --- mode ---
    signal_only_manual_confirm: bool = True  # v1 default (safe)

    # --- symbols/timeframes (defaults; not a menu) ---
    primary_symbol: str = "BTC-USD"
    tf_entry: str = "15m"
    tf_trend: str = "1h"

    # --- execution policy ---
    limit_first: bool = True
    limit_timeout_sec: int = 20
    allow_market_fallback: bool = True
    slippage_cap_bps: int = 25  # 0.25%

    # --- risk ---
    max_risk_per_trade_pct: float = 0.0075   # 0.75%
    position_size_pct_equity: float = 0.10   # 10%
    min_trade_usd: float = 25.0
    max_trade_usd: float = 500.0

    max_daily_loss_pct: float = 0.02         # 2%
    max_drawdown_pct: float = 0.06           # 6%
    cooldown_bars_after_exit: int = 3

    # --- balances guards ---
    min_cash_usd: float = 10.0
    min_base_qty: float = 1e-8  # SELL suppression guard

    # --- backtest realism knobs ---
    fee_bps: int = 10
    assumed_slippage_bps: int = 5

    # --- files ---
    state_path: str = "app/ezcore_v1_state.json"
    log_path: str = "logs/ezcore_v1.log"
    events_path: str = "logs/ezcore_v1_events.jsonl"

    # --- alerts ---
    enable_tts: bool = True
    tts_rate: float = 1.0
    tts_engine: Optional[str] = None
