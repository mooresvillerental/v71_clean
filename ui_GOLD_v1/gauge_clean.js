/* ===== EZTrade Clean Gauge logic =====
   Goal:
   - Needle pinned at bottom center
   - Never dips below horizon (clamp)
   - Works NOW by reading existing DOM text (no need to refactor your fetch code yet)
*/

(function(){
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  function findReadinessScore(){
    // Looks for "READINESS" row that usually contains something like "34/100"
    const all = document.querySelectorAll("div,span,p,td");
    for (const el of all) {
      const t = (el.textContent || "").trim().toUpperCase();
      if (t === "READINESS") {
        // try next siblings
        const p = el.parentElement;
        if (p) {
          const txt = (p.textContent || "");
          const m = txt.match(/READINESS\s+(\d{1,3})\s*\/\s*100/i);
          if (m) return clamp(parseInt(m[1],10),0,100);
        }
      }
    }
    // fallback: search anywhere
    const body = document.body?.textContent || "";
    const m2 = body.match(/READINESS\s+(\d{1,3})\s*\/\s*100/i);
    if (m2) return clamp(parseInt(m2[1],10),0,100);
    return null;
  }

  function findSide(){
    // Try to infer BUY/SELL lean from headline text like "BUY-LEANING", "SELL-LEANING"
    const body = document.body?.textContent || "";
    if (/SELL\s*-\s*LEANING/i.test(body) || /\bSELL-LEANING\b/i.test(body)) return "SELL";
    if (/BUY\s*-\s*LEANING/i.test(body)  || /\bBUY-LEANING\b/i.test(body))  return "BUY";

    // fallback: look for any small pill/tag that contains BUY/SELL
    const pills = document.querySelectorAll(".pill,.tag,.chip,div,span");
    for (const el of pills) {
      const t = (el.textContent || "").toUpperCase();
      if (/\bSELL\b/.test(t)) return "SELL";
      if (/\bBUY\b/.test(t)) return "BUY";
    }
    return "WAIT";
  }

  function findStateWord(){
    const body = document.body?.textContent || "";
    if (/\bOFFLINE\b/i.test(body)) return "OFFLINE";
    if (/\bWAITING\b/i.test(body)) return "WAITING";
    if (/\bPAUSED\b/i.test(body)) return "PAUSED";
    if (/\bNO-TRADE\b/i.test(body)) return "NO-TRADE";
    return null;
  }

  function computeNeedleDeg(){
    // Center (0deg) points straight up.
    // Left is SELL (-deg), right is BUY (+deg).
    // Clamp to keep it above horizon: [-86, +86]
    const state = findStateWord();
    if (state && (state === "OFFLINE" || state === "WAITING" || state === "PAUSED" || state === "NO-TRADE")) {
      return 0;
    }

    const score = findReadinessScore();
    const side = findSide();

    if (score == null) return 0;

    // Convert score to strength: 0..1
    const s = clamp(score/100, 0, 1);

    // max travel inside half gauge
    const maxDeg = 86;

    if (side === "SELL") return -maxDeg * s;
    if (side === "BUY")  return  maxDeg * s;

    // unknown -> center
    return 0;
  }

  function setNeedle(deg){
    const safe = clamp(deg, -86, 86);
    document.documentElement.style.setProperty("--ezNeedleDeg", safe.toFixed(2) + "deg");
  }

  function tick(){
    try{
      setNeedle(computeNeedleDeg());
    }catch(_e){}
  }

  window.EZGaugeClean = {
    tick,
    setNeedle
  };

  // Keep it synced even if other code updates DOM later
  setInterval(tick, 800);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) tick(); });
  setTimeout(tick, 50);
})();
