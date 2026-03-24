import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if "app" in sys.modules:
    mod = sys.modules.get("app")
    if getattr(mod, "__file__", "").endswith("ezmarketing_site/app.py"):
        del sys.modules["app"]

from app.server import (
    _ez_live_kraken_price_symbol,
    _ez_kraken_ohlc_symbol,
    _ez_build_signals_from_candles,
    _ez_norm_symbol,
)

SIGNAL_FILE = os.path.abspath("signals/latest_signal.json")
ANALYTICS_FILE = os.path.abspath("logs/ezcore_v1_signal_analytics.json")
TRADE_HISTORY_FILE = os.path.abspath("signals/assistant_trade_history.json")
WAITLIST_FILE = os.path.abspath("waitlist.json")

TG_BOT_TOKEN = os.environ.get("EZTRADER_TG_BOT_TOKEN", "").strip()
ADMIN_TG_CHAT_ID = os.environ.get("EZTRADER_ADMIN_TG_CHAT_ID", "-1003642621722").strip()

HOST = "0.0.0.0"
PORT = 8091

def send_admin_signup_alert(email, signed_up_at, count):
    if not TG_BOT_TOKEN or not ADMIN_TG_CHAT_ID:
        return
    message = (
        "📥 New EZTrader AI Signup\n\n"
        f"Email: {email}\n"
        f"Time: {signed_up_at}\n"
        f"Total Signups: {count}"
    )
    data = urllib.parse.urlencode({
        "chat_id": ADMIN_TG_CHAT_ID,
        "text": message,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
        data=data,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except Exception as e:
        print("admin signup alert failed:", e)

HTML = """<!doctype html>
<html>
<head>
  <link rel="icon" type="image/svg+xml" href="/assets/eztrader_favicon.svg">
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>EZTrader AI — Live Trading Engine</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg:#0E1117;
      --panel:#161B22;
      --text:#F2F4F8;
      --muted:rgba(242,244,248,.62);
      --gold:#D4A017;
      --green:#1EB980;
      --red:#E55353;
      --blue:#3A8DFF;
      --border:rgba(255,255,255,.08);
    }
    * { box-sizing:border-box; }
    body { word-break:break-word; max-width:100vw; overflow-x:hidden;
      margin:0; background:var(--bg); color:var(--text);
      font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Arial,sans-serif;
    }
    .wrap { max-width:1100px; margin:0 auto; padding:28px 18px 56px; }
    .top { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:28px; }
    .brand { display:flex; align-items:center; gap:14px; }
    
.logo {
  width:52px;
  height:52px;
  border-radius:16px;
  background:var(--panel);
  border:1px solid var(--border);
  display:flex;
  align-items:center;
  justify-content:center;
  overflow:hidden;
}

.logo svg {
  width:36px;
  height:36px;
  display:block;
}
.logo .zwrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.logo .arrow-shaft {
  position: absolute;
  left: 11px;
  top: 13px;
  width: 16px;
  height: 2px;
  background: var(--gold);
  transform: rotate(-35deg);
  transform-origin: left center;
}

.logo .arrow-head {
  position: absolute;
  left: 24px;
  top: 6px;
  width: 8px;
  height: 8px;
  border-top: 2px solid var(--gold);
  border-right: 2px solid var(--gold);
  transform: rotate(10deg);
}

    .logo span { position:relative; display:inline-block; }
    .logo .zwrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.logo .arrow-shaft {
  position: absolute;
  left: 11px;
  top: 13px;
  width: 16px;
  height: 2px;
  background: var(--gold);
  transform: rotate(-35deg);
  transform-origin: left center;
}

.logo .arrow-head {
  position: absolute;
  left: 24px;
  top: 6px;
  width: 8px;
  height: 8px;
  border-top: 2px solid var(--gold);
  border-right: 2px solid var(--gold);
  transform: rotate(10deg);
}
    .muted { color:var(--muted); }
    .hero, .panel { max-width:100%; box-sizing:border-box;
      background:var(--panel); border:1px solid var(--border);
      border-radius:28px;
    }
    .hero { padding:32px; margin-bottom:24px; }
    .hero h1 { margin:0 0 10px; font-size:42px; line-height:1.05; }
    .hero p { margin:0; max-width:720px; color:var(--muted); }
    .grid { display:grid; grid-template-columns:1.15fr .85fr; gap:24px; margin-bottom:24px; }
    .panel { max-width:100%; box-sizing:border-box; padding:24px; margin-top:24px; }
    .kicker { font-size:12px; letter-spacing:.18em; text-transform:uppercase; color:var(--gold); }
    .main-value { font-size:44px; font-weight:700; line-height:1; margin:8px 0; }
    .signal-row { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:16px; }
    .card {
      background:var(--bg); border:1px solid var(--border);
      border-radius:20px; padding:16px;
    }
    .label { font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }
    .value { margin-top:8px; font-size:22px; font-weight:600; }
    .mini-grid {
      display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:14px;
    }
    .row {
      display:flex; justify-content:space-between; gap:12px;
      padding:12px 0; border-bottom:1px solid var(--border);
    }
    .row:last-child { border-bottom:none; }
    .buy { color:var(--green); }
    .sell { color:var(--red); }
    .hold, .none { color:var(--blue); }
    .footer {
      margin-top:24px; text-align:center; color:var(--muted); font-size:14px;
    }
    input {
      padding:12px; width:260px; border-radius:10px; border:none; outline:none;
    }
    button {
      padding:12px 18px; background:#ffd700; border:none; border-radius:10px;
      margin-left:10px; cursor:pointer;
    }
    @media (max-width: 900px) {
      .grid { grid-template-columns:1fr; }
      .hero h1 { font-size:34px; }
      .main-value { font-size:36px; }
      .top { align-items:flex-start; flex-direction:column; }
      input { width:100%; }
      button { margin-left:0; margin-top:10px; width:100%; }
    }
  </style>
</head>
<body>
  <div class="wrap"><div style="font-size:12px;color:var(--muted);margin-bottom:10px;">Independent platform. Not affiliated with any previous company using similar naming.</div>
    <div class="top">
      <div class="brand">
        <div class="logo" aria-label="EZTrader AI logo">
  <svg viewBox="0 0 52 52" xmlns="http://www.w3.org/2000/svg" role="img">
    <!-- E -->
    <rect x="7" y="11" width="4" height="22" fill="#F2F4F8"/>
    <rect x="7" y="11" width="12" height="4" fill="#F2F4F8"/>
    <rect x="7" y="20" width="10" height="4" fill="#F2F4F8"/>
    <rect x="7" y="29" width="12" height="4" fill="#F2F4F8"/>

    <!-- Z -->
    <rect x="23" y="11" width="14" height="4" fill="#F2F4F8"/>
    <rect x="23" y="29" width="14" height="4" fill="#F2F4F8"/>

    <!-- Arrow aligned with Z and extended slightly past it -->
    <line x1="24" y1="31" x2="46" y2="7"
          stroke="#D4A017"
          stroke-width="3"
          stroke-linecap="round"/>

    <!-- Arrow head -->
    <line x1="46" y1="7" x2="41" y2="8"
          stroke="#D4A017"
          stroke-width="3"
          stroke-linecap="round"/>

    <line x1="46" y1="7" x2="45" y2="12"
          stroke="#D4A017"
          stroke-width="3"
          stroke-linecap="round"/>
  </svg>
</div>
        <div>
          <div style="font-size:22px;font-weight:700;">EZTrader AI</div>
          <div class="muted">Live AI Trading Engine</div>
        </div>
      </div>
      <div class="muted" id="updated">Updated --</div>
    </div>

    <section class="hero">
      <div class="kicker">Real-Time AI Trading Signals — No Guessing. No Hype.</div>
      <h1>Real-Time AI Trading Signals — No Guessing. No Hype.</h1>
      <p>
        Live market analysis, transparent signal output, and disciplined trade logic before launch.
      </p>
    </section>

    <div class="grid">
      <section class="panel" style="margin-top:0;">
        <div class="kicker">Latest Signal</div>
        <div id="symbol" class="main-value">--</div>
        <div class="signal-row">
          <div class="card">
            <div class="label">Action</div>
            <div id="action" class="value">--</div>
          </div>
          <div class="card">
            <div class="label">Live Price</div>
            <div id="price" class="value">--</div>
          </div>
        </div>
        <div class="mini-grid">
          <div class="card"><div class="label">Confidence</div><div id="confidence" class="value">--</div></div>
          <div class="card"><div class="label">Suggested Trade</div><div id="trade" class="value">--</div></div>
          <div class="card"><div class="label">Strategy</div><div id="strategy" class="value">--</div></div>
          <div class="card"><div class="label">Preferred Strategy</div><div id="preferred" class="value">--</div></div>
        </div>
      </section>

      <section class="panel" style="margin-top:0;">
        <div class="kicker">Engine Status</div>
        <div class="row"><span class="muted">Regime</span><strong id="regime">--</strong></div>
        <div class="row"><span class="muted">Trend</span><strong id="trend">--</strong></div>
        <div class="row"><span class="muted">Risk Level</span><strong id="risk">--</strong></div>
        <div class="row"><span class="muted">Trade Eligible</span><strong id="eligible">--</strong></div>
        <div class="row"><span class="muted">Eligibility Reason</span><strong id="eligibility_reason">--</strong></div>
        <div class="row"><span class="muted">Quality Blocked</span><strong id="quality_blocked">--</strong></div>
        <div class="row"><span class="muted">Quality Reason</span><strong id="quality_reason">--</strong></div>
        <div class="row"><span class="muted">RSI</span><strong id="rsi">--</strong></div>
      </section>
    </div>

    <section class="panel">
      <div class="kicker">Strategy Analytics</div>
      <div style="margin-bottom:10px;font-weight:600;">
      AI Strategy Performance (Live Learning Data)
    </div>
    <div style="background:rgba(255,255,255,.02);border:1px solid var(--border);border-radius:12px;padding:12px;min-height:260px;">
      <canvas id="performance_chart" height="220"></canvas>
    </div>
    <div class="muted" style="margin-top:8px;font-size:13px;">
      Shows how EZTrader AI strategies are performing across different timeframes based on real signals.
    </div>
      <div id="strategy_table" style="margin-top:16px;"></div>
    </section>

    <section class="panel">
      <div class="kicker">Recent Executed Trades</div>
      <div id="trade_history" style="margin-top:16px;"></div>
    </section>

    
    
    
    <section class="panel">
      <div class="kicker">Live Portfolio</div>
      <div class="mini-grid" style="margin-top:16px;">
        <div class="card">
          <div class="label">Current Portfolio Value</div>
          <div id="pf_value" class="value">--</div>
        </div>
        <div class="card">
          <div class="label">Cash Balance</div>
          <div id="pf_cash" class="value">--</div>
        </div>
        <div class="card">
          <div class="label">BTC Holdings</div>
          <div id="pf_qty" class="value">--</div>
        </div>
        <div class="card">
          <div class="label">Average Entry Price</div>
          <div id="pf_avg" class="value">--</div>
        </div>
        <div class="card">
          <div class="label">Current BTC Price</div>
          <div id="pf_price" class="value">--</div>
        </div>
        <div class="card">
          <div class="label">Unrealized P/L</div>
          <div id="pf_upl" class="value">--</div>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="kicker">AI Decision</div>
      <div class="row"><span class="muted">Symbol</span><strong id="ai_symbol">--</strong></div>
      <div class="row"><span class="muted">Confidence</span><strong id="ai_confidence">--</strong></div>
      <div class="row"><span class="muted">Regime</span><strong id="ai_regime">--</strong></div>
      <div class="row"><span class="muted">Trend</span><strong id="ai_trend">--</strong></div>
      <div class="row"><span class="muted">Decision</span><strong id="ai_decision">--</strong></div>
      <div class="row"><span class="muted">Reason</span><strong id="ai_reason">--</strong></div>
    </section>

    <section class="panel">
      <div class="kicker">Why This Matters</div>
      <p class="muted" style="margin:10px 0 0;">
        EZTrader AI does not force trades. It continuously evaluates market conditions and only comes alive
        when a valid setup appears.
      </p>
    </section>

    <section class="panel">
      <div class="kicker">EZTrader AI Access</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin-top:18px;">
        <div class="card">
          <div class="label">Basic</div>
          <div style="font-size:32px;font-weight:700;margin-top:6px;">$19</div>
          <div class="muted" style="margin-top:8px;">per month</div>
      <div class="muted" style="margin-top:8px;font-size:12px;">Pricing subject to change at launch.</div>
      
          <ul style="margin-top:14px;color:var(--muted);padding-left:18px;">
            <li>BUY / SELL signals</li>
            <li>Confidence rating</li>
            <li>Market regime detection</li>
            <li>Manual trading</li>
          </ul>
        </div>
        <div class="card" style="border:1px solid var(--gold);">
          <div class="label">Pro</div>
          <div style="font-size:32px;font-weight:700;margin-top:6px;">$49</div>
          <div class="muted" style="margin-top:8px;">per month</div>
      <div class="muted" style="margin-top:8px;font-size:12px;">Pricing subject to change at launch.</div>
      
          <ul style="margin-top:14px;color:var(--muted);padding-left:18px;">
            <li>Everything in Basic</li>
            <li>Recommended trade sizes</li>
            <li>Portfolio-aware signals</li>
            <li>Advanced strategy insights</li>
          </ul>
        </div>
        <div class="card">
          <div class="label">Elite</div>
          <div style="font-size:32px;font-weight:700;margin-top:6px;">$149</div>
          <div class="muted" style="margin-top:8px;">per month</div>
      <div class="muted" style="margin-top:8px;font-size:12px;">Pricing subject to change at launch.</div>
      
          <ul style="margin-top:14px;color:var(--muted);padding-left:18px;">
            <li>Everything in Pro</li>
            <li>Fully automated trading</li>
            <li>Execution engine</li>
            <li>Risk management automation</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="kicker">Get Early Access to EZTrader AI</div>
      <div class="muted" style="margin-top:8px;">
        Be among the first to access live AI trading signals and automation.
      </div>
      <div id="waitlist_count" class="muted" style="margin-top:8px;">Join the early access waitlist today.</div>
      <div style="margin-top:16px">
        <input id="email_box" placeholder="Enter email for early access">
        <button onclick="joinWaitlist()">Join</button>
        <div id="wait_msg" style="margin-top:10px;color:#aaa"></div>
      </div>
      <div class="muted" style="margin-top:10px;max-width:720px;">
        We respect your privacy. Your email will only be used for EZTrader AI updates, early access, and product announcements. We will never sell or share your information.
      </div>
    </section>
  </div>

  
  <script>
    function clsForAction(action) {
      const a = String(action || "").toLowerCase();
      if (a === "buy") return "buy";
      if (a === "sell") return "sell";
      if (a === "hold") return "hold";
      return "none";
    }

    function money(v) {
      const n = Number(v);
      if (Number.isNaN(n)) return "--";
      return "$" + n.toLocaleString(undefined, {maximumFractionDigits: 2});
    }

    function setText(id, value, className) {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = value;
      if (className) el.className = "value " + className;
    }

    async function joinWaitlist() {
      const email = document.getElementById("email_box").value.trim();
      if (!email) {
        document.getElementById("wait_msg").innerText = "Please enter an email.";
        return;
      }
      try {
        const r = await fetch("/api/waitlist", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({email: email})
        });
        const data = await r.json();
        if (r.ok) {
          document.getElementById("wait_msg").innerText = "You're on the list. Early access invites coming soon.";
          if (typeof data.count === "number") {
            const c = document.getElementById("waitlist_count");
            if (c) c.innerText = "Join " + data.count.toLocaleString() + " early users on the waitlist.";
          }
          document.getElementById("email_box").value = "";
        } else {
          document.getElementById("wait_msg").innerText = "Signup failed: " + (data.error || "unknown error");
        }
      } catch (e) {
        document.getElementById("wait_msg").innerText = "Signup failed. Check server.";
      }
    }
    async function loadWaitlistCount() {
      try {
        const r = await fetch("/api/waitlist-count");
        const data = await r.json();
        const c = document.getElementById("waitlist_count");
        if (c && typeof data.count === "number") {
          c.innerText = "Join " + data.count.toLocaleString() + " early users on the waitlist.";
        }
      } catch (e) {
        console.log("Waitlist count load error:", e);
      }
    }

    
async function loadEngineStats() {
  const r = await fetch("/api/learning-stats");
  const data = await r.json();

  document.getElementById("signals_observed").textContent = data.signals_observed ?? "--";
  document.getElementById("strategies_learned").textContent = data.strategies_learned ?? "--";
}

async function loadSignal() {
      const r = await fetch("/api/latest-signal");
      const data = await r.json();

      document.getElementById("symbol").textContent = data.symbol || "--";
      setText("action", (
        (data.final_action || data.action) === "NONE" ? "No Trade" :
        (data.final_action || data.action || "--")
      ), clsForAction(data.final_action || data.action));
      document.getElementById("price").textContent = money(data.price);
      document.getElementById("confidence").textContent = (data.confidence ?? "--") + "%";
      document.getElementById("trade").textContent = money(data.suggested_trade_usd);
      document.getElementById("strategy").textContent = (
        data.strategy === "NO_SIGNAL" ? "No Trade" :
        data.strategy === "A_TREND_PULLBACK" ? "Trend Pullback" :
        data.strategy === "B_VOL_BREAKOUT" ? "Volatility Breakout" :
        data.strategy || "--"
      );
      document.getElementById("preferred").textContent = (
        data.preferred_strategy === "A_TREND_PULLBACK" ? "Trend Pullback" :
        data.preferred_strategy === "B_VOL_BREAKOUT" ? "Volatility Breakout" :
        data.preferred_strategy === "NO_SIGNAL" ? "No Trade" :
        data.preferred_strategy || "--"
      );
      document.getElementById("regime").textContent = data.regime || "--";
      document.getElementById("trend").textContent = data.trend || "--";
      document.getElementById("risk").textContent = data.risk_level || "--";
      document.getElementById("eligible").textContent = data.trade_eligible ? "Yes" : "No";
      document.getElementById("eligibility_reason").textContent =
        data.eligibility_reason === "no_trade_signal" ? "No valid setup detected." :
        (data.eligibility_reason || "--");
      document.getElementById("quality_blocked").textContent = data.quality_blocked ? "Yes" : "No";
      document.getElementById("quality_reason").textContent = data.quality_reason || "--";
      document.getElementById("rsi").textContent =
        typeof data.rsi === "number" ? data.rsi.toFixed(2) : "--";

      document.getElementById("ai_symbol").textContent = data.symbol || "--";
      document.getElementById("ai_confidence").textContent = (data.confidence ?? "--") + "%";
      document.getElementById("ai_regime").textContent = data.regime || "--";
      document.getElementById("ai_trend").textContent = data.trend || "--";
      document.getElementById("ai_decision").textContent =
        (data.final_action || data.action) === "NONE" ? "No Trade" :
        (data.final_action || data.action || "No Trade");
      document.getElementById("ai_reason").textContent =
        data.eligibility_reason === "no_trade_signal" ? "No valid setup detected." :
        (data.eligibility_reason || data.quality_reason || "No valid trade setup detected.");

      const updatedEl = document.getElementById("updated");
      if (updatedEl) {
        updatedEl.textContent = "Updated " + new Date().toLocaleTimeString();
      }
    }

    
    async function loadPortfolio() {
      const r = await fetch("/api/portfolio");
      const p = await r.json();

      const money = v => "$" + Number(v).toLocaleString(undefined, {maximumFractionDigits: 2});
      document.getElementById("pf_value").textContent = money(p.portfolio_value);
      document.getElementById("pf_cash").textContent = money(p.cash_usd);
      document.getElementById("pf_qty").textContent = Number(p.qty).toFixed(6);
      document.getElementById("pf_avg").textContent = money(p.avg_price);
      document.getElementById("pf_price").textContent = money(p.current_price);

      const upl = Number(p.unrealized_pl);
      const uplEl = document.getElementById("pf_upl");
      uplEl.textContent = (upl >= 0 ? "+" : "-") + money(Math.abs(upl));
      uplEl.style.color = upl >= 0 ? "var(--green)" : "var(--red)";
    }

    
    async function loadLearning() {
      const r = await fetch("/api/learning-stats");
      const data = await r.json();

      const sig = typeof data.signals_observed === "number"
        ? data.signals_observed.toLocaleString()
        : "--";

      const wins = typeof data.winning_signals === "number"
        ? data.winning_signals.toLocaleString()
        : "--";

      const strat = typeof data.strategies_learned === "number"
        ? data.strategies_learned.toLocaleString()
        : "--";

      // Update learning section (if present)
      const s1 = document.getElementById("signals_observed");
      if (s1) s1.textContent = sig;

      const s2 = document.getElementById("winning_signals");
      if (s2) s2.textContent = wins;

      const s3 = document.getElementById("strategies_learned");
      if (s3) s3.textContent = strat;

      // Update Public Track Record
      const p1 = document.getElementById("trk_wins");
      if (p1) p1.textContent = wins;

      const p2 = document.getElementById("trk_strategies");
      if (p2) p2.textContent = strat;
    }

    async function loadTrades() {
      const r = await fetch("/api/recent-trades");
      const trades = await r.json();
      const container = document.getElementById("trade_history");
      container.innerHTML = "";

      document.getElementById("trk_trades").textContent =
        Array.isArray(trades) ? trades.length.toLocaleString() : "--";

      (Array.isArray(trades) ? [...trades].reverse() : []).forEach(t => {
        const d = document.createElement("div");
        d.className = "card";
        d.style.marginBottom = "12px";
        const time = new Date(t.timestamp * 1000).toLocaleString();
        d.innerHTML = `
          <div class="label">${t.symbol}</div>
          <div class="value">${t.action === "NONE" ? "No Trade" : t.action} @ $${Number(t.price).toLocaleString()}</div>
          <div class="muted">Size: $${t.size_usd}</div>
          <div class="muted">Filled Qty: ${Number(t.filled_qty).toFixed(6)} BTC</div>
          <div class="muted">${time}</div>
        `;
        container.appendChild(d);
      });
    }

    let strategyChart = null;
    async function loadStrategies() {
      const r = await fetch("/api/strategy-analytics");
      const rows = await r.json();
      const container = document.getElementById("strategy_table");
      container.innerHTML = "";

      const filtered = rows
        .filter(r => r.strategy !== "UNKNOWN" && r.strategy !== "NONE")
        .filter(r => r.samples >= 5)
        .sort((a, b) => Number(b.win_pct) - Number(a.win_pct));

      filtered.forEach(r => {
        const d = document.createElement("div");
        d.className = "card";
        d.style.marginBottom = "10px";
        d.innerHTML = `
          <div class="label">${(
            r.strategy === "A_TREND_PULLBACK" ? "Trend Pullback" :
            r.strategy === "B_VOL_BREAKOUT" ? "Volatility Breakout" :
            r.strategy === "NO_SIGNAL" ? "No Trade" :
            r.strategy
          )} (${r.timeframe})</div>
          <div class="muted">Samples: ${r.samples}</div>
          <div class="muted">Win Rate: ${Number(r.win_pct).toFixed(2)}%</div>
          <div class="muted">Avg Move: ${Number(r.avg_move).toFixed(4)}%</div>
        `;
        container.appendChild(d);
      });

      const labels = filtered.map(r => r.strategy + " " + r.timeframe);
      const data = filtered.map(r => Number(r.win_pct));
      const ctx = document.getElementById("performance_chart");

      if (strategyChart) strategyChart.destroy();
      strategyChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels,
          datasets: [{ label: "Win Rate %", data }]
        },
        options: { responsive: true }
      });
    }

    async function boot() {
      try {
        await Promise.all([
          loadPortfolio(),
          loadSignal(),
          loadLearning(),
          loadTrades(),
          loadStrategies()
        ]);
      } catch (e) {
        console.log("Boot error:", e);
      }
    }

    boot();
    setInterval(loadSignal, 5000);
  </script>

</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def _send(self, code=200, content_type="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/waitlist":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                email = data.get("email", "").strip()
                try:
                    with open(WAITLIST_FILE, "r", encoding="utf-8") as f:
                        wl = json.load(f)
                        if not isinstance(wl, list):
                            wl = []
                except Exception:
                    wl = []
                if email:
                    signed_up_at = datetime.now().isoformat(timespec="seconds")
                    wl.append({
                        "email": email,
                        "signed_up_at": signed_up_at
                    })
                    with open(WAITLIST_FILE, "w", encoding="utf-8") as f:
                        json.dump(wl, f, indent=2)
                    send_admin_signup_alert(email, signed_up_at, len(wl))
                self._send(200, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({"status": "ok", "count": len(wl)}).encode("utf-8"))
            except Exception as e:
                self._send(500, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self._send(404, "application/json; charset=utf-8")
        self.wfile.write(json.dumps({"error": "not found"}).encode("utf-8"))

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send()
            self.wfile.write(HTML.encode("utf-8"))
            return

        
        if self.path == "/api/portfolio":
            try:
                with urllib.request.urlopen("http://127.0.0.1:18093/portfolio", timeout=5) as r:
                    raw = json.loads(r.read().decode("utf-8"))

                qty = 0.0
                current_price = 0.0
                if isinstance(raw.get("holdings_qty"), dict):
                    qty = float(raw["holdings_qty"].get("BTC-USD", 0) or 0)
                if isinstance(raw.get("prices"), dict):
                    current_price = float(raw["prices"].get("BTC-USD", 0) or 0)

                payload = {
                    "cash_usd": float(raw.get("cash_usd", 0) or 0),
                    "qty": qty,
                    "avg_price": 0,
                    "current_price": current_price,
                    "portfolio_value": float(raw.get("total_usd", 0) or 0),
                    "unrealized_pl": 0
                }

                self._send(200,"application/json; charset=utf-8")
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            except Exception as e:
                self._send(500,"application/json; charset=utf-8")
                self.wfile.write(json.dumps({"error":str(e)}).encode("utf-8"))
            return

        if self.path == "/api/latest-signal":
            try:
                with urllib.request.urlopen("http://127.0.0.1:18093/signal", timeout=5) as r:
                    raw = json.loads(r.read().decode("utf-8"))
                sig = raw.get("signal", {}) if isinstance(raw, dict) else {}
                payload = {
                    "symbol": sig.get("symbol"),
                    "final_action": sig.get("action"),
                    "action": sig.get("action"),
                    "price": sig.get("price"),
                    "live_price": sig.get("engine_price"),
                    "rsi": sig.get("rsi"),
                    "confidence": sig.get("confidence"),
                    "strategy": sig.get("strategy"),
                    "preferred_strategy": sig.get("strategy"),
                    "regime": sig.get("regime"),
                    "trend": sig.get("trend"),
                    "risk_level": "Medium",
                    "trade_eligible": sig.get("trade_eligible"),
                    "eligibility_reason": sig.get("reason"),
                    "quality_blocked": sig.get("quality_blocked"),
                    "quality_reason": sig.get("reason"),
                    "suggested_trade_usd": 0,
                    "timestamp": sig.get("ts"),
                }
                self._send(200, "application/json; charset=utf-8")
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            except Exception as e:
                self._send(500, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if self.path == "/api/learning-stats":
            try:
                with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                stats = {"signals_observed": 0, "winning_signals": 0, "strategies_learned": 0}
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
                self._send(200, "application/json; charset=utf-8")
                self.wfile.write(json.dumps(stats).encode("utf-8"))
            except Exception as e:
                self._send(500, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if self.path == "/api/recent-trades":
            try:
                with open(TRADE_HISTORY_FILE, "r", encoding="utf-8") as f:
                    trades = json.load(f)
                trades = trades[-5:] if isinstance(trades, list) else []
                self._send(200, "application/json; charset=utf-8")
                self.wfile.write(json.dumps(trades).encode("utf-8"))
            except Exception as e:
                self._send(500, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if self.path == "/api/strategy-analytics":
            try:
                with urllib.request.urlopen("http://127.0.0.1:18093/strategy-stats", timeout=5) as r:
                    raw = json.loads(r.read().decode("utf-8"))
                rows = raw.get("strategies", []) if isinstance(raw, dict) else []
                rows = [{
                    "strategy": x.get("strategy"),
                    "timeframe": x.get("timeframe"),
                    "samples": x.get("samples", 0),
                    "win_pct": x.get("win_pct", 0),
                    "avg_move": x.get("avg_move_pct", 0)
                } for x in rows]
                rows = sorted(rows, key=lambda x: x["samples"], reverse=True)[:10]
                self._send(200, "application/json; charset=utf-8")
                self.wfile.write(json.dumps(rows).encode("utf-8"))
            except Exception as e:
                self._send(500, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self._send(404, "text/plain; charset=utf-8")
        self.wfile.write(b"Not found")

if __name__ == "__main__":
    print(f"Serving EZTrader AI at http://127.0.0.1:{PORT}")
    print(f"Reading signal file: {SIGNAL_FILE}")
    HTTPServer((HOST, PORT), Handler).serve_forever()

    def get_activity_feed(self):
        import os
        posts_dir = "marketing_posts"
        events = []

        if os.path.exists(posts_dir):
            files = sorted(os.listdir(posts_dir), reverse=True)[:10]

            for f in files:
                try:
                    with open(os.path.join(posts_dir, f), "r") as fp:
                        events.append({
                            "file": f,
                            "content": fp.read()
                        })
                except:
                    pass

        return events


        if self.path.startswith("/price"):
            try:
                qs = parse_qs((urlparse(self.path).query or ""))
                sym = (qs.get("symbol") or ["BTC-USD"])[0]
                px = _ez_live_kraken_price_symbol(sym, timeout_sec=2.5)
                self._send(200, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({
                    "ok": bool(px is not None),
                    "symbol": _ez_norm_symbol(sym),
                    "price": px,
                    "ts_ms": int(time.time() * 1000)
                }).encode("utf-8"))
            except Exception as e:
                self._send(500, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        if self.path.startswith("/signals"):
            try:
                qs = parse_qs((urlparse(self.path).query or ""))
                try:
                    interval = int((qs.get("interval") or ["5"])[0])
                except Exception:
                    interval = 5
                try:
                    since = int((qs.get("since") or ["0"])[0]) or None
                except Exception:
                    since = None
                sym = (qs.get("symbol") or ["BTC-USD"])[0]
                candles = _ez_kraken_ohlc_symbol(
                    sym,
                    interval_min=interval,
                    since=since,
                    timeout_sec=6
                )
                signals = _ez_build_signals_from_candles(candles)
                self._send(200, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({
                    "ok": True,
                    "interval": interval,
                    "signals": signals
                }).encode("utf-8"))
            except Exception as e:
                self._send(500, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        if self.path.startswith("/ohlc"):
            try:
                qs = parse_qs((urlparse(self.path).query or ""))
                try:
                    interval = int((qs.get("interval") or ["5"])[0])
                except Exception:
                    interval = 5
                try:
                    since = int((qs.get("since") or ["0"])[0]) or None
                except Exception:
                    since = None
                sym = (qs.get("symbol") or ["BTC-USD"])[0]
                candles = _ez_kraken_ohlc_symbol(
                    sym,
                    interval_min=interval,
                    since=since,
                    timeout_sec=6
                )
                self._send(200, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({
                    "ok": True,
                    "interval": interval,
                    "candles": candles
                }).encode("utf-8"))
            except Exception as e:
                self._send(500, "application/json; charset=utf-8")
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        if self.path == "/api/activity-feed":
            feed = self.get_activity_feed()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(feed).encode())
            return

