#!/usr/bin/env python3
"""
Regime Detection v1 (bull / bear / range) — dependency-free (stdlib only)

Why stdlib-only:
- Termux pip builds for numpy/pandas often fail (cmake/patchelf toolchain issues).
- Keeps EZTrader portable and regression-safe.

Inputs:
- candles: iterable of dicts OR tuples:
    dict: {"ts": <unix_seconds or iso str>, "close": float}
    tuple: (ts, close)
  Candles must be sorted ascending by time.

Output:
- regimes: list[str] aligned 1:1 with input candles: "bull"|"bear"|"range"

Logic (Option A+):
- Build 1H closes from base candles (last close of each hour bucket)
- EMA(ema_len) on 1H closes
- EMA slope over slope_len bars (sign only)
- Hysteresis buffer around EMA (buffer_pct)
- Confirm bull/bear with confirm_bars consecutive buckets
- Forward-fill regime back to base candles
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Literal, Optional, Sequence, Tuple, Union

Regime = Literal["bull", "bear", "range"]


@dataclass(frozen=True)
class RegimeConfig:
    enabled: bool = False
    timeframe: str = "1H"          # currently supports "1H" only in stdlib mode
    ema_len: int = 200
    slope_len: int = 12            # bars on 1H timeframe
    buffer_pct: float = 0.006      # 0.6% hysteresis buffer
    confirm_bars: int = 2          # require N consecutive bars to confirm

    bull_mult: float = 1.00
    range_mult: float = 0.50
    bear_mult: float = 0.00

    range_rsi_buy_offset: float = 4.0  # stricter buys in range


Candle = Union[dict, Tuple[object, float]]


def _to_unix_seconds(ts: object) -> int:
    if ts is None:
        raise ValueError("timestamp is None")
    if isinstance(ts, (int, float)):
        return int(ts)
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return int(ts.timestamp())
    if isinstance(ts, str):
        # Accept ISO-ish strings: "2026-01-01T00:00:00Z" or "2026-01-01 00:00:00"
        s = ts.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            # last resort: common format
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    raise TypeError(f"Unsupported timestamp type: {type(ts)}")


def _extract_ts_close(c: Candle) -> Tuple[int, float]:
    if isinstance(c, dict):
        ts = _to_unix_seconds(c.get("ts"))
        close = float(c.get("close"))
        return ts, close
    # tuple-like
    ts, close = c
    return _to_unix_seconds(ts), float(close)


def _hour_bucket(ts_sec: int) -> int:
    # bucket key = unix seconds floored to the hour
    return ts_sec - (ts_sec % 3600)


def _ema(values: Sequence[float], length: int) -> List[float]:
    n = max(1, int(length))
    alpha = 2.0 / (n + 1.0)
    out: List[float] = []
    ema: Optional[float] = None
    for v in values:
        if ema is None:
            ema = v
        else:
            ema = (alpha * v) + ((1.0 - alpha) * ema)
        out.append(ema)
    return out


def _diff_n(values: Sequence[float], n: int) -> List[Optional[float]]:
    k = max(1, int(n))
    out: List[Optional[float]] = [None] * len(values)
    for i in range(k, len(values)):
        out[i] = values[i] - values[i - k]
    return out


def _confirm(mask: Sequence[bool], confirm_bars: int) -> List[bool]:
    k = max(1, int(confirm_bars))
    if k == 1:
        return list(mask)
    out = [False] * len(mask)
    run = 0
    for i, m in enumerate(mask):
        if m:
            run += 1
        else:
            run = 0
        if run >= k:
            out[i] = True
    return out


def build_regime_series(candles: Iterable[Candle], cfg: RegimeConfig) -> List[str]:
    items = [_extract_ts_close(c) for c in candles]
    if not items:
        return []

    # If disabled, default to "bull" to keep callers simple (and avoid reducing trades).
    if not cfg.enabled:
        return ["bull"] * len(items)

    if str(cfg.timeframe).upper() != "1H":
        raise ValueError("Stdlib regime engine currently supports timeframe='1H' only")

    # Build 1H close series: last close per hour bucket
    hour_keys: List[int] = []
    hour_closes: List[float] = []
    last_key: Optional[int] = None
    for ts, close in items:
        k = _hour_bucket(ts)
        if last_key is None:
            last_key = k
            hour_keys.append(k)
            hour_closes.append(close)
        elif k == last_key:
            hour_closes[-1] = close  # update last close in same hour
        else:
            last_key = k
            hour_keys.append(k)
            hour_closes.append(close)

    if not hour_closes:
        return ["range"] * len(items)

    ema = _ema(hour_closes, cfg.ema_len)
    slope = _diff_n(ema, cfg.slope_len)

    buffer = float(cfg.buffer_pct)

    bull_raw: List[bool] = []
    bear_raw: List[bool] = []
    for close, e, s in zip(hour_closes, ema, slope):
        if s is None:
            bull_raw.append(False)
            bear_raw.append(False)
            continue
        upper = e * (1.0 + buffer)
        lower = e * (1.0 - buffer)
        bull_raw.append((close > upper) and (s > 0))
        bear_raw.append((close < lower) and (s < 0))

    bull = _confirm(bull_raw, cfg.confirm_bars)
    bear = _confirm(bear_raw, cfg.confirm_bars)

    # regime per hour
    regime_hour: List[str] = ["range"] * len(hour_keys)
    for i in range(len(hour_keys)):
        if bull[i]:
            regime_hour[i] = "bull"
        if bear[i]:
            regime_hour[i] = "bear"

    # map hour bucket -> regime
    hour_reg_map = {k: r for k, r in zip(hour_keys, regime_hour)}

    # forward-fill to base candles
    regimes: List[str] = []
    cur: str = "range"
    for ts, _close in items:
        k = _hour_bucket(ts)
        if k in hour_reg_map:
            cur = hour_reg_map[k]
        regimes.append(cur)

    return regimes


def regime_multiplier(regime: str, cfg: RegimeConfig) -> float:
    r = (regime or "range").lower()
    if r == "bull":
        return float(cfg.bull_mult)
    if r == "bear":
        return float(cfg.bear_mult)
    return float(cfg.range_mult)


def range_rsi_buy_threshold(base_rsi_buy: float, cfg: RegimeConfig) -> float:
    return float(base_rsi_buy) - float(cfg.range_rsi_buy_offset)


if __name__ == "__main__":
    # quick stdlib self-test
    # 5m candles for 1 day: uptrend
    start = int(datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp())
    candles = []
    price = 100.0
    for i in range(12 * 24):  # 288 candles
        ts = start + (i * 300)
        price += 0.03
        candles.append({"ts": ts, "close": price})

    cfg = RegimeConfig(enabled=True, timeframe="1H", ema_len=20, slope_len=3, buffer_pct=0.001, confirm_bars=2)
    regs = build_regime_series(candles, cfg)
    # show last 10 regimes
    print("last10:", regs[-10:])
