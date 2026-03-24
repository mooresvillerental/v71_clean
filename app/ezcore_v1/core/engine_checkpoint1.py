from __future__ import annotations
import time, uuid
from typing import Any, Dict, List

from ..data.models import Signal
from .alerts import Alerts
from .config import CoreConfig
from .execution import ExecutionLayer
from .logger import EventLogger
from .risk import RiskManager
from .state import StateStore


def _event_id() -> str:
    return uuid.uuid4().hex[:12]


def _fmt(x: float, nd: int = 2) -> str:
    try:
        return f"{x:.{nd}f}"
    except Exception:
        return str(x)




def _calc_atr(highs, lows, closes, period=14):
    if len(closes) < period+1:
        return None
    trs=[]
    for i in range(1,len(closes)):
        tr=max(
            highs[i]-lows[i],
            abs(highs[i]-closes[i-1]),
            abs(lows[i]-closes[i-1])
        )
        trs.append(tr)
    return sum(trs[-period:])/period



    def _simple_confidence_score(self, sig):
        try:
            score = 0
            rsi = getattr(sig, "rsi", None)
            strat = str(getattr(sig, "strategy", "")).upper()

            if "TREND" in strat:
                score += 30

            if "BREAKOUT" in strat:
                score += 25

            try:
                if rsi is not None:
                    rsi = float(rsi)
                    if 45 <= rsi <= 65:
                        score += 25
                    elif 65 < rsi <= 75:
                        score += 10
            except:
                pass

            if score > 100:
                score = 100

            return score

        except:
            return 0



class CoreV1:

    def _simple_confidence_score(self, sig):
        try:
            score = 0
            rsi = getattr(sig, "rsi", None)
            strat = str(getattr(sig, "strategy", "") or "").upper()

            if "TREND" in strat:
                score += 30
            if "BREAKOUT" in strat:
                score += 25

            try:
                if rsi is not None:
                    rsi = float(rsi)
                    if 45.0 <= rsi <= 65.0:
                        score += 25
                    elif 65.0 < rsi <= 75.0:
                        score += 10
            except Exception:
                pass

            if score > 100:
                score = 100
            if score < 0:
                score = 0
            return int(score)
        except Exception:
            return 0



    def _should_announce(self, st: dict, sig: "Signal") -> bool:
        """Transition-only announcements.
        # --- announce de-dupe (prevents repeated BUY/SELL spam) ---
        try:
            sym = getattr(sig, 'symbol', None) or (st.get('primary_symbol') if isinstance(st, dict) else None) or 'UNKNOWN'
            act = str(getattr(sig, 'action', 'NONE') or 'NONE').upper()
            last = (self._last_announced.get(sym) if hasattr(self, '_last_announced') else None)
            if act in ('BUY','SELL') and last == act:
                return False
            # reset latch when signal goes NONE (lets future announces happen)
            if act == 'NONE' and last is not None:
                self._last_announced.pop(sym, None)
        except Exception:
            pass

        Announces only when action changes into BUY/SELL.
        Persists last action in state so restarts don't spam alerts.
        """
        try:
            symbol = getattr(sig, "symbol", None) or self.cfg.primary_symbol
            action = (getattr(sig, "action", None) or "NONE").upper()
            last_map = st.setdefault("_last_action", {})
            last = (last_map.get(symbol) or "NONE").upper()
            # update last seen action every tick
            last_map[symbol] = action
            return action in ("BUY", "SELL") and action != last
        except Exception:
            # fail-safe: don't spam
            return False


    # --- DECISION DIAGNOSTICS (safe logging) ---

    def _diag(self, msg: str) -> None:

        """Best-effort diagnostic logging. Never breaks trading loop."""

        try:

            if not bool(getattr(self, 'EZ_DECISION_LOG', False)):

                return

            # self.log is EventLogger-like (line())

            self.log.line('[DECISION] ' + str(msg))

        except Exception:

            return


    # --- PERF TRACKING (paper trades) ---

    def _perf_open(self, st, symbol, price, rsi, strategy, reasons):

        try:

            perf = st.setdefault('perf', {})

            pos = perf.get('open_pos')

            if pos and pos.get('symbol') == symbol:

                return

            perf['open_pos'] = {

                'symbol': symbol,

                'entry_ts': int(time.time()),

                'entry_price': float(price) if price is not None else None,

                'entry_rsi': float(rsi) if rsi is not None else None,

                'entry_strategy': strategy,

                'entry_reasons': list(reasons or [])[:10],

            }

        except Exception:

            return


    def _perf_close(self, st, symbol, price, rsi, strategy, reasons):

        try:

            perf = st.setdefault('perf', {})

            pos = perf.get('open_pos')

            if not pos or pos.get('symbol') != symbol:

                return

            exit_ts = int(time.time())

            entry_p = float(pos.get('entry_price') or 0.0)

            exit_p  = float(price) if price is not None else 0.0

            pnl_pct = ((exit_p - entry_p) / entry_p * 100.0) if entry_p > 0 else None

            trade = {

                'symbol': symbol,

                'entry_ts': pos.get('entry_ts'),

                'exit_ts': exit_ts,

                'hold_s': int(exit_ts - int(pos.get('entry_ts') or exit_ts)),

                'entry_price': pos.get('entry_price'),

                'exit_price': exit_p,

                'pnl_pct': pnl_pct,

                'entry_rsi': pos.get('entry_rsi'),

                'exit_rsi': float(rsi) if rsi is not None else None,

                'entry_strategy': pos.get('entry_strategy'),

                'exit_strategy': strategy,

                'entry_reasons': pos.get('entry_reasons') or [],

                'exit_reasons': list(reasons or [])[:10],

            }

            perf.setdefault('trades', []).append(trade)

            perf['open_pos'] = None

        except Exception:

            return

    def __init__(self, cfg: CoreConfig):
        self._last_announced = {}
        self.cfg = cfg
        # --- DECISION DIAGNOSTICS (safe logging) ---
        self.EZ_DECISION_LOG = bool(getattr(self, 'EZ_DECISION_LOG', False))

        # --- selector knobs ---
        self.EZ_DISABLE_B = bool(getattr(self, "EZ_DISABLE_B", False))
        self.EZ_B_BENCH_HOURS = int(getattr(self, "EZ_B_BENCH_HOURS", 6))
        self.EZ_B_BENCH_UNTIL_TS = int(getattr(self, "EZ_B_BENCH_UNTIL_TS", 0))

        # --- load persisted adaptive knobs (non-fatal) ---
        try:
            from .knobs import load_knobs
            k = load_knobs()
            # decision diagnostics knobs (safe)
            self.EZ_DECISION_LOG = bool(k.get('EZ_DECISION_LOG', bool(getattr(self,'EZ_DECISION_LOG', False))))
            self.EZ_DECISION_EVERY = int(k.get('EZ_DECISION_EVERY', int(getattr(self,'EZ_DECISION_EVERY', 10))))
            self.EZ_DECISION_MAX_REASONS = int(k.get('EZ_DECISION_MAX_REASONS', int(getattr(self,'EZ_DECISION_MAX_REASONS', 3))))
            # apply decision diagnostics knob
            self.EZ_DECISION_LOG = bool(k.get('EZ_DECISION_LOG', bool(getattr(self,'EZ_DECISION_LOG', False))))

            # apply pre-BUY safety knobs from knobs file
            self.EZ_BUY_RSI_MAX = float(k.get('EZ_BUY_RSI_MAX', float(getattr(self,'EZ_BUY_RSI_MAX',70.0))))
            self.EZ_BUY_CONFIRM_BARS = int(k.get('EZ_BUY_CONFIRM_BARS', int(getattr(self,'EZ_BUY_CONFIRM_BARS',2))))
            self.EZ_PAPER_STOP_LOSS_PCT = float(getattr(self, 'EZ_PAPER_STOP_LOSS_PCT', 1.5))
            self.EZ_MIN_HOLD_BARS = int(getattr(self, 'EZ_MIN_HOLD_BARS', 2))
            self.EZ_USE_TREND_FAIL_EXIT = bool(getattr(self, 'EZ_USE_TREND_FAIL_EXIT', True))
            # apply persisted knobs to instance (with safe defaults)
            self.EZ_B_MIN_CONF = int(k.get('EZ_B_MIN_CONF', int(getattr(self,'EZ_B_MIN_CONF',80))))
            self.EZ_B_TIE_ADVANTAGE = int(k.get('EZ_B_TIE_ADVANTAGE', int(getattr(self,'EZ_B_TIE_ADVANTAGE',25))))
            self.EZ_ADAPTIVE_WEIGHTS = bool(k.get('EZ_ADAPTIVE_WEIGHTS', bool(getattr(self,'EZ_ADAPTIVE_WEIGHTS',True))))
            self.EZ_ADAPT_MIN_N_A_1H = int(k.get('EZ_ADAPT_MIN_N_A_1H', int(getattr(self,'EZ_ADAPT_MIN_N_A_1H',10))))
            self.EZ_ADAPT_MIN_N_B_1H = int(k.get('EZ_ADAPT_MIN_N_B_1H', int(getattr(self,'EZ_ADAPT_MIN_N_B_1H',8))))
            self.EZ_B_BENCH_SEC = int(k.get('EZ_B_BENCH_SEC', int(getattr(self,'EZ_B_BENCH_SEC',3600))))
            self.EZ_DISABLE_B = bool(k.get('EZ_DISABLE_B', bool(getattr(self,'EZ_DISABLE_B',False))))
            self.EZ_B_BENCH_UNTIL_TS = int(k.get('EZ_B_BENCH_UNTIL_TS', int(getattr(self,'EZ_B_BENCH_UNTIL_TS',0))))

            self.EZ_B_MIN_CONF = int(k.get(EZ_B_MIN_CONF, getattr(self, EZ_B_MIN_CONF, 80)))
            self.EZ_B_TIE_ADVANTAGE = int(k.get(EZ_B_TIE_ADVANTAGE, getattr(self, EZ_B_TIE_ADVANTAGE, 25)))
            self.EZ_ADAPTIVE_WEIGHTS = bool(k.get(EZ_ADAPTIVE_WEIGHTS, getattr(self, EZ_ADAPTIVE_WEIGHTS, True)))
            self.EZ_ADAPT_MIN_N_A_1H = int(k.get(EZ_ADAPT_MIN_N_A_1H, getattr(self, EZ_ADAPT_MIN_N_A_1H, 10)))
            self.EZ_ADAPT_MIN_N_B_1H = int(k.get(EZ_ADAPT_MIN_N_B_1H, getattr(self, EZ_ADAPT_MIN_N_B_1H, 8)))
        except Exception:
            pass

        # --- signal weighting knobs (instance defaults) ---
        self.EZ_B_MIN_CONF = int(getattr(self, 'EZ_B_MIN_CONF', 80))
        self.EZ_B_TIE_ADVANTAGE = int(getattr(self, 'EZ_B_TIE_ADVANTAGE', 25))
        self.EZ_ADAPTIVE_WEIGHTS = bool(getattr(self, 'EZ_ADAPTIVE_WEIGHTS', True))
        self.EZ_ADAPT_MIN_N_A_1H = int(getattr(self, 'EZ_ADAPT_MIN_N_A_1H', 10))
        self.EZ_ADAPT_MIN_N_B_1H = int(getattr(self, 'EZ_ADAPT_MIN_N_B_1H', 4))

        self.log = EventLogger(cfg.log_path, cfg.events_path)
        self._maybe_adapt_weights()
        # persist knobs at init end (non-fatal; ensures knobs file exists)
        try:
            from .knobs import save_knobs
            save_knobs({'EZ_B_MIN_CONF': int(getattr(self,'EZ_B_MIN_CONF',80)), 'EZ_B_TIE_ADVANTAGE': int(getattr(self,'EZ_B_TIE_ADVANTAGE',25)), 'EZ_ADAPTIVE_WEIGHTS': bool(getattr(self,'EZ_ADAPTIVE_WEIGHTS',True)), 'EZ_ADAPT_MIN_N_A_1H': int(getattr(self,'EZ_ADAPT_MIN_N_A_1H',10)), 'EZ_ADAPT_MIN_N_B_1H': int(getattr(self,'EZ_ADAPT_MIN_N_B_1H',8)), 'EZ_B_BENCH_SEC': int(getattr(self,'EZ_B_BENCH_SEC',3600)), 'EZ_DISABLE_B': bool(getattr(self,'EZ_DISABLE_B',False)), 'EZ_B_BENCH_UNTIL_TS': int(getattr(self,'EZ_B_BENCH_UNTIL_TS',0))})
        except Exception:
            pass
        self.alerts = Alerts(self.log, enable_tts=cfg.enable_tts,
                             tts_rate=cfg.tts_rate,
                             tts_engine=cfg.tts_engine)
        self.state = StateStore(cfg.state_path, cfg.primary_symbol)
        self.risk = RiskManager(cfg, self.log)
        self.exec = ExecutionLayer(cfg, self.log)

        from ..strategies import strategy_a_trend_pullback as strat_a
        from ..strategies import strategy_b_vol_breakout as strat_b
        self.strat_a = strat_a
        self.strat_b = strat_b

        # Transition tracking (in-memory only)
        self._last_action: Dict[str, str] = {}
        self._last_strategy: Dict[str, str] = {}

    # ----------------------------
    # Alert formatting
    # ----------------------------


    def announce_signal(self, sig: Signal,
                        suggested_trade_usd: float,
                        suggested_qty: float) -> None:

        rsi_txt = "n/a" if sig.rsi is None else _fmt(sig.rsi, 1)
        base = sig.symbol.split("-")[0] if "-" in sig.symbol else sig.symbol

        if sig.action == "BUY":




            msg = (
                f"BUY {sig.symbol} | price ${_fmt(sig.price)} | RSI {rsi_txt} | "
                f"suggest ${_fmt(suggested_trade_usd)} "
                f"(~{_fmt(suggested_qty, 8)} {base})"
            )
        elif sig.action == "SELL":
            msg = (
                f"SELL {sig.symbol} | price ${_fmt(sig.price)} | RSI {rsi_txt} | "
                f"suggest ALL (~{_fmt(suggested_qty, 8)} {base} "
                f"-> est ${_fmt(suggested_trade_usd)})"
            )
        else:
            msg = f"NONE {sig.symbol} | price ${_fmt(sig.price)} | RSI {rsi_txt}"

        
        if bool(getattr(self,'EZ_ANNOUNCE_SIGNALS',True)):
            self.alerts.announce(msg)


    # ----------------------------
    # Transition-only logic
    # ----------------------------





    def _regime_prefers_b(
        self,
        closes1h,
        vols15,
    ) -> bool:
        """Return True when conditions look 'breakout-ish' so Strategy B is allowed to win.

        Heuristic:
        - Volatility spike: recent 1h return stdev > mult * baseline stdev
        - Volume spike: recent 15m avg volume > mult * baseline avg volume
        """
        try:
            vol_mult = float(getattr(self, "EZ_REGIME_VOL_MULT", 1.6))
            lookback = int(getattr(self, "EZ_REGIME_VOL_LOOKBACK", 40))
            min_bars = int(getattr(self, "EZ_REGIME_VOL_MIN_BARS", 60))

            if not isinstance(closes1h, list) or not isinstance(vols15, list):
                return False
            if len(closes1h) < max(min_bars, lookback + 5) or len(vols15) < max(min_bars, lookback + 5):
                return False

            # --- volatility spike (1h returns stdev) ---
            rets = []
            for i in range(-lookback-1, -1):
                a = float(closes1h[i])
                b = float(closes1h[i+1])
                if a > 0:
                    rets.append((b / a) - 1.0)
            if len(rets) < 10:
                return False

            # baseline returns stdev from an earlier window
            rets_base = []
            for i in range(-2*lookback-1, -lookback-1):
                if abs(i) <= len(closes1h) - 2:
                    a = float(closes1h[i])
                    b = float(closes1h[i+1])
                    if a > 0:
                        rets_base.append((b / a) - 1.0)
            if len(rets_base) < 10:
                return False

            def stdev(x):
                m = sum(x)/len(x)
                v = sum((t-m)*(t-m) for t in x)/max(1, (len(x)-1))
                return v**0.5

            s_now = stdev(rets)
            s_base = stdev(rets_base)
            if s_base <= 0:
                return False
            vol_spike = (s_now >= vol_mult * s_base)

            # --- volume spike (15m vols avg) ---
            v_now = sum(float(v) for v in vols15[-lookback:]) / float(lookback)
            v_base = sum(float(v) for v in vols15[-2*lookback:-lookback]) / float(lookback)
            if v_base <= 0:
                return False
            volu_spike = (v_now >= vol_mult * v_base)

            return bool(vol_spike and volu_spike)
        except Exception:
            return False

    def _maybe_adapt_weights(self) -> None:
        """Optionally adapt weighting knobs from latest analytics JSON.

        Supports analytics output in either format:
          A) {"rows":[{strategy,side,horizon,n,win_pct,avg,...}, ...]}
          B) {"A_TREND_PULLBACK": {"BUY": {"1h": {...}}}, "B_VOL_BREAKOUT": {...}}
        """
        if not bool(getattr(self, "EZ_ADAPTIVE_WEIGHTS", False)):
            return
        try:
            import json, os, time as _time
            path = "logs/ezcore_v1_signal_analytics.json"
            if not os.path.exists(path):
                return
            data = json.load(open(path, "r", encoding="utf-8"))

            def get_row(strategy: str, side: str, horizon: str):
                rows = data.get("rows")
                if isinstance(rows, list):
                    for r in rows:
                        if r.get("strategy") == strategy and r.get("side") == side and r.get("horizon") == horizon:
                            return r
                    return None
                # strategy-map style
                m = data.get(strategy) or {}
                s = m.get(side) or {}
                h = s.get(horizon) or None
                if not isinstance(h, dict):
                    return None
                # normalize keys to the row-like shape
                return {
                    "strategy": strategy,
                    "side": side,
                    "horizon": horizon,
                    "n": h.get("n", 0),
                    "win_pct": h.get("win_pct", 0.0),
                    # some files call it avg_move_pct (already in pct units)
                    "avg": h.get("avg_move_pct", h.get("avg", 0.0)),
                }

            a = get_row("A_TREND_PULLBACK", "BUY", "1h")
            b = get_row("B_VOL_BREAKOUT", "BUY", "1h")
            if not a or not b:
                return

            na = int(a.get("n", 0) or 0)
            nb = int(b.get("n", 0) or 0)

            min_na = int(getattr(self, "EZ_ADAPT_MIN_N_A_1H", 10))
            min_nb = int(getattr(self, "EZ_ADAPT_MIN_N_B_1H", 8))
            if na < min_na or nb < min_nb:
                return

            # Score: win% dominates; avg% breaks ties.
            # "avg" is already in percent units in both formats above.
            a_score = float(a.get("win_pct", 0.0)) + float(a.get("avg", 0.0)) * 100.0
            b_score = float(b.get("win_pct", 0.0)) + float(b.get("avg", 0.0)) * 100.0

            min_conf = int(getattr(self, "EZ_B_MIN_CONF", 80))
            tie_adv  = int(getattr(self, "EZ_B_TIE_ADVANTAGE", 25))

            # Bench logic knobs
            bench_sec = int(getattr(self, "EZ_B_BENCH_SEC", 3600))  # 1h default
            now = int(_time.time())

            # If B clearly underperforms, tighten + optionally bench B for a while.
            # If B clearly outperforms, loosen and unbench.
            if b_score + 2.0 < a_score:
                min_conf = min(95, min_conf + 5)
                tie_adv  = min(60, tie_adv + 5)

                # If B is really bad (e.g., win% == 0 with enough n), bench it temporarily.
                try:
                    bwin = float(b.get("win_pct", 0.0))
                    if nb >= min_nb and bwin <= 0.0:
                        self.EZ_DISABLE_B = True
                        self.EZ_B_BENCH_UNTIL_TS = now + bench_sec
                except Exception:
                    pass

            elif b_score > a_score + 2.0:
                min_conf = max(50, min_conf - 5)
                tie_adv  = max(0,  tie_adv - 5)

                # If B is doing well, unbench it.
                self.EZ_DISABLE_B = False
                self.EZ_B_BENCH_UNTIL_TS = 0

            self.EZ_B_MIN_CONF = int(min_conf)
            self.EZ_B_TIE_ADVANTAGE = int(tie_adv)

        except Exception:
            return

    def _b_breakout_confirmed(self, highs15, vols15, price) -> bool:
        """Return True only when breakout is confirmed by price + volume.

        Conditions:
        - price breaks above recent highs (lookback)
        - recent avg volume exceeds baseline avg volume by a multiplier
        """
        try:
            lookback = int(getattr(self, "EZ_B_BREAKOUT_LOOKBACK", 40))
            vol_mult = float(getattr(self, "EZ_B_BREAKOUT_VOL_MULT", 1.4))
            min_bars = int(getattr(self, "EZ_B_BREAKOUT_MIN_BARS", 60))

            if not isinstance(highs15, list) or not isinstance(vols15, list):
                return False
            if len(highs15) < max(min_bars, lookback + 5) or len(vols15) < max(min_bars, lookback + 5):
                return False

            recent_high = max(float(x) for x in highs15[-lookback:])
            if float(price) <= float(recent_high):
                return False

            v_now = sum(float(v) for v in vols15[-lookback:]) / float(lookback)
            v_base = sum(float(v) for v in vols15[-2*lookback:-lookback]) / float(lookback)
            if v_base <= 0:
                return False
            if v_now < vol_mult * v_base:
                return False

            return True
        except Exception:
            return False


    def _record_seen(self, st_or_sig, sig=None) -> None:

        """Record the selected signal every tick for debugging/telemetry.


        Back-compat:

          - _record_seen(sig)

          - _record_seen(st, sig)

        """

        try:

            # Allow both call styles

            if sig is None:

                st = {}

                sig = st_or_sig

            else:

                st = st_or_sig


            if not isinstance(st, dict) or sig is None:

                return


            seen = st.setdefault("seen_signals", {})

            log = st.setdefault("seen_signals_log", [])

            now = int(time.time())

            rec = {

                "ts": now,

                "action": getattr(sig, "action", None),

                "symbol": getattr(sig, "symbol", None),

                "price": float(getattr(sig, "price", 0.0) or 0.0),

                "rsi": None if getattr(sig, "rsi", None) is None else float(getattr(sig, "rsi")),

                "confidence": int(getattr(sig, "confidence", 0) or 0),

                "strategy": getattr(sig, "strategy", None),

                "reasons": list(getattr(sig, "reasons", []) or []),

                "kind": getattr(sig, "kind", None),

            }

            sym = rec.get("symbol") or "UNKNOWN"

            seen[sym] = rec

            log.append(rec)

            # keep last 200

            if len(log) > 200:

                del log[:-200]

        except Exception:

            # never let telemetry break trading loop

            pass

    def tick_paper(self,
                   bars_15m: Dict[str, List[float]],
                   bars_1h: Dict[str, List[float]],
                   highs_15m: Dict[str, List[float]],
                   lows_15m: Dict[str, List[float]],
                   vols_15m: Dict[str, List[float]]) -> None:

        st = self.state.load()
        symbol = self.cfg.primary_symbol

        # --- DECISION tick header (rate-limited) ---
        try:
            if getattr(self, 'EZ_DECISION_LOG', False) and bool(st.get('_diag_emit', True)):
                n = int(st.get('_diag_n', 0) or 0) + 1
                st['_diag_n'] = n
                every = int(getattr(self, 'EZ_DECISION_EVERY', 10) or 10)
                emit = (every <= 1) or (n % every == 1)
                st['_diag_emit'] = emit
                if emit:
                    self.log.line('[DECISION] tick_paper start symbol=%s n=%s every=%s' % (symbol, n, every))
        except Exception:
            pass

        # --- DECISION DIAGNOSTICS (safe logging): tick header ---

                # --- DECISION DIAGNOSTICS (safe logging): tick header (throttled) ---
        try:
            if getattr(self, 'EZ_DECISION_LOG', False):
                every = int(getattr(self, 'EZ_DECISION_EVERY', 10) or 10)
                if every < 1:
                    every = 1
                n = int(getattr(self, '_ez_decision_tick_n', 0) or 0) + 1
                setattr(self, '_ez_decision_tick_n', n)
                if (n % every) == 1:
                    self._diag('tick_paper start symbol=' + str(symbol) + ' n=' + str(n) + ' every=' + str(every))
        except Exception:
            pass


        closes15 = bars_15m[symbol]
        closes1h = bars_1h[symbol]
        price = float(closes15[-1])
        # --- auto-unbench Strategy B when bench window expires ---
        try:
            if bool(getattr(self, "EZ_DISABLE_B", False)):
                until_ts = int(getattr(self, "EZ_B_BENCH_UNTIL_TS", 0) or 0)
                if until_ts and int(time.time()) >= until_ts:
                    self.EZ_DISABLE_B = False
                    self.EZ_B_BENCH_UNTIL_TS = 0
        except Exception:
            pass


        # heartbeat: ensures log file exists even when no alerts fire
        try:
            self.log.log('TICK {} price={:.2f}'.format(symbol, price))
        except Exception:
            pass

        sig_a = self.strat_a.generate(symbol, closes15, closes1h, price)
        sig_b = self.strat_b.generate(
            symbol,
            highs_15m[symbol],
            lows_15m[symbol],
            closes15,
            vols_15m[symbol],
            price
        )

        
        # --- signal selection + weighting ---
        # Gate Strategy B unless confidence is strong (prevents weak breakout noise)
        try:
            if getattr(sig_b, "action", "NONE") != "NONE":
                if int(getattr(sig_b, "confidence", 0) or 0) < int(getattr(self, 'EZ_B_MIN_CONF', 80)):
                    sig_b = Signal("NONE", symbol, price, sig_b.rsi, 0, ["B gated: low confidence"], None, getattr(sig_b, "kind", None))
        except Exception:
            pass

        # Prefer A unless B clearly dominates by a margin
        sig = sig_a if sig_a.action != "NONE" else sig_b
        if sig_a.action != "NONE" and sig_b.action != "NONE":
            aconf = int(getattr(sig_a, "confidence", 0) or 0)
            bconf = int(getattr(sig_b, "confidence", 0) or 0)
            sig = sig_b if (bconf >= aconf + int(getattr(self, 'EZ_B_TIE_ADVANTAGE', 25))) else sig_a

        # If BOTH strategies are NONE, use a neutral NONE signal so telemetry isn't tagged to B by default
        if getattr(sig_a, 'action', 'NONE') == 'NONE' and getattr(sig_b, 'action', 'NONE') == 'NONE':
            rsi0 = sig_a.rsi if getattr(sig_a, 'rsi', None) is not None else getattr(sig_b, 'rsi', None)
            sig = Signal(
                'NONE', symbol, price,
                rsi0,
                0,
                ['No signal (A&B NONE)'],
                'NONE',
                'NONE',
            )



        # --- BUY attempt diagnostics (pre-gate) ---



        try:



            diag = st.setdefault('diag', {})



            # Count raw B breakout BUY attempts BEFORE any gating converts it to NONE



            if getattr(sig_b, 'action', 'NONE') == 'BUY':



                diag['buy_attempts_B'] = int(diag.get('buy_attempts_B', 0) or 0) + 1



        except Exception:



            pass




        # --- pre-BUY gating (RSI + confirm streak) [BEFORE record_seen] ---
        try:
            confirm = st.setdefault('confirm', {})
            bs = confirm.setdefault('buy_streaks', {})
            sym = symbol
        
            # update streak (reset on non-BUY)
            if getattr(sig, 'action', 'NONE') == 'BUY':
                bs[sym] = int(bs.get(sym, 0) or 0) + 1
            else:
                bs[sym] = 0
        
            # RSI ceiling
            rsi_now = getattr(sig, 'rsi', None)
            rsi_max = float(getattr(self, 'EZ_BUY_RSI_MAX', 70.0))
            if getattr(sig, 'action', 'NONE') == 'BUY' and rsi_now is not None and float(rsi_now) >= rsi_max:
                bs[sym] = 0
                sig = Signal(
                    'NONE',
                    sym,
                    price,
                    rsi_now,
                    0,
                    ['BUY gated: RSI too high (>= {:.1f})'.format(rsi_max)],
                    None,
                    getattr(sig, 'kind', None),
                )
        
            # Confirm streak gate
            need = int(getattr(self, 'EZ_BUY_CONFIRM_BARS', 2))
            if getattr(sig, 'action', 'NONE') == 'BUY' and need > 1 and int(bs.get(sym, 0) or 0) < need:
                sig = Signal(
                    'NONE',
                    sym,
                    price,
                    rsi_now,
                    0,
                    ['BUY pending confirm (streak {}/{})'.format(int(bs.get(sym,0) or 0), need)],
                    None,
                    getattr(sig, 'kind', None),
                )
        except Exception:
            pass



            pass




        self._record_seen(st, sig)


        # --- Strategy A quality filter (RSI band) ---
        # Allow A_TREND_PULLBACK BUY only when RSI is in [40, 65]
        try:
            if getattr(sig, "action", "NONE") == "BUY" and getattr(sig, "strategy", None) == "A_TREND_PULLBACK":
                r = getattr(sig, "rsi", None)
                if r is not None:
                    rr = float(r)
                    if rr < 40.0 or rr > 65.0:
                        sig = Signal(
                            "NONE",
                            symbol,
                            price,
                            r,
                            0,
                            ["A gated: RSI out of band (40-65)"],
                            None,
                            getattr(sig, "kind", None),
                        )
        except Exception:
            pass


        # --- Strategy A trend filter (1H regime) ---
        # Allow A_TREND_PULLBACK BUY only when 1h trend isn't down: SMA20 >= SMA50
        try:
            if getattr(sig, "action", "NONE") == "BUY" and getattr(sig, "strategy", None) == "A_TREND_PULLBACK":
                c1h = closes1h
                if isinstance(c1h, list) and len(c1h) >= 55:
                    sma20 = sum(c1h[-20:]) / 20.0
                    sma50 = sum(c1h[-50:]) / 50.0
                    if sma20 < sma50:
                        sig = Signal(
                            "NONE",
                            symbol,
                            price,
                            getattr(sig, "rsi", None),
                            0,
                            ["A gated: downtrend (SMA20<SMA50)"],
                            None,
                            getattr(sig, "kind", None),
                        )
        except Exception:
            pass



        
        # --- MARKET REGIME FILTER ---
        try:
            regime_ok = True

            if len(closes15) >= 200:

                ema50 = sum(closes15[-50:]) / 50.0
                ema200 = sum(closes15[-200:]) / 200.0

                regime_ok = ema50 > ema200

        except Exception:
            regime_ok = True


        # ------------------------
        # FLAT → consider BUY
        # ------------------------

        # --- DECISION FINAL SUMMARY (A/B + final sig) ---

        # --- DECISION SELECTED SUMMARY (winner + codes) ---
        def _rc(s: str) -> str:
            """Reason code mapper: keeps logs countable while staying human-readable."""
            try:
                t = (s or "").strip().lower()
            except Exception:
                t = ""
            # A-side
            if "trend filter blocked" in t:
                return "A_BLOCK_TREND"
            if "rsi out of band" in t:
                return "A_RSI_BAND"
            if "downtrend" in t:
                return "A_DOWNTREND"
            # B-side
            if "no breakout" in t:
                return "B_NO_BREAKOUT"
            if "low confidence" in t:
                return "B_LOW_CONF"
            if "breakout above" in t:
                return "B_BREAKOUT"
            if "volume above" in t:
                return "B_VOL"
            if "atr expansion" in t:
                return "B_ATR"
            # BUY gates
            if "buy gated: rsi too high" in t:
                return "BUY_RSI_GATE"
            if "buy pending confirm" in t:
                return "BUY_CONFIRM_WAIT"
            # default
            return "OTHER"

        def _codes(reasons):
            try:
                rr = reasons or []
                return [_rc(str(x)) for x in rr]
            except Exception:
                return []

        # Winner attribution (best-effort; no behavior changes)
        try:
            a_conf = int(getattr(sig_a, "confidence", 0) or 0)
            b_conf = int(getattr(sig_b, "confidence", 0) or 0)
            winner = "NONE"
            why = "n/a"
            # identity check first
            if sig is sig_a:
                winner = "A"
            elif sig is sig_b:
                winner = "B"

            # explain "why" in a deterministic way
            if a_conf > b_conf:
                why = "confidence_higher(A)"
            elif b_conf > a_conf:
                why = "confidence_higher(B)"
            elif a_conf == b_conf and (a_conf > 0 or b_conf > 0):
                # If tie, B can be favored by EZ_B_TIE_ADVANTAGE (existing knob)
                try:
                    tie_adv = int(getattr(self, "EZ_B_TIE_ADVANTAGE", 0) or 0)
                except Exception:
                    tie_adv = 0
                why = "tie"
                if tie_adv and winner == "B":
                    why = "tie_advantage(B)"

            if getattr(self, "EZ_DECISION_LOG", False):
                self.log.line("[DECISION] SELECTED winner={} why={} A_conf={} B_conf={} A_codes={} B_codes={} FINAL_codes={}".format(
                    winner, why, a_conf, b_conf,
                    _codes(getattr(sig_a, "reasons", None)),
                    _codes(getattr(sig_b, "reasons", None)),
                    _codes(getattr(sig, "reasons", None)),
                ))
        except Exception:
            pass


        if getattr(self, 'EZ_DECISION_LOG', False):

            try:

                maxr = int(getattr(self, 'EZ_DECISION_MAX_REASONS', 3) or 3)

                def _r(x):

                    rr = getattr(x, 'reasons', None)

                    if not rr: return []

                    try: return list(rr)[:maxr]

                    except Exception: return []

                sa = locals().get('sig_a', None)

                sb = locals().get('sig_b', None)

                if sa is not None:

                    self.log.line('[DECISION] A action={} conf={} rsi={} reasons={}'.format(

                        getattr(sa,'action',None), getattr(sa,'confidence',None), getattr(sa,'rsi',None), _r(sa)

                    ))

                if sb is not None:

                    self.log.line('[DECISION] B action={} conf={} rsi={} reasons={}'.format(

                        getattr(sb,'action',None), getattr(sb,'confidence',None), getattr(sb,'rsi',None), _r(sb)

                    ))

                self.log.line('[DECISION] FINAL action={} strat={} conf={} rsi={} reasons={}'.format(

                    getattr(sig,'action',None), getattr(sig,'strategy',None), getattr(sig,'confidence',None), getattr(sig,'rsi',None), _r(sig)

                ))

            except Exception:

                pass



        # --- CONFIDENCE SCORE LOG ---
        try:
            confidence_score = int(self._simple_confidence_score(sig) or 0)
            setattr(sig, "confidence_score", confidence_score)
            try:
                self.log.line("[CONF] score={} strat={} action={} rsi={}".format(
                    confidence_score,
                    getattr(sig, "strategy", None),
                    getattr(sig, "action", None),
                    getattr(sig, "rsi", None),
                ))
            except Exception:
                pass
        except Exception:
            confidence_score = 0

        
        
        # --- MARKET REGIME DETECTOR ---
        try:
            if len(closes15) >= 200:
                ema50 = sum(closes15[-50:]) / 50.0
                ema200 = sum(closes15[-200:]) / 200.0
                trend_strength = abs(ema50 - ema200)

                atr = self._atr(highs15, lows15, closes15, 14)

                regime_score = trend_strength / atr if atr else 0

                if regime_score < 0.8:
                    sig.action = "NONE"
        except Exception:
            pass

        # --- TREND STRENGTH FILTER ---
        try:
            if len(closes15) >= 200:
                ema50 = sum(closes15[-50:]) / 50.0
                ema200 = sum(closes15[-200:]) / 200.0
                trend_strength = abs(ema50 - ema200) / ema200 * 100.0

                if trend_strength < 0.25:
                    sig.action = "NONE"
        except Exception:
            pass

        
        # --- TRADE COOLDOWN FILTER ---
        try:
            perf = st.get("perf", {}) or {}
            last_trade_bar = perf.get("last_trade_bar")
            current_bar = len(closes15)

            if last_trade_bar is not None:
                if current_bar - last_trade_bar < 10:
                    sig.action = "NONE"
        except Exception:
            pass

        if regime_ok and sig.action == "BUY" and not st.get("perf", {}).get("open_pos"):
            rd = self.risk.allow_action(st, "BUY", symbol, price)
            suggested_usd = rd.trade_usd
            suggested_qty = 0.0 if price <= 0 else (suggested_usd / price)
            # PERF_OPEN_ON_REAL_BUY
            self._perf_open(st, symbol, price, getattr(sig,'rsi',None), getattr(sig,'strategy',None), getattr(sig,'reasons',None))
            try:
                perf = st.setdefault("perf", {})
                op = perf.get("open_pos")
                if op and op.get("symbol") == symbol:
                    op["entry_confidence_score"] = int(confidence_score or 0)
            except Exception:
                pass
            try:
                perf = st.setdefault("perf", {})
                op = perf.get("open_pos")
                if op and op.get("symbol") == symbol:
                    op["entry_bar"] = len(closes15)
            except Exception:
                pass
            try:
                st.setdefault("holdings", {})[symbol] = float(suggested_qty)
            except Exception:
                pass

            if self._should_announce(st, sig):
                self.announce_signal(sig, suggested_usd, suggested_qty)


        # --- PAPER STOP-LOSS EXIT ---
        try:
            perf = st.get("perf", {}) or {}
            op = perf.get("open_pos")
            if op and op.get("symbol") == symbol:
                entry_price = float(op.get("entry_price") or 0.0)
                stop_pct = float(getattr(self, "EZ_PAPER_STOP_LOSS_PCT", 1.5) or 1.5)
                if entry_price > 0 and price is not None:
                    move_pct = ((float(price) - entry_price) / entry_price) * 100.0
                    if move_pct <= -abs(stop_pct) and min_hold_bars_ok:
                        exit_sig = Signal("SELL", symbol, price,
                                          sig.rsi, 90,
                                          [f"STOPLOSS {move_pct:.3f}% <= -{abs(stop_pct):.3f}%"],
                                          None,
                                          "STOPLOSS")
                        qty = float(st.get("holdings", {}).get(symbol, 0.0))
                        if qty > 1e-12:
                            suggested_usd = qty * price
                            self._perf_close(st, symbol, price,
                                             getattr(exit_sig, 'rsi', None),
                                             getattr(exit_sig, 'strategy', None),
                                             getattr(exit_sig, 'reasons', None))
                            try:
                                st.setdefault("holdings", {})[symbol] = 0.0
                            except Exception:
                                pass
                            if self._should_announce(st, exit_sig):
                                if self._last_announced.get(symbol) != "SELL":
                                    self.announce_signal(exit_sig, suggested_usd, qty)
                                    self._last_announced[symbol] = "SELL"
        except Exception:
            pass


        # --- MIN HOLD BARS GUARD ---
        min_hold_bars_ok = True
        try:
            perf = st.get("perf", {}) or {}
            op = perf.get("open_pos")
            if op and op.get("symbol") == symbol:
                entry_bar = int(op.get("entry_bar") or 0)
                bars_held = max(0, len(closes15) - entry_bar)
                min_hold_bars_ok = bars_held >= int(getattr(self, "EZ_MIN_HOLD_BARS", 2) or 2)
        except Exception:
            min_hold_bars_ok = True


        # --- INTELLIGENT TREND-FAIL EXIT ---
        try:
            if False and bool(getattr(self, "EZ_USE_TREND_FAIL_EXIT", True)):
                perf = st.get("perf", {}) or {}
                op = perf.get("open_pos")
                if op and op.get("symbol") == symbol and min_hold_bars_ok:
                    qty = float(st.get("holdings", {}).get(symbol, 0.0))
                    if qty > 1e-12 and len(closes15) >= 20:
                        ema20_now = sum(closes15[-20:]) / 20.0
                        if price < ema20_now:
                            exit_sig = Signal("SELL", symbol, price,
                                              sig.rsi, 85,
                                              [f"TREND_FAIL price<{ema20_now:.3f} EMA20"],
                                              None,
                                              "TREND_FAIL")
                            suggested_usd = qty * price
                            self._perf_close(st, symbol, price,
                                             getattr(exit_sig, 'rsi', None),
                                             getattr(exit_sig, 'strategy', None),
                                             getattr(exit_sig, 'reasons', None))
                            try:
                                st.setdefault("holdings", {})[symbol] = 0.0
                            except Exception:
                                pass
                            if self._should_announce(st, exit_sig):
                                if self._last_announced.get(symbol) != "SELL":
                                    self.announce_signal(exit_sig, suggested_usd, qty)
                                    self._last_announced[symbol] = "SELL"
        except Exception:
            pass

        

        if False:
            pass
        # --- RSI MOMENTUM ROLLOVER EXIT DISABLED ---
        try:
            perf = st.get("perf", {}) or {}
            op = perf.get("open_pos")

            if op and op.get("symbol") == symbol:

                qty = float(st.get("holdings", {}).get(symbol, 0.0))

                if qty > 1e-12 and len(rsi15) >= 2:

                    rsi_now = rsi15[-1]
                    rsi_prev = rsi15[-2]

                    if rsi_now > 65 and rsi_now < rsi_prev:

                        exit_sig = Signal(
                            "SELL",
                            symbol,
                            price,
                            rsi_now,
                            85,
                            ["RSI momentum rollover"],
                            None,
                            "RSI_ROLL"
                        )

                        suggested_usd = qty * price

                        self._perf_close(
                            st,
                            symbol,
                            price,
                            getattr(exit_sig,'rsi',None),
                            getattr(exit_sig,'strategy',None),
                            getattr(exit_sig,'reasons',None)
                        )

                        try:
                            st.setdefault("holdings", {})[symbol] = 0.0
                        except Exception:
                            pass

                        if self._should_announce(st, exit_sig):
                            if self._last_announced.get(symbol) != "SELL":
                                self.announce_signal(exit_sig, suggested_usd, qty)
                                self._last_announced[symbol] = "SELL"

        except Exception:
            pass



        if False:
            pass
        # --- ATR TAKE PROFIT EXIT DISABLED ---
        try:
            perf = st.get("perf", {}) or {}
            op = perf.get("open_pos")

            if op and op.get("symbol") == symbol:

                entry_price = float(op.get("entry_price", 0))
                qty = float(st.get("holdings", {}).get(symbol, 0.0))

                if qty > 1e-12 and len(closes15) >= 15:

                    # simple ATR approximation
                    atr = max(closes15[-15:]) - min(closes15[-15:])

                    target = entry_price + (atr * 0.7)

                    if price >= target:

                        exit_sig = Signal(
                            "SELL",
                            symbol,
                            price,
                            getattr(sig,"rsi",None),
                            90,
                            [f"ATR target {target:.2f}"],
                            None,
                            "ATR_TP"
                        )

                        suggested_usd = qty * price

                        self._perf_close(
                            st,
                            symbol,
                            price,
                            getattr(exit_sig,'rsi',None),
                            getattr(exit_sig,'strategy',None),
                            getattr(exit_sig,'reasons',None)
                        )

                        try:
                            st.setdefault("holdings", {})[symbol] = 0.0
                        except Exception:
                            pass

                        if self._should_announce(st, exit_sig):
                            if self._last_announced.get(symbol) != "SELL":
                                self.announce_signal(exit_sig, suggested_usd, qty)
                                self._last_announced[symbol] = "SELL"

        except Exception:
            pass

# ------------------------
        # IN POSITION → consider SELL (RSI exit)
        # ------------------------

        
        # --- ATR stop loss ---
        try:
            if bool(getattr(self,"EZ_USE_ATR_STOP",False)):
                atr=_calc_atr(highs_15m,lows_15m,closes15,int(getattr(self,"EZ_ATR_PERIOD",14)))
                if atr:
                    mult=float(getattr(self,"EZ_ATR_MULT",1.2))
                    stop_price=st.get("perf",{}).get("open_pos",{}).get("entry_price",price)-atr*mult
                    if price <= stop_price:
                        exit_sig = Signal("SELL", symbol, price,
                                          sig.rsi, 90,
                                          ["ATR stop"],
                                          None,
                                          "ATR_STOP")
        except Exception:
            pass

        if sig.rsi is not None and sig.rsi >= 70.0 and min_hold_bars_ok:
            exit_sig = Signal("SELL", symbol, price,
                              sig.rsi, 80,
                              ["RSI>=70 exit"],
                              None,
                              "EXIT")

            qty = float(st.get("holdings", {}).get(symbol, 0.0))
            # Guardrail: suppress SELL alerts when no holdings
            if qty <= 1e-12:
                pass
            else:
                suggested_usd = qty * price
                # PERF_CLOSE_ON_EXIT
                self._perf_close(st, symbol, price, getattr(exit_sig,'rsi',None), getattr(exit_sig,'strategy',None), getattr(exit_sig,'reasons',None))
                try:
                    st.setdefault("holdings", {})[symbol] = 0.0
                except Exception:
                    pass
                if self._should_announce(st, exit_sig):
                    if self._last_announced.get(symbol) != "SELL":
                        self.announce_signal(exit_sig, suggested_usd, qty)
                        self._last_announced[symbol] = "SELL"

        self._record_seen(st, sig)
        self.state.save(st)
