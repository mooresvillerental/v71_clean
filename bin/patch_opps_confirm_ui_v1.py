from pathlib import Path
import re

p = Path("ui/opportunities.html")
s = p.read_text("utf-8", errors="replace")

# idempotency marker
MARK = "EZ_CONFIRM_UI_V1"
if MARK in s:
    print("OK ✅ Confirm UI already present")
    raise SystemExit(0)

# 1) Add CSS (insert before </style> if a <style> exists)
css = r"""
/* EZ_CONFIRM_UI_V1 */
#confirmWrap{
  position: sticky;
  top: 0;
  z-index: 50;
  padding: 10px 12px 0;
  background: linear-gradient(to bottom, rgba(11,15,26,.98), rgba(11,15,26,.88));
  border-bottom: 1px solid rgba(30,36,51,.7);
}
#confirmCard{
  display:none;
  border: 2px solid rgba(45,212,191,.9);
  border-radius: 18px;
  padding: 12px;
  background: rgba(15,22,38,.9);
  box-shadow: 0 6px 22px rgba(0,0,0,.35);
}
#confirmTitle{
  font-weight: 900;
  letter-spacing: .3px;
  margin-bottom: 6px;
}
#confirmLine{
  color: rgba(203,213,225,.95);
  font-size: 14px;
  margin-bottom: 10px;
}
#confirmMeta{
  color: rgba(148,163,184,.95);
  font-size: 12px;
  margin-bottom: 10px;
}
#confirmBtns{
  display:flex;
  gap:10px;
  align-items:center;
  flex-wrap:wrap;
}
#btnConfirm{
  background: rgba(45,212,191,.16);
  border: 2px solid rgba(45,212,191,.9);
  color: rgba(203,213,225,1);
  border-radius: 14px;
  padding: 12px 14px;
  font-weight: 900;
}
#btnDismiss{
  background: rgba(148,163,184,.10);
  border: 1px solid rgba(148,163,184,.25);
  color: rgba(203,213,225,.9);
  border-radius: 14px;
  padding: 12px 14px;
  font-weight: 700;
}
#confirmHint{
  color: rgba(148,163,184,.9);
  font-size: 12px;
}
"""

if "</style>" in s:
    s = s.replace("</style>", css + "\n</style>", 1)
else:
    # no style tag found: add one in <head>
    s = re.sub(r"</head>", f"<style>\n{css}\n</style>\n</head>", s, count=1, flags=re.I)

# 2) Add HTML block near top of <body>
html_block = r"""
<!-- EZ_CONFIRM_UI_V1 -->
<div id="confirmWrap">
  <div id="confirmCard">
    <div id="confirmTitle">EZTrader ALERT</div>
    <div id="confirmLine">--</div>
    <div id="confirmMeta">--</div>
    <div id="confirmBtns">
      <button id="btnConfirm">CONFIRM</button>
      <button id="btnDismiss">Dismiss</button>
      <div id="confirmHint">Tip: this pops when the top opportunity is BUY/SELL. HOLD does not alert.</div>
    </div>
  </div>
</div>
"""

# insert right after <body ...> if possible
m = re.search(r"<body[^>]*>", s, flags=re.I)
if not m:
    raise SystemExit("PATCH FAILED: could not find <body> tag to insert confirm UI")
ins_at = m.end()
s = s[:ins_at] + "\n" + html_block + "\n" + s[ins_at:]

# 3) Add JS logic: show confirm card when top opportunity is BUY/SELL
# Find a safe place to inject: before </body> (or at end if missing)
js_block = r"""
<script>
/* EZ_CONFIRM_UI_V1 */
(function(){
  const card = document.getElementById("confirmCard");
  const line = document.getElementById("confirmLine");
  const meta = document.getElementById("confirmMeta");
  const btnC = document.getElementById("btnConfirm");
  const btnD = document.getElementById("btnDismiss");

  // keeps it clean: we only show for BUY/SELL
  let lastKey = null;

  function fmtMoney(x){
    try { return Math.round(parseFloat(x)); } catch(e){ return null; }
  }

  function coinName(sym){
    sym = (sym || "").trim();
    if (!sym) return "UNKNOWN";
    return sym.split("-", 1)[0];
  }

  function hide(){
    if (card) card.style.display = "none";
  }

  function showTop(o){
    if (!card) return;

    const action = String(o.action || "HOLD").toUpperCase();
    if (action !== "BUY" && action !== "SELL"){
      hide();
      return;
    }

    const sym = String(o.symbol || "").toUpperCase();
    const c = coinName(sym);

    const recUsd = fmtMoney(o.recommended_usd);
    const px = o.price;

    // unique-ish key so we don't spam re-showing the same thing
    const key = action + "|" + sym + "|" + String(o.rsi) + "|" + String(o.score);
    if (key === lastKey){
      // still show if already visible
      if (card.style.display !== "block") card.style.display = "block";
      return;
    }
    lastKey = key;

    const moneyPart = (recUsd != null) ? (recUsd + " dollars") : "no amount";
    line.textContent = "EZTrader " + action + " " + moneyPart + " " + c;

    const rsi = (o.rsi == null) ? "--" : String(o.rsi);
    const score = (o.score == null) ? "--" : String(o.score);
    meta.textContent = "symbol=" + sym + "  price=" + px + "  rsi=" + rsi + "  score=" + score + "  reason=" + (o.reason || "--");

    // stash payload for the next step (wiring confirm)
    card.dataset.payload = JSON.stringify(o);

    card.style.display = "block";

    // bring it into view fast
    try { window.scrollTo({top:0, behavior:"smooth"}); } catch(e){ window.scrollTo(0,0); }
    try { if (navigator.vibrate) navigator.vibrate([40, 40, 40]); } catch(e){}
  }

  btnD && btnD.addEventListener("click", function(){
    hide();
  });

  btnC && btnC.addEventListener("click", function(){
    // UI-only for now: we store pending payload so the next step can wire actual confirm + balance tracking safely.
    try {
      const payload = card.dataset.payload || "{}";
      localStorage.setItem("EZ_PENDING_CONFIRM", payload);
      alert("Saved pending confirm. Next step will wire confirm + re-check and show it on screen.");
    } catch(e){
      alert("Could not save pending confirm: " + String(e));
    }
  });

  // Hook into existing refresh loop if it exists:
  // We poll /opportunities lightly without changing your existing logic.
  async function poll(){
    try{
      const u = "/opportunities?interval=5&limit=1&ts=" + Date.now();
      const r = await fetch(u, {cache:"no-store"});
      const j = await r.json();
      const top = (j.top || []);
      if (top.length) showTop(top[0]);
    }catch(e){
      // keep quiet; no spam
    }
  }

  // Start polling. Keep it clean: 6 seconds.
  setInterval(poll, 6000);
  poll();
})();
</script>
"""

if "</body>" in s.lower():
    # insert before last </body>
    s = re.sub(r"</body>", js_block + "\n</body>", s, count=1, flags=re.I)
else:
    s += "\n" + js_block + "\n"

p.write_text(s, "utf-8")
print("OK ✅ Confirm UI added to ui/opportunities.html (EZ_CONFIRM_UI_V1)")
