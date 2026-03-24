import json
import time
from dataclasses import replace
from pathlib import Path
from strategy_weighting import compute_strategy_delta

CONFIDENCE_REFRESH_SECONDS = 10

from app.ezcore_v1.core.config import CoreConfig
from app.ezcore_v1.core.engine import CoreV1

PRICE_FILE = Path("signals/latest_price.json")
SIGNAL_FILE = Path("signals/latest_signal.json")
SIGNAL_HISTORY_LOG = Path("signals/signal_history.jsonl")
HISTORY_FILE = Path("signals/history_seed.json")
OHLC_FILE = Path("signals/ohlc_live.json")

cfg = CoreConfig()
engine = CoreV1(cfg)

closes_1m = []
closes_15m = []
closes_1h = []

last_signal_key = None

last_trade_time = None
last_trade_price = None
last_trade_action = None

last_minute_bucket = None
last_15m_bucket = None
last_1h_bucket = None

if HISTORY_FILE.exists():
    seed = json.loads(HISTORY_FILE.read_text())
    closes_15m = seed.get("closes_15m", [])
    closes_1h = seed.get("closes_1h", [])
    print("Loaded history seed:")
    print("15m candles:", len(closes_15m))
    print("1h candles:", len(closes_1h))
else:
    print("No history seed found.")

def load_price():
    # Prefer latest_price.json if it is fresh; otherwise fall back to latest OHLC close.
    try:
        if PRICE_FILE.exists():
            age_sec = time.time() - PRICE_FILE.stat().st_mtime
            if age_sec <= 120:
                data = json.loads(PRICE_FILE.read_text())
                return float(data["price"])
    except Exception:
        pass

    try:
        if OHLC_FILE.exists():
            data = json.loads(OHLC_FILE.read_text())
            closes = data.get("closes", [])
            if closes:
                return float(closes[-1])
    except Exception:
        pass

    return None

def load_ohlc():
    if not OHLC_FILE.exists():
        return None
    try:
        data = json.loads(OHLC_FILE.read_text())
        return {
            "highs": [float(x) for x in data.get("highs", [])],
            "lows": [float(x) for x in data.get("lows", [])],
            "closes": [float(x) for x in data.get("closes", [])],
            "volumes": [float(x) for x in data.get("volumes", [])],
        }
    except Exception:
        return None

def write_signal(sig):
    SIGNAL_FILE.write_text(json.dumps(sig, indent=2) + "\n", encoding="utf-8")

def append_signal_history(sig):
    history_row = {
        "timestamp": sig.get("timestamp"),
        "symbol": sig.get("symbol"),
        "action": sig.get("action"),
        "final_action": sig.get("final_action"),
        "strategy": sig.get("strategy"),
        "winning_strategy": sig.get("winning_strategy"),
        "strategy_a_action": sig.get("strategy_a_action"),
        "strategy_b_action": sig.get("strategy_b_action"),
        "preferred_strategy": sig.get("preferred_strategy"),
        "conflict": sig.get("conflict"),
        "conflict_reason": sig.get("conflict_reason"),
        "confidence": sig.get("confidence"),
        "price": sig.get("price"),
        "rsi": sig.get("rsi"),
        "trend": sig.get("trend"),
        "regime": sig.get("regime"),
        "quality_blocked": sig.get("quality_blocked"),
        "quality_reason": sig.get("quality_reason"),
        "trade_eligible": sig.get("trade_eligible"),
        "eligibility_reason": sig.get("eligibility_reason"),
        "seconds_since_last_trade": sig.get("seconds_since_last_trade"),
        "price_move_since_last_trade_pct": sig.get("price_move_since_last_trade_pct"),
        "suggested_trade_usd": sig.get("suggested_trade_usd"),
    }
    SIGNAL_HISTORY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SIGNAL_HISTORY_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(history_row, separators=(",", ":")) + "\n")

def conf_to_trade_size(conf, action):
    if action == "NONE":
        return 0
    if conf >= 80:
        return 600
    if conf >= 70:
        return 400
    if conf >= 60:
        return 250
    if conf >= 50:
        return 150
    return 75

def evaluate_trade_guard(action, confidence, price):
    global last_trade_time, last_trade_price, last_trade_action

    now = int(time.time())

    if action == "NONE":
        return True, "no_trade_signal", None, None

    if last_trade_time is None or last_trade_price is None or last_trade_action is None:
        return True, "no_previous_trade_signal", None, None

    seconds_since = now - last_trade_time
    price_move_pct = ((price - last_trade_price) / last_trade_price) * 100.0 if last_trade_price else 0.0

    eligible = True
    reason = "normal"

    if action != last_trade_action:
        if seconds_since < 120 and confidence < 70:
            eligible = False
            reason = "rapid_flip"

    if action == last_trade_action:
        if seconds_since < 90 and confidence < 65:
            eligible = False
            reason = "weak_repeat"

    if confidence >= 80:
        eligible = True
        reason = "strong_signal_override"

    return eligible, reason, seconds_since, price_move_pct

def resolve_signals(sig_a, sig_b, conf_a, conf_b):
    a_action = getattr(sig_a, "action", "NONE")
    b_action = getattr(sig_b, "action", "NONE") if sig_b is not None else "NONE"

    a_strategy = getattr(sig_a, "strategy", "A_TREND_PULLBACK")
    b_strategy = getattr(sig_b, "strategy", "B_VOL_BREAKOUT") if sig_b is not None else "B_VOL_BREAKOUT"

    a_rsi = getattr(sig_a, "rsi", 0.0)
    b_rsi = getattr(sig_b, "rsi", a_rsi) if sig_b is not None else a_rsi

    base = {
        "strategy_a_action": a_action,
        "strategy_b_action": b_action,
        "conflict": False,
        "conflict_reason": "",
        "resolver_mode": "AGREE_OR_BLOCK",
        "winning_strategy": "",
    }

    if a_action == "NONE" and b_action == "NONE":
        return {
            **base,
            "action": "NONE",
            "final_action": "NONE",
            "strategy": "NO_SIGNAL",
            "winning_strategy": "",
            "confidence": max(conf_a, conf_b),
            "rsi": a_rsi,
        }

    if a_action != "NONE" and b_action == "NONE":
        return {
            **base,
            "action": a_action,
            "final_action": a_action,
            "strategy": "A_ONLY",
            "winning_strategy": a_strategy,
            "confidence": conf_a,
            "rsi": a_rsi,
        }

    if b_action != "NONE" and a_action == "NONE":
        return {
            **base,
            "action": b_action,
            "final_action": b_action,
            "strategy": "B_ONLY",
            "winning_strategy": b_strategy,
            "confidence": conf_b,
            "rsi": b_rsi,
        }

    if a_action == b_action:
        winner_name = a_strategy if a_strategy == b_strategy else f"{a_strategy}+{b_strategy}"
        selected_rsi = a_rsi if conf_a >= conf_b else b_rsi
        return {
            **base,
            "action": a_action,
            "final_action": a_action,
            "strategy": "A_B_CONFIRMED",
            "winning_strategy": winner_name,
            "confidence": min(max(conf_a, conf_b) + 10, 95),
            "rsi": selected_rsi,
        }

    return {
        **base,
        "action": "NONE",
        "final_action": "NONE",
        "strategy": "A_B_CONFLICT",
        "winning_strategy": "",
        "confidence": min(conf_a, conf_b, 25),
        "rsi": a_rsi,
        "conflict": True,
        "conflict_reason": f"A={a_action}, B={b_action}",
    }

print("EZTRADER Candle Engine running...")

while True:
    price = load_price()
    ohlc = load_ohlc()

    if ohlc and ohlc.get("closes"):
        try:
            price = float(ohlc["closes"][-1])
        except Exception:
            pass

    if price is None:
        time.sleep(2)
        continue

    now_ts = int(time.time())
    minute_bucket = now_ts // 60
    bucket_15m = now_ts // (15 * 60)
    bucket_1h = now_ts // (60 * 60)

    if last_minute_bucket != minute_bucket:
        closes_1m.append(price)
        last_minute_bucket = minute_bucket
        if len(closes_1m) > 1000:
            closes_1m.pop(0)

    if last_15m_bucket != bucket_15m:
        closes_15m.append(price)
        last_15m_bucket = bucket_15m
        if len(closes_15m) > 400:
            closes_15m.pop(0)

    if last_1h_bucket != bucket_1h:
        closes_1h.append(price)
        last_1h_bucket = bucket_1h
        if len(closes_1h) > 400:
            closes_1h.pop(0)

    symbol = "BTC-USD"

    a_15 = closes_15m[-220:]
    a_1h = closes_1h[-220:]

    sig_a = engine.strat_a.generate(symbol, a_15, a_1h, price)
    conf_a = engine._simple_confidence_score(sig_a)

    sig_b = None
    conf_b = 0

    if ohlc:
        highs = ohlc["highs"][-220:]
        lows = ohlc["lows"][-220:]
        closes = ohlc["closes"][-220:]
        volumes = ohlc["volumes"][-220:]

        if len(highs) >= 70 and len(lows) >= 70 and len(closes) >= 70 and len(volumes) >= 70:
            
            sig_b = engine.strat_b.generate(symbol, highs, lows, closes, volumes, price)

            # Breakout distance filter
            recent_high = max(highs[-20:])
            recent_low = min(lows[-20:])
            range_size = recent_high - recent_low

            breakout_distance_pct = 0
            if range_size > 0:
                breakout_distance_pct = abs(price - closes[-2]) / closes[-2] * 100

            if breakout_distance_pct < 0.15:
                sig_b = replace(sig_b, action="NONE")

            conf_b = engine._simple_confidence_score(sig_b)

    
    resolved = resolve_signals(sig_a, sig_b, conf_a, conf_b)

    raw_action = resolved["action"]
    strategy = resolved["strategy"]
    conf = resolved["confidence"]

    # --- Strategy performance weighting ---
    try:
        delta = compute_strategy_delta(strategy)
        conf = max(0, min(100, conf + delta))
    except:
        pass

    quality_blocked = False
    quality_reason = ""

    if raw_action != "NONE" and conf < 40:
        quality_blocked = True
        quality_reason = "confidence_below_threshold"

    action = "NONE" if quality_blocked else raw_action
    final_action = "NONE" if quality_blocked else resolved["final_action"]

    if action == "BUY":
        trend = "Bullish"
    elif action == "SELL":
        trend = "Bearish"
    else:
        trend = "Neutral"
    # --- Regime Observation ---
    regime = "UNKNOWN"
    try:
        if len(closes_1m) >= 60:
            sma20 = sum(closes_1m[-20:]) / 20
            sma50 = sum(closes_1m[-50:]) / 50
            trend_strength = abs(sma20 - sma50) / price

            if trend_strength > 0.002:
                regime = "TREND"
            else:
                regime = "RANGE"
    except:
        regime = "UNKNOWN"

    # --- Regime strategy observer (no trading impact) ---
    preferred_strategy = "NONE"
    if regime == "TREND":
        preferred_strategy = "A_TREND_PULLBACK"
    elif regime == "RANGE":
        preferred_strategy = "B_VOL_BREAKOUT"


    # --- Dynamic confidence adjustment ---
    try:
        if raw_action in ("BUY", "SELL") and len(closes_1m) >= 10:
            recent_ref = closes_1m[-10]
            move_pct_10s = ((price - recent_ref) / recent_ref) * 100 if recent_ref else 0.0

            confidence_delta = 0
            if raw_action == "BUY":
                if move_pct_10s >= 0.20:
                    confidence_delta += 10
                elif move_pct_10s >= 0.10:
                    confidence_delta += 5
                elif move_pct_10s <= -0.20:
                    confidence_delta -= 15
                elif move_pct_10s <= -0.10:
                    confidence_delta -= 8
            elif raw_action == "SELL":
                if move_pct_10s <= -0.20:
                    confidence_delta += 10
                elif move_pct_10s <= -0.10:
                    confidence_delta += 5
                elif move_pct_10s >= 0.20:
                    confidence_delta -= 15
                elif move_pct_10s >= 0.10:
                    confidence_delta -= 8

            winning_strategy = resolved.get("winning_strategy") or ""
            if regime == "RANGE" and ("A_TREND_PULLBACK" in winning_strategy or strategy == "A_ONLY"):
                confidence_delta -= 10
            if regime == "TREND" and ("B_VOL_BREAKOUT" in winning_strategy or strategy == "B_ONLY"):
                confidence_delta -= 5

            conf = max(0, min(100, conf + confidence_delta))
    except:
          pass

    trade_eligible, eligibility_reason, seconds_since, price_move = evaluate_trade_guard(
        action,
        conf,
        price,
    )

    trade_size = conf_to_trade_size(conf, action)

    signal = {
        "symbol": symbol,
        "action": action,
        "final_action": final_action,
        "price": price,
        "rsi": resolved["rsi"],
        "confidence": conf,
        "strategy": strategy,
        "winning_strategy": resolved["winning_strategy"],
        "strategy_a_action": resolved["strategy_a_action"],
        "strategy_b_action": resolved["strategy_b_action"],
        "preferred_strategy": preferred_strategy,
        "conflict": resolved["conflict"],
        "conflict_reason": resolved["conflict_reason"],
        "resolver_mode": resolved["resolver_mode"],
        "risk_level": "Medium",
        "trend": trend,
            "regime": regime,
        "quality_blocked": quality_blocked,
        "quality_reason": quality_reason,
        "trade_eligible": trade_eligible,
        "eligibility_reason": eligibility_reason,
        "seconds_since_last_trade": seconds_since,
        "price_move_since_last_trade_pct": price_move,
        "suggested_trade_usd": trade_size,
        "timestamp": int(time.time()),
    }

    signal_key = (
        signal["action"],
        signal["strategy"],
        signal["winning_strategy"],
        signal["strategy_a_action"],
        signal["strategy_b_action"],
        signal["preferred_strategy"],
        signal["conflict"],
        signal["conflict_reason"],
        signal["regime"],
        signal["quality_blocked"],
        signal["quality_reason"],
        signal["trade_eligible"],
        signal["eligibility_reason"],
    )

    write_signal(signal)

    if signal_key != last_signal_key:
        append_signal_history(signal)
        try:
            import subprocess
            subprocess.run(
                ["python", "shadow_trade_logger.py"],
                cwd="/data/data/com.termux/files/home/v71_clean",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass
        print("New Signal:", signal)
        last_signal_key = signal_key

        if action != "NONE":
            last_trade_time = signal["timestamp"]
            last_trade_price = price
            last_trade_action = action

    time.sleep(2)
