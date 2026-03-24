from __future__ import annotations

from typing import List

from ..core.indicators import ema, rsi
from ..data.models import Signal


def generate(symbol: str, closes_15m: List[float], closes_1h: List[float], price: float) -> Signal:
    rr = rsi(closes_15m, 14)

    # Trend filter (1h): close above EMA200
    ema200_1h = ema(closes_1h, 200)
    if ema200_1h is None or closes_1h[-1] <= ema200_1h:
        return Signal("NONE", symbol, price, rr, 0, ["Trend filter blocked"], None, "A_TREND_PULLBACK")

    # 15m structure: EMA50 > EMA200
    ema50 = ema(closes_15m, 50)
    ema200 = ema(closes_15m, 200)
    if ema50 is None or ema200 is None or ema50 <= ema200:
        return Signal("NONE", symbol, price, rr, 0, ["15m EMA structure not bullish"], None, "A_TREND_PULLBACK")

    if rr is None:
        return Signal("NONE", symbol, price, None, 0, ["RSI unavailable"], None, "A_TREND_PULLBACK")

    # Pullback trigger (approx): RSI dipped <40 recently and now >=45
    dipped = False
    for k in range(1, 6):
        if len(closes_15m) > 14 + k:
            rv = rsi(closes_15m[:-k], 14)
            if rv is not None and rv < 40.0:
                dipped = True
                break

    if dipped and rr >= 45.0:
        return Signal(
            "BUY",
            symbol,
            price,
            rr,
            70,
            ["1h trend OK", "15m EMA50>EMA200", "RSI pullback recovery"],
            None,
            "A_TREND_PULLBACK",
        )

    return Signal("NONE", symbol, price, rr, 0, ["No pullback trigger"], None, "A_TREND_PULLBACK")
