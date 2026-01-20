from pathlib import Path
import re, time

p = Path("ui/index.html")
if not p.exists():
    raise SystemExit("ui/index.html not found")

src = p.read_text(encoding="utf-8", errors="ignore")
bak = p.with_suffix(p.suffix + f".bak_confirm_v2_{int(time.time())}")
bak.write_text(src, encoding="utf-8")

# 1) Remove prior injected confirm bind blocks (any variant we may have added)
src2 = re.sub(r'\s*<script[^>]*id=["\']POST_CONFIRM_FIX["\'][\s\S]*?</script>\s*', "\n", src, flags=re.I)
src2 = re.sub(r'\s*<script[^>]*id=["\']EZ_CONFIRM_BIND_V2["\'][\s\S]*?</script>\s*', "\n", src2, flags=re.I)

# 2) Remove the debug pill DIV (EZ: loading...)
src2 = re.sub(r'\s*<div[^>]*id=["\']ez-pill["\'][\s\S]*?</div>\s*', "\n", src2, flags=re.I)

# 3) Remove obvious stray "EZ: loading..." literals
src2 = src2.replace("EZ: loading...", "")
src2 = src2.replace("EZ: loading..", "")
src2 = src2.replace("EZ: loading.", "")

inject = r"""
<script id="EZ_CONFIRM_BIND_V2">
(() => {
  function speak(msg){
    try {
      // If app already has a speak function, use it
      if (window.ezSpeak) return window.ezSpeak(msg);
      if (window.EZ && typeof window.EZ.speak === "function") return window.EZ.speak(msg);
      if (window.speechSynthesis) {
        const u = new SpeechSynthesisUtterance(String(msg));
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(u);
        return;
      }
    } catch(e) {}
    // Last resort (silent)
    console.log("SAY:", msg);
  }

  function findConfirmButton(){
    // Prefer explicit class if present
    let btn = document.querySelector("button.confirm, .confirm button");
    if (btn) return btn;

    // Otherwise find by text content
    const buttons = Array.from(document.querySelectorAll("button"));
    return buttons.find(b => (b.textContent || "").trim().toUpperCase() === "CONFIRM") || null;
  }

  function setConfirmVisible(btn, visible){
    if (!btn) return;
    btn.style.display = visible ? "" : "none";
    btn.disabled = !visible;
    btn.setAttribute("aria-disabled", (!visible).toString());
  }

  function normalizeAction(v){
    const s = String(v || "").trim().toUpperCase();
    if (s === "BUY" || s === "SELL" || s === "HOLD" || s === "NO_TRADE") return s;
    return s;
  }

  function extractAction(payload){
    // /signal currently returns either:
    // - { signal: { action: "HOLD"... } }
    // - { pending_trade: { side: "BUY"... }, bias: "BUY", ... }
    // We'll treat BUY/SELL only as confirmable.
    let a =
      (payload && payload.signal && payload.signal.action) ||
      (payload && payload.pending_trade && payload.pending_trade.side) ||
      (payload && payload.bias) ||
      (payload && payload.action);

    a = normalizeAction(a);

    // If UI says NO_TRADE, treat as HOLD
    if (a === "NO_TRADE") a = "HOLD";
    return a || "HOLD";
  }

  async function fetchSignal(){
    const url = "/signal?ts=" + Math.floor(Date.now()/1000);
    const r = await fetch(url, { cache: "no-store" });
    const j = await r.json();
    window.__EZ_LAST_SIGNAL_PAYLOAD = j;
    window.__EZ_LAST_ACTION = extractAction(j);
    return j;
  }

  async function doConfirm(){
    const action = normalizeAction(window.__EZ_LAST_ACTION);
    if (action !== "BUY" && action !== "SELL"){
      speak("Nothing to confirm.");
      return { ok:false, error:"no_confirmable_action", action };
    }
    const body = JSON.stringify({ action, ts: Math.floor(Date.now()/1000) });
    const r = await fetch("/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body
    });
    const j = await r.json();

    if (j && j.ok){
      speak("Confirmed " + action + ".");
    } else {
      const e = (j && j.error) ? j.error : "confirm_failed";
      speak("Easy trader confirm failed.");
      console.log("CONFIRM FAIL:", j);
    }
    return j;
  }

  function cleanupDebugArtifacts(){
    // remove any leftover debug pill nodes if present
    const pill = document.getElementById("ez-pill");
    if (pill) pill.remove();

    // remove any stray inline text nodes containing "EZ:" (common debug remnants)
    try {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const kill = [];
      while (walker.nextNode()){
        const t = walker.currentNode;
        if (t && t.nodeValue && t.nodeValue.includes("EZ:")) kill.push(t);
      }
      kill.forEach(t => t.nodeValue = t.nodeValue.replace(/EZ:\s*.*?/g, ""));
    } catch(e) {}
  }

  function bindConfirm(){
    const btn = findConfirmButton();
    if (!btn) return null;
    if (btn.dataset.ezBound === "1") return btn;
    btn.dataset.ezBound = "1";

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      doConfirm().catch(err => {
        console.log("CONFIRM EXC:", err);
        speak("Easy trader confirm failed.");
      });
    }, { passive: false });

    return btn;
  }

  async function tick(){
    cleanupDebugArtifacts();

    const btn = bindConfirm();
    try {
      const sig = await fetchSignal();
      const action = normalizeAction(window.__EZ_LAST_ACTION);
      const confirmable = (action === "BUY" || action === "SELL");
      setConfirmVisible(btn, confirmable);

      // Optional: if you want visible feedback in console
      // console.log("ACTION:", action, "confirmable:", confirmable, sig);

    } catch (e) {
      // If /signal fails, hide confirm (safest)
      const btn2 = findConfirmButton();
      setConfirmVisible(btn2, False);
      console.log("SIGNAL ERROR:", e);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    // First run immediately
    tick();

    // Keep in sync with server (don’t fight any existing poll; just light-touch)
    if (!window.__EZ_CONFIRM_TIMER){
      window.__EZ_CONFIRM_TIMER = setInterval(tick, 1500);
    }
  });
})();
</script>
"""

# 4) Insert injection before </body> (case-insensitive)
if re.search(r"</body\s*>", src2, flags=re.I):
    src2 = re.sub(r"</body\s*>", inject + "\n</body>", src2, flags=re.I, count=1)
else:
    src2 += "\n" + inject + "\n"

p.write_text(src2, encoding="utf-8")
print(f"✅ Patched ui/index.html")
print(f"✅ Backup saved: {bak}")
