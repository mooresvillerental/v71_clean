from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Signal:
    action: str            # BUY / SELL / NONE
    symbol: str
    price: float
    rsi: Optional[float]
    confidence: int        # 0-100
    reasons: list[str]
    invalidation: Optional[float]
    strategy: Optional[str]
