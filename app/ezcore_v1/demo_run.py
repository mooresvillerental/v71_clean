from __future__ import annotations
import random, time

from .core.config import CoreConfig
from .core.engine import CoreV1


def _gen(n: int, start: float, drift: float, vol: float):
    x = start
    closes, highs, lows, vols = [], [], [], []
    for _ in range(n):
        x = max(1.0, x * (1.0 + drift + random.uniform(-vol, vol)))
        c = x
        h = c * (1.0 + random.uniform(0.0, 0.003))
        l = c * (1.0 - random.uniform(0.0, 0.003))
        v = 100 + random.uniform(-20, 50)
        closes.append(c); highs.append(h); lows.append(l); vols.append(v)
    return closes, highs, lows, vols


def main():
    print("ezcore_v1 demo starting...")

    cfg = CoreConfig(enable_tts=False)  # disable TTS for demo stability
    bot = CoreV1(cfg)
    # demo-only: allow Strategy B through (so analytics can see B rows)
    bot.EZ_B_MIN_CONF = 0
    bot.EZ_B_TIE_ADVANTAGE = 0

    s = cfg.primary_symbol

    closes15, highs15, lows15, vols15 = _gen(300, 40000.0, 0.0002, 0.002)

    # --- inject stronger synthetic breakout spikes so Strategy B can fire ---
    for k in range(235, 300, 12):
        try:
            closes15[k] = closes15[k] * 1.05   # bigger jump
            highs15[k]  = max(highs15[k], closes15[k] * 1.01)
            vols15[k]   = vols15[k] * 12.0     # bigger volume spike
        except Exception:
            pass


    # --- inject a few synthetic breakout spikes so Strategy B can fire in demo ---
    for k in range(235, 300, 15):
        try:
            closes15[k] = closes15[k] * 1.012  # small jump
            highs15[k]  = max(highs15[k], closes15[k] * 1.003)
            vols15[k]   = vols15[k] * 4.0      # volume spike
        except Exception:
            pass

    closes1h, _, _, _ = _gen(300, 40000.0, -0.00025, 0.0015)

    bars_15m = {s: closes15}
    highs_15m = {s: highs15}
    lows_15m  = {s: lows15}
    vols_15m  = {s: vols15}
    bars_1h   = {s: closes1h}

    for i in range(220, 300):
        if i % 10 == 0:
            print(f"tick {i}/299")
        bars_15m[s] = closes15[: i + 1]
        highs_15m[s]= highs15[: i + 1]
        lows_15m[s] = lows15[: i + 1]
        vols_15m[s] = vols15[: i + 1]
        bars_1h[s]  = closes1h[: i + 1]
        bot.tick_paper(bars_15m, bars_1h, highs_15m, lows_15m, vols_15m)
        time.sleep(0.02)

    print("demo complete")

    # --- DECISION SUMMARY (toggle via EZ_DECISION_SUMMARY knob) ---

    try:

        from app.ezcore_v1.core.knobs import load_knobs

        k = load_knobs()

        if bool(k.get('EZ_DECISION_SUMMARY', False)):

            import json, os

            sp = 'app/ezcore_v1_state.json'

            if os.path.exists(sp):

                st = json.load(open(sp, 'r', encoding='utf-8'))

                rows = st.get('seen_signals_log') or []

                total = len(rows)

                buys  = sum(1 for r in rows if r.get('action') == 'BUY')

                sells = sum(1 for r in rows if r.get('action') == 'SELL')

                none  = sum(1 for r in rows if r.get('action') == 'NONE')

                rsi_gated = sum(1 for r in rows if any('BUY gated: RSI too high' in str(x) for x in (r.get('reasons') or [])))

                conf_wait = sum(1 for r in rows if any('BUY pending confirm' in str(x) for x in (r.get('reasons') or [])))

                no_sig = sum(1 for r in rows if any('No signal (A&B NONE)' in str(x) for x in (r.get('reasons') or [])))

                print('\n=== DECISION SUMMARY ===')
                diag = (st.get('diag') or {})
                print('BUY attempts (B breakout):', int(diag.get('buy_attempts_B', 0) or 0))

                print('rows:', total)

                print('BUY:', buys, 'SELL:', sells, 'NONE:', none)

                print('BUY gated (RSI):', rsi_gated)

                print('BUY pending confirm:', conf_wait)

                print('No signal (A&B NONE):', no_sig)

    except Exception:

        pass

    print(f"state:  {cfg.state_path}")
    print(f"log:    {cfg.log_path}")
    print(f"events: {cfg.events_path}")


if __name__ == "__main__":
    main()
