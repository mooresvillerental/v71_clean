from __future__ import annotations

from typing import List, Optional


def ema(values: List[float], period: int) -> Optional[float]:
    if period <= 0 or len(values) < period:
        return None
    k = 2.0 / (period + 1.0)
    e = values[0]
    for v in values[1:]:
        e = (v * k) + (e * (1.0 - k))
    return e


def rsi(values: List[float], period: int = 14) -> Optional[float]:
    if period <= 0 or len(values) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        d = values[i] - values[i - 1]
        if d >= 0:
            gains += d
        else:
            losses += (-d)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100.0 - (100.0 / (1.0 + rs))


def true_range(high: float, low: float, prev_close: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    if period <= 0 or len(closes) < period + 1:
        return None
    trs = []
    for i in range(-period, 0):
        trs.append(true_range(highs[i], lows[i], closes[i - 1]))
    return sum(trs) / float(period)
