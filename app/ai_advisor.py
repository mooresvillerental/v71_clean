"""
EZTrader AI Advisor (Phase 1)

Goal:
- Keep the deterministic/base signal logic as the source of truth.
- Provide an optional "AI-adjusted confidence" and a short explanation.
- No network calls. No LLM dependency. Safe + testable.

Later:
- Swap internals to a trained model or LLM, but keep the same function signature.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Tuple


def _clamp(x: float, lo: float, hi: float) -> float:
    try:
        x = float(x)
    except Exception:
        return lo
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


@dataclass
class AIAdvice:
    ai_confidence: int          # 0..100
    delta: int                  # ai - base
    explanation: str            # short and speak-friendly


def ai_adjust_confidence(
    *,
    symbol: str,
    action: str,
    base_confidence: int,
    features: Dict[str, Any] | None = None,
) -> AIAdvice:
    """
    Inputs:
      - symbol/action/base_confidence from your existing deterministic engine
      - features: optional computed stats (trend/volatility/peak watchers later)

    Output:
      - AI-adjusted confidence (0..100), delta, explanation

    IMPORTANT:
      - This should NEVER bypass hard risk rules (cash-only, min trade, etc.).
      - This should be "advisory overlay" only.
    """
    action = (action or "HOLD").upper().strip()
    base = int(_clamp(base_confidence, 0, 100))
    f = features or {}

    # Phase 1 heuristic overlay (safe, small influence):
    # - Adds/ subtracts up to ~15 points based on simple stability cues.
    # - Later we replace this with a real model (same interface).
    delta = 0

    # If we don't have features yet, keep it minimal and honest.
    if not f:
        return AIAdvice(
            ai_confidence=base,
            delta=0,
            explanation="AI overlay inactive (no features yet).",
        )

    # Optional feature keys (we'll wire these in later):
    # trend_slope_pct: e.g., percent change over last N candles
    # vol_pct:         e.g., ATR% or simple range%
    # peak_risk:       0..100 higher = more likely near exhaustion
    trend = float(f.get("trend_slope_pct", 0.0) or 0.0)
    vol = float(f.get("vol_pct", 0.0) or 0.0)
    peak_risk = float(f.get("peak_risk", 0.0) or 0.0)

    # Trend alignment helps confidence a little
    if action == "BUY" and trend < 0:
        delta += 6
    if action == "SELL" and trend > 0:
        delta += 6

    # High volatility increases uncertainty
    if vol >= 2.5:
        delta -= 8
    elif vol >= 1.5:
        delta -= 4

    # Peak risk reduces SELL confidence if we’re not convincingly “topping”
    # (we’ll make this smarter when peak watchers are wired in)
    if action == "SELL" and peak_risk < 50:
        delta -= 5

    # HOLD should stay quiet/low influence
    if action == "HOLD":
        delta = 0

    # Clamp influence so AI can’t hijack the system
    delta = int(_clamp(delta, -15, 15))
    ai = int(_clamp(base + delta, 0, 100))

    # Explanation (short; we’ll improve as features expand)
    bits = []
    if action != "HOLD":
        bits.append(f"Base {base}.")
        if delta > 0:
            bits.append(f"AI +{delta}.")
        elif delta < 0:
            bits.append(f"AI {delta}.")
        else:
            bits.append("AI 0.")
        if vol >= 1.5:
            bits.append("High volatility.")
        if action == "BUY" and trend < 0:
            bits.append("Downtrend exhaustion possible.")
        if action == "SELL" and trend > 0:
            bits.append("Uptrend strength present.")
    else:
        bits.append("Hold. AI not applied.")

    return AIAdvice(ai_confidence=ai, delta=delta, explanation=" ".join(bits).strip())


if __name__ == "__main__":
    # tiny self-test
    a = ai_adjust_confidence(symbol="BTC-USD", action="BUY", base_confidence=72, features={"trend_slope_pct": -0.8, "vol_pct": 1.2})
    print(a)
