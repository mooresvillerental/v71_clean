import json
from pathlib import Path
from datetime import datetime

SIGNAL_FILE = Path("signals/latest_signal.json")
ANALYTICS_FILE = Path("logs/ezcore_v1_signal_analytics.json")
OUT_DIR = Path("marketing_posts")

OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def compute_learning_stats(data: dict):
    stats = {
        "signals_observed": 0,
        "winning_signals": 0,
        "strategies_learned": 0,
    }

    if isinstance(data, dict):
        stats["strategies_learned"] = len(data)
        for strat in data.values():
            if isinstance(strat, dict):
                for action in strat.values():
                    if isinstance(action, dict):
                        for tf in action.values():
                            if isinstance(tf, dict):
                                stats["signals_observed"] += int(tf.get("n", 0) or 0)
                                stats["winning_signals"] += int(tf.get("wins", 0) or 0)
    return stats

def build_report():
    signal = load_json(SIGNAL_FILE, {})
    analytics = load_json(ANALYTICS_FILE, {})
    stats = compute_learning_stats(analytics)

    symbol = signal.get("symbol", "--")
    action = signal.get("final_action") or signal.get("action") or "--"
    strategy = signal.get("strategy", "--")
    regime = signal.get("regime", "--")
    trend = signal.get("trend", "--")
    confidence = signal.get("confidence", "--")

    return (
        "EZTrader Daily Engine Report\n\n"
        f"Symbol: {symbol}\n"
        f"Signals observed: {stats['signals_observed']}\n"
        f"Winning signals: {stats['winning_signals']}\n"
        f"Strategies learned: {stats['strategies_learned']}\n"
        f"Latest action: {action}\n"
        f"Latest strategy: {strategy}\n"
        f"Current regime: {regime}\n"
        f"Current trend: {trend}\n"
        f"Current confidence: {confidence}%\n"
    )

def main():
    now = datetime.now()
    filename = OUT_DIR / f"daily_summary_{now.strftime('%Y%m%d')}.txt"
    filename.write_text(build_report(), encoding="utf-8")
    print(f"[EZMarketing] Created {filename}")

if __name__ == "__main__":
    main()
