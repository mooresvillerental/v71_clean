from __future__ import annotations

from typing import List

from ..core.indicators import atr, rsi
from ..data.models import Signal


def generate(symbol: str, highs: List[float], lows: List[float], closes: List[float], vols: List[float], price: float) -> Signal:
    rr = rsi(closes, 14)
    a = atr(highs, lows, closes, 14)
    if a is None or len(closes) < 70:
        return Signal("NONE", symbol, price, rr, 0, ["Not enough bars/ATR"], None, "B_VOL_BREAKOUT")

    hh20 = max(highs[-21:-1])
    ll20 = min(lows[-21:-1])

    breakout_up = closes[-1] > hh20
    breakout_down = closes[-1] < ll20

    avg20 = sum(vols[-21:-1]) / 20.0
    vol_ok = vols[-1] > avg20

    if breakout_up and vol_ok:
        return Signal(
            "BUY",
            symbol,
            price,
            rr,
            75,
            ["Breakout above HH20", "Volume above avg20", "ATR expansion proxy"],
            None,
            "B_VOL_BREAKOUT",
        )

    if breakout_down and vol_ok:
        return Signal(
            "SELL",
            symbol,
            price,
            rr,
            75,
            ["Breakdown below LL20", "Volume above avg20", "ATR expansion proxy"],
            None,
            "B_VOL_BREAKOUT",
        )

    return Signal("NONE", symbol, price, rr, 0, ["No breakout"], None, "B_VOL_BREAKOUT")
