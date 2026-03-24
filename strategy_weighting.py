import json
from pathlib import Path

ANALYTICS_PATH = Path("logs/ezcore_v1_signal_analytics.json")

def _safe_num(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def _load_analytics():
    try:
        if not ANALYTICS_PATH.exists():
            return {}
        return json.loads(ANALYTICS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _aggregate_strategy_score(strategy: str):
    data = _load_analytics()
    strat = str(strategy or "").upper().strip()
    if not strat:
        return None

    bucket = data.get(strat)
    if not isinstance(bucket, dict):
        return None

    weighted_sum = 0.0
    weighted_n = 0.0
    total_samples = 0

    for side_payload in bucket.values():
        if not isinstance(side_payload, dict):
            continue
        for tf_payload in side_payload.values():
            if not isinstance(tf_payload, dict):
                continue
            n = int(_safe_num(tf_payload.get("n", 0), 0))
            win_pct = _safe_num(tf_payload.get("win_pct", 0), 0.0)
            if n <= 0:
                continue
            weighted_sum += win_pct * n
            weighted_n += n
            total_samples += n

    if weighted_n <= 0:
        return None

    avg_win_pct = weighted_sum / weighted_n
    return {
        "avg_win_pct": avg_win_pct,
        "samples": total_samples,
    }

def adjust_confidence(strategy, confidence):
    """
    Soft adaptive weighting from real analytics.
    - No hard block
    - Small boosts/penalties only
    """
    base = _safe_num(confidence, 0.0)
    strat = str(strategy or "").upper().strip()

    # Default soft penalty for unclassified / no-signal style labels
    if strat in {"", "NONE", "UNKNOWN", "NO_SIGNAL"}:
        return max(0, min(100, round(base - 8, 2)))

    info = _aggregate_strategy_score(strat)
    if not info:
        return max(0, min(100, round(base, 2)))

    win_pct = info["avg_win_pct"]
    samples = info["samples"]

    # Sample confidence factor:
    # 0 when tiny sample, approaches 1 as samples grow
    sample_factor = min(1.0, samples / 30.0)

    # Center around 50% win rate
    edge = win_pct - 50.0

    # Soft adjustment only
    adjustment = edge * 0.20 * sample_factor

    weighted = base + adjustment
    weighted = max(0, min(100, round(weighted, 2)))
    return weighted
