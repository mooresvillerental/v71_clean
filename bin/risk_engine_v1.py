#!/usr/bin/env python3
"""
EZTrader Risk Engine v1
- Hard max drawdown cap (kill switch)
- Soft drawdown compression (position size multiplier)
"""

from dataclasses import dataclass

@dataclass
class RiskConfig:
    dd_cap_pct: float = 30.0      # HARD stop at this drawdown %
    soft1_pct: float = 10.0       # start compressing
    soft2_pct: float = 20.0
    soft3_pct: float = 25.0
    m1: float = 0.75              # 10–20%
    m2: float = 0.50              # 20–25%
    m3: float = 0.25              # 25–cap
    min_equity: float | None = None  # optional absolute floor (USD)

def dd_pct(peak_equity: float, equity: float) -> float:
    if peak_equity <= 0:
        return 0.0
    d = (peak_equity - equity) / peak_equity * 100.0
    return max(0.0, d)

def size_multiplier(config: RiskConfig, dd_now_pct: float) -> float:
    # 0–soft1: 1.0
    if dd_now_pct < config.soft1_pct:
        return 1.0
    # soft1–soft2
    if dd_now_pct < config.soft2_pct:
        return float(config.m1)
    # soft2–soft3
    if dd_now_pct < config.soft3_pct:
        return float(config.m2)
    # soft3–cap
    if dd_now_pct < config.dd_cap_pct:
        return float(config.m3)
    return 0.0

def should_halt(config: RiskConfig, peak_equity: float, equity: float) -> tuple[bool, str]:
    d = dd_pct(peak_equity, equity)
    if config.min_equity is not None and equity <= config.min_equity:
        return True, f"HALT: equity {equity:.2f} <= min_equity {config.min_equity:.2f}"
    if d >= config.dd_cap_pct:
        return True, f"HALT: drawdown {d:.2f}% >= cap {config.dd_cap_pct:.2f}%"
    return False, ""
