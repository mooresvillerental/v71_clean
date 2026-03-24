

  // --- OPTION A TOGGLE LOGIC ---
  try{
    // Default: hide advanced on phones
    const isPhone = (screen && Number(screen.width||9999) <= 900);
    if(isPhone) document.body.classList.add("hideAdv");

    const btn = document.getElementById("btnAdvanced");
    function sync(){
      try{
        const hidden = document.body.classList.contains("hideAdv");
        if(btn) btn.textContent = hidden ? "Advanced ▾" : "Advanced ▴";
      }catch(_e){}
    }
    if(btn){
      btn.addEventListener("click", (e)=>{
        e.preventDefault();
        document.body.classList.toggle("hideAdv");
        sync();
      });
      sync();
    }
  }catch(_e){}
  // --- END OPTION A ---


(() => {
  const $ = (id) => document.getElementById(id);

  const dot = $("dot");
  const pillText = $("pillText");
  const testModeBadge = $("testModeBadge");
  const actionTxt = $("actionTxt");
  const reasonTxt = $("reasonTxt");
  const symTxt = $("symTxt");
  const priceTxt = $("priceTxt");
  const livePriceTxt = $("livePriceTxt");
  const enginePriceTxt = $("enginePriceTxt");
  const tsTxt = $("tsTxt");
  const recoTxt = $("recoTxt");
  const bestTimeBar = $("bestTimeBar");
  const bestTimePct = $("bestTimePct");
  const bestTimeLbl = $("bestTimeLbl");

  const msg = $("msg");
  const btnConfirm = $("btnConfirm");
  const btnRefresh = $("btnRefresh");
  const chkAnnounce = $("chkAnnounce");
  const aEnabled = $("aEnabled");
  const aNotify = $("aNotify");
  const aVibrate = $("aVibrate");
  const aSpeak = $("aSpeak");
  const aPoll = $("aPoll");
  const aRepeat = $("aRepeat");
  const aQuiet = $("aQuiet");
  const aQuietStart = $("aQuietStart");
  const aQuietEnd = $("aQuietEnd");
  const aQNotify = $("aQNotify");
  const aQVibrate = $("aQVibrate");
  const aQSpeak = $("aQSpeak");
  const alertsEffective = $("alertsEffective");
  const btnAlertsSave = $("btnAlertsSave");
  const btnAlertsReload = $("btnAlertsReload");

  const chkRepeat = $("chkRepeat");
  const selRepeatSec = $("selRepeatSec");
const inpPct = $("inpPct");
    const inpFeePct = $("inpFeePct");
    const inpFeeUsd = $("inpFeeUsd");
    const btnSave = $("btnSave");
  const selIntelProfile = $("selIntelProfile");
  const intelHeadline = $("intelHeadline");
  const intelSent = $("intelSent");
  const intelTrend = $("intelTrend");
  const balCash = $("balCash");
  const balBtcUsd = $("balBtcUsd");
  const intelProfile = $("intelProfile");

  let lastKey = "";
  let lastActionable = null;
let retryTimer = null;
let recoOk = false;
  let recoAmt = "";
window.__ez_minTradeUsd = window.__ez_minTradeUsd || 0;
window.__ez_suppress_announce = window.__ez_suppress_announce || false;
let lastRecoSpokenKey = "";
let currentSignal = null;
  let repeatTimer = null;
  let repeatLastKey = "";


  function setPill(ok, text){
    dot.classList.remove("ok","bad");
    dot.classList.add(ok ? "ok" : "bad");
    pillText.textContent = text;
  }

  function setMsg(kind, text){
    msg.classList.remove("ok","bad");
    if(!text){ msg.textContent=""; return; }
    msg.classList.add(kind === "ok" ? "ok" : "bad");
    msg.textContent = text;
  }

  function speak(text){
    try{
      // --- MIN_TRADE_SUPPRESSION: hard voice gate ---
      if(window.__ez_suppress_announce) return;
      // --- END hard voice gate ---
      const u = new SpeechSynthesisUtterance(String(text||""));
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    }catch(e){}
  }

  function stopRepeat(){
    try{
      if(repeatTimer){ clearInterval(repeatTimer); repeatTimer = null; }
      repeatLastKey = "";
    }catch(e){}
  }

  function startRepeatIfNeeded(sig){
    try{
      if(!chkAnnounce || !chkAnnounce.checked) return stopRepeat();
      if(!chkRepeat || !chkRepeat.checked) return stopRepeat();
      const a = String((sig && sig.action) || "").toUpperCase();
      if(a !== "BUY" && a !== "SELL") return stopRepeat();

      const sec = selRepeatSec ? Number(selRepeatSec.value || 120) : 120;
      const ms = (isFinite(sec) && sec >= 30) ? Math.round(sec * 1000) : 120000;

      const key = [sig.action, sig.reason, sig.symbol, sig.price, sig.ts].join("|");
      if(repeatLastKey !== key){
        stopRepeat();
        repeatLastKey = key;
      }

      if(!repeatTimer){
        try{
          const shown = (recoTxt && recoTxt.textContent) ? String(recoTxt.textContent).trim() : "";
          const amt = shown.replace(/[^0-9.]/g,"");
          if(amt) speak(`EZTrader repeat alert. ${a}. Recommended amount: ${amt} dollars.`);
          else speak(`EZTrader repeat alert. ${a}.`);
        }catch(e){}

        repeatTimer = setInterval(()=>{
          try{
            const shown = (recoTxt && recoTxt.textContent) ? String(recoTxt.textContent).trim() : "";
            const amt = shown.replace(/[^0-9.]/g,"");
            if(amt) speak(`EZTrader repeat alert. ${a}. Recommended amount: ${amt} dollars.`);
            else speak(`EZTrader repeat alert. ${a}.`);
          }catch(e){}
        }, ms);
      }
    }catch(e){
      stopRepeat();
    }
  }



    async function doConfirm(){
    try{
      setMsg("", "");

      if(!currentSignal) return setMsg("bad", "No signal loaded");

      const action = String(currentSignal.action || "").toUpperCase();
      if(action !== "BUY" && action !== "SELL"){
        return setMsg("bad", "Confirm only works for BUY/SELL");
      }

      const r = await fetch("/confirm", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({action, note:"trade_ui"})
      });

      const j = await r.json().catch(()=> ({}));

      if(r.status === 200 && j && j.ok){
        setMsg("ok", "Confirmed ✓");
        if(chkAnnounce.checked){
  const shown = (recoTxt && recoTxt.textContent) ? String(recoTxt.textContent).trim() : "";
  const amt = shown.replace(/[^0-9.]/g,"");
  if(amt) speak(`EZTrader confirm successful. Recommended amount: ${amt} dollars.`);
  else speak("EZTrader confirm successful.");
}
}else{
        const err = (j && j.error) ? j.error : ("HTTP " + r.status);
        setMsg("bad", "Confirm failed: " + err);
        if(chkAnnounce.checked && !window.__ez_suppress_announce) speak("EZTrader confirm failed.");
      }
    }catch(e){
      setMsg("bad", "Confirm failed");
      if(chkAnnounce.checked && !window.__ez_suppress_announce) speak("EZTrader confirm failed.");
    }
  }

  
    async function loadSettings(){
      try{
        const r = await fetch("/settings?ts=" + Date.now(), {cache:"no-store"});
        const j = await r.json();
      try{
        const mt = (j && j.settings && j.settings.min_trade_usd != null) ? j.settings.min_trade_usd : (j && j.min_trade_usd != null ? j.min_trade_usd : 0);
        window.__ez_minTradeUsd = Number(mt) || 0;
      }catch(_e){}

        if(j && j.ok && j.settings){
          const s = j.settings;
          try{
            if(selIntelProfile){
              const ip = (s.intel_profile || "balanced");
              selIntelProfile.value = String(ip).toLowerCase();
            }
          }catch(_e){}

          inpPct.value = ((Number(s.reco_percent) || 0.05) * 100).toFixed(1);
          inpFeePct.value = ((Number(s.fee_buffer_pct) || 0.0) * 100).toFixed(1);
          inpFeeUsd.value = (Number(s.fee_buffer_usd) || 0).toFixed(2);
        }
      }catch(e){}
    }

    async function saveSettings(){
      try{
        const rp = Math.max(0.1, Math.min(25, Number(inpPct.value || 5))) / 100.0;
        const fp = Math.max(0, Math.min(10, Number(inpFeePct.value || 0))) / 100.0;
        const fu = Math.max(0, Math.min(1000, Number(inpFeeUsd.value || 0)));
        const r = await fetch("/settings", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({reco_mode:"percent", reco_percent: rp, fee_buffer_pct: fp, fee_buffer_usd: fu, intel_profile: (selIntelProfile ? String(selIntelProfile.value||"balanced").toLowerCase() : "balanced")})
        });
        const j = await r.json().catch(()=> ({}));
        if(r.status === 200 && j && j.ok){
          setMsg("ok", "Settings saved ✓");
          if(chkAnnounce.checked && !window.__ez_suppress_announce) speak("EZTrader. Settings saved.");
          await fetchSignal();
        }else{
          setMsg("bad", "Settings save failed");
          if(chkAnnounce.checked && !window.__ez_suppress_announce) speak("EZTrader. Settings save failed.");
        }
      }catch(e){
        setMsg("bad", "Settings save failed");
      }
    }

    
  // --- RESTORE: fetchSignal() using /reco ---
  
  // --- BEST TIME GAUGE LOGIC ---
  let __ez_last_price = null;
  let __ez_last_action = null;
  let __ez_stable_ticks = 0;
  let __ez_last_score = null;

  function clamp(n, a, b){ return Math.max(a, Math.min(b, n)); }

  function computeBestTimeScore(sig, recoUsd){
    let s = 35;

    const a = String((sig && sig.action) || "HOLD").toUpperCase();
    const price = (sig && sig.price != null) ? Number(sig.price) : null;

    // If not actionable, keep it low
    if(a !== "BUY" && a !== "SELL"){
      return 10;
    }

    // recommended amount exists => more confident
    const ru = Number(recoUsd || 0);
    if(isFinite(ru) && ru > 0){
      s += 25;
    }

    // stability: if action holds steady for consecutive ticks, raise score
    if(__ez_last_action === a){
      __ez_stable_ticks += 1;
    }else{
      __ez_stable_ticks = 0;
    }
    __ez_last_action = a;
    s += clamp(__ez_stable_ticks * 8, 0, 24);

    // price momentum: small boost if price moved in favor since last tick
    if(__ez_last_price !== null && price !== null && isFinite(price)){
      const dp = price - __ez_last_price;
      if(a === "BUY" && dp > 0) s += 8;
      else if(a === "SELL" && dp < 0) s += 8;
      else s -= 4;
    }

    // update last price
    if(price !== null && isFinite(price)){
      __ez_last_price = price;
    }

    return clamp(Math.round(s), 0, 100);
  }

  function renderBestTime(score){
    try{
      // Smooth jumps: EMA-ish blend (70% previous, 30% new)
      let s = Number(score);
      if(!isFinite(s)) s = 0;
      if(__ez_last_score === null){
        __ez_last_score = s;
      }else{
        __ez_last_score = (__ez_last_score * 0.70) + (s * 0.30);
      }
      const v = Math.max(0, Math.min(100, Math.round(__ez_last_score)));

      // Color thresholds + label
      let lbl = "Watch";
      let grad = "linear-gradient(90deg,#f44336,#ff9800,#4caf50)";
      if(v < 40){ lbl = "Caution"; grad = "linear-gradient(90deg,#f44336,#f44336)"; }
      else if(v < 70){ lbl = "Watch"; grad = "linear-gradient(90deg,#ff9800,#ff9800)"; }
      else { lbl = "Prime"; grad = "linear-gradient(90deg,#4caf50,#4caf50)"; }

      if(bestTimeBar){
        bestTimeBar.style.width = String(v) + "%";
        bestTimeBar.style.background = grad;
      }
      if(bestTimePct) bestTimePct.textContent = String(v) + "%";
      if(bestTimeLbl) bestTimeLbl.textContent = lbl;
    }catch(e){}
  }
  // --- END BEST TIME GAUGE LOGIC ---


  // --- MARKET INTEL (Fortune-teller Phase 1) ---
  async function fetchIntel(){
    try{
      const j = await fetch("/intel?ts=" + Date.now(), {cache:"no-store"}).then(r=>r.json());
      if(!j || !j.ok) return;
      if(intelHeadline) intelHeadline.textContent = j.headline || "—";
      if(intelSent) intelSent.textContent = j.sentiment || "—";
      if(intelTrend) intelTrend.textContent = j.trend || "—";
      try{
        if(livePriceTxt){
          const lp = Number(j.lp);
          window.__ez_live_lp = lp;
          livePriceTxt.textContent = (isFinite(lp) && lp > 0) ? ("$" + lp.toFixed(2)) : "—";
        }
      }catch(e){}

    }catch(e){}
  }
  
  async function fetchIntelProfile(){
    try{
      const j = await fetch("/settings?ts=" + Date.now(), {cache:"no-store"}).then(r=>r.json());
      const ip = (j && j.settings && j.settings.intel_profile) ? String(j.settings.intel_profile) : "balanced";
      if(intelProfile) intelProfile.textContent = ip;
    }catch(e){}
  }
  // --- TRACKING BALANCES (Manual) ---
  async function fetchBalances(){
    try{
      const j = await fetch("/settings?ts=" + Date.now(), {cache:"no-store"}).then(r=>r.json());
      const s = (j && j.settings) ? j.settings : {};
      const cash = Number(s.manual_cash_usd);
      const btcusd = Number(s.manual_btc_usd);
      if(balCash) balCash.textContent = (isFinite(cash) ? ("$" + cash.toFixed(2)) : "—");
      if(balBtcUsd) balBtcUsd.textContent = (isFinite(btcusd) ? ("$" + btcusd.toFixed(2)) : "—");
    }catch(e){}
  }
  // --- END TRACKING BALANCES ---
  // --- ALERTS (UI) ---
  function _bool01(v){ return String(v||"0").trim()==="1"; }
  function _to01(b){ return b ? "1" : "0"; }

  async function loadAlertsUI(){
    try{
      const j = await fetch("/alerts?ts=" + Date.now(), {cache:"no-store"}).then(r=>r.json());
      if(!j || !j.ok) return;

      const a = j.alerts || {};
      if(aEnabled) aEnabled.checked = _bool01(a.ALERTS_ENABLED);
      if(aNotify) aNotify.checked = _bool01(a.NOTIFY);
      if(aVibrate) aVibrate.checked = _bool01(a.VIBRATE);
      if(aSpeak) aSpeak.checked = _bool01(a.SPEAK);

      if(aPoll) aPoll.value = String(a.POLL_SEC || "5");
      if(aRepeat) aRepeat.value = String(a.REPEAT_SEC || "0");

      if(aQuiet) aQuiet.checked = _bool01(a.QUIET_ENABLED);
      if(aQuietStart) aQuietStart.value = String(a.QUIET_START || "22:00");
      if(aQuietEnd) aQuietEnd.value = String(a.QUIET_END || "07:00");

      if(aQNotify) aQNotify.checked = _bool01(a.QUIET_ALLOW_NOTIFY);
      if(aQVibrate) aQVibrate.checked = _bool01(a.QUIET_ALLOW_VIBRATE);
      if(aQSpeak) aQSpeak.checked = _bool01(a.QUIET_ALLOW_SPEAK);

      try{
        const eff = (j.effective || {});
        const q = j.quiet_active_now ? "Quiet=ON" : "Quiet=OFF";
        const parts = [`Notify=${eff.NOTIFY?"ON":"OFF"}`, `Vibrate=${eff.VIBRATE?"ON":"OFF"}`, `Speak=${eff.SPEAK?"ON":"OFF"}`, q];
        if(alertsEffective) alertsEffective.textContent = parts.join(" • ");
      }catch(e){}
    }catch(e){}
  }

  async function saveAlertsUI(){
    try{
      const payload = {
        ALERTS_ENABLED: _to01(aEnabled && aEnabled.checked),
        NOTIFY: _to01(aNotify && aNotify.checked),
        VIBRATE: _to01(aVibrate && aVibrate.checked),
        SPEAK: _to01(aSpeak && aSpeak.checked),
        POLL_SEC: String(aPoll ? aPoll.value : "5"),
        REPEAT_SEC: String(aRepeat ? aRepeat.value : "0"),
        QUIET_ENABLED: _to01(aQuiet && aQuiet.checked),
        QUIET_START: String(aQuietStart ? aQuietStart.value : "22:00"),
        QUIET_END: String(aQuietEnd ? aQuietEnd.value : "07:00"),
        QUIET_ALLOW_NOTIFY: _to01(aQNotify && aQNotify.checked),
        QUIET_ALLOW_VIBRATE: _to01(aQVibrate && aQVibrate.checked),
        QUIET_ALLOW_SPEAK: _to01(aQSpeak && aQSpeak.checked),
      };

      const r = await fetch("/alerts", {
        method:"POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      }).then(x=>x.json());

      if(r && r.ok){
        setMsg("ok","Alerts saved ✓");
        loadAlertsUI();
      }else{
        setMsg("bad","Alerts save failed: " + String((r && r.error) || "unknown"));
      }
    }catch(e){
      setMsg("bad","Alerts save failed.");
    }
  }
  // --- END ALERTS (UI) ---



  // --- END MARKET INTEL ---

async function fetchSignal(){
    try{
      setPill(true, "Online");
      const j = await fetch("/reco?ts=" + Date.now(), {cache:"no-store"}).then(r=>r.json());
      if(!j || !j.ok){
        setPill(false, "Offline");
        setMsg("bad", "Reco not ok");
        btnConfirm.disabled = true;
        return;
      }

      // Normalize to the old "sig" shape the UI expects
      const sig = {
        action: String(j.action || "HOLD").toUpperCase(),
        reason: j.reason || "",
        symbol: j.symbol || "",
        price: j.price,
        ts: j.ts || ""
      };
      currentSignal = sig;
      startRepeatIfNeeded(sig);

      const a = sig.action;
      actionTxt.textContent = a || "HOLD";
      reasonTxt.textContent = sig.reason ? String(sig.reason) : "—";
      try{
        const rs = String(sig.reason || "");
        if(testModeBadge){
          testModeBadge.style.display = (rs.indexOf("TEST_") >= 0) ? "inline-block" : "none";
        }
      }catch(e){}

      symTxt.textContent = sig.symbol ? String(sig.symbol) : "—";
            try{
        const live = Number(window.__ez_live_lp);
        if(isFinite(live) && live > 0){
          priceTxt.textContent = live.toFixed(2);
        }else{
          priceTxt.textContent = (sig.price != null && isFinite(Number(sig.price))) ? Number(sig.price).toFixed(2) : "—";
        }
      }catch(e){
        priceTxt.textContent = (sig.price != null && isFinite(Number(sig.price))) ? Number(sig.price).toFixed(2) : "—";
      }
      try{
        if(enginePriceTxt){
          const ep = Number(sig.price);
          enginePriceTxt.textContent = (isFinite(ep) && ep > 0) ? ("$" + ep.toFixed(2)) : "—";
        }
      }catch(e){}

      tsTxt.textContent = sig.ts ? String(sig.ts) : "—";

      // Recommended amount (prefer USD)
      try{
        const usd = Number(j.recommended_usd || 0);
        if(isFinite(usd) && usd > 0){
          recoOk = true;
          recoAmt = usd.toFixed(2);
          recoTxt.textContent = "$" + recoAmt;
        }else{
          recoOk = false;
          recoAmt = "";
          recoTxt.textContent = "—";
        }
      }catch(e){
        recoOk = false;
        recoAmt = "";
        recoTxt.textContent = "—";
      }

      // Final confirm gating: MUST be BUY/SELL AND have a real recommended amount
      btnConfirm.disabled = !(recoOk && (a === "BUY" || a === "SELL"));

      setMsg("", "");

      // update Best Time gauge (final, correct placement)
      try{
        const score = computeBestTimeScore(sig, recoAmt);
        renderBestTime(score);
      }catch(e){}

    }catch(e){
      setPill(false, "Offline");
      btnConfirm.disabled = true;
      setMsg("bad", "Reco fetch failed — retrying…");
      setTimeout(fetchSignal, 1200);
    }
  }
  // --- END RESTORE fetchSignal ---

async function diag(){
      try{
        const h = await fetch("/health?ts=" + Date.now(), {cache:"no-store"}).then(r=>r.json());
        console.log("HEALTH", h);
      }catch(e){
      }
    }


    btnRefresh.addEventListener("click", fetchSignal);
  btnConfirm.addEventListener("click", (e) => { e.preventDefault(); doConfirm(); });
    btnSave.addEventListener("click", (e) => { e.preventDefault(); saveSettings(); });

    if(btnAlertsSave) btnAlertsSave.addEventListener("click", ()=>{ saveAlertsUI(); });
    if(btnAlertsReload) btnAlertsReload.addEventListener("click", ()=>{ loadAlertsUI(); });


    if(chkRepeat) chkRepeat.addEventListener("change", ()=>{ if(!chkRepeat.checked) stopRepeat(); else if(currentSignal) startRepeatIfNeeded(currentSignal); });
    if(chkAnnounce) chkAnnounce.addEventListener("change", ()=>{ if(!chkAnnounce.checked) stopRepeat(); else if(currentSignal) startRepeatIfNeeded(currentSignal); });
    if(selRepeatSec) selRepeatSec.addEventListener("change", ()=>{ stopRepeat(); if(currentSignal) startRepeatIfNeeded(currentSignal); });


  // start
  fetchSignal();
  fetchIntel();
  fetchBalances();
  fetchIntelProfile();
  setInterval(fetchSignal, 5000);
  setInterval(fetchIntel, 10000);
  setInterval(loadAlertsUI, 15000);
  setInterval(fetchBalances, 10000);
  setInterval(fetchIntelProfile, 10000);
})();


  // === EZ_POS_PERSIST (server-backed position that survives reloads) ===
  (function(){
    try{
      // Support either mp* ids or pos* ids
      const sideEl  = document.getElementById("mpSide")  || document.getElementById("posSide");
      const qtyEl   = document.getElementById("mpQty")   || document.getElementById("posQty");
      const entryEl = document.getElementById("mpEntry") || document.getElementById("posEntry");
      const statEl  = document.getElementById("mpStatus")|| document.getElementById("posStatus");

      if(!sideEl && !qtyEl && !entryEl){
        // No position UI present; do nothing safely.
        return;
      }

      function _up(s, q, e){
        try{
          const S = String(s||"FLAT").toUpperCase();
          const qq = (q!=null && isFinite(Number(q))) ? Number(q) : null;
          const ee = (e!=null && isFinite(Number(e))) ? Number(e) : null;

          // side select/value
          if(sideEl){
            try{
              // accept "FLAT"/"LONG" (and tolerate other values)
              sideEl.value = (S === "LONG" ? "LONG" : "FLAT");
            }catch(_e){}
          }

          // If flat, clear inputs
          if(S !== "LONG"){
            try{ if(qtyEl) qtyEl.value = ""; }catch(_e){}
            try{ if(entryEl) entryEl.value = ""; }catch(_e){}
            try{ if(statEl) statEl.textContent = "FLAT"; }catch(_e){}
            return;
          }

          // long: set values
          try{ if(qtyEl) qtyEl.value = (qq!=null ? String(qq) : ""); }catch(_e){}
          try{ if(entryEl) entryEl.value = (ee!=null ? String(ee) : ""); }catch(_e){}

          try{
            if(statEl){
              const q2 = (qq!=null ? qq : 0);
              const e2 = (ee!=null ? ee : 0);
              statEl.textContent = `LONG • qty ${q2} • entry $${Number(e2||0).toFixed(2)}`;
            }
          }catch(_e){}
        }catch(_e){}
      }

      async function loadPos(){
        try{
          const j = await fetch("/settings?ts=" + Date.now(), {cache:"no-store"}).then(r=>r.json());
          if(!(j && j.ok && j.settings)) return;
          const st = j.settings || {};
          _up(st.pos_side, st.pos_qty, st.pos_entry_price);
        }catch(_e){}
      }

      async function savePos(){
        try{
          const side = sideEl ? String(sideEl.value||"FLAT").toUpperCase() : "FLAT";
          let qty = qtyEl ? String(qtyEl.value||"").trim() : "";
          let ent = entryEl ? String(entryEl.value||"").trim() : "";

          if(side !== "LONG"){
            qty = ""; ent = "";
          }else{
            // qty: blank allowed; if provided must be >= 0
            if(qty !== ""){
              const qn = Number(qty);
              if(!(isFinite(qn) && qn >= 0)) qty = "";
            }
            // entry: blank allowed; if provided must be > 0
            if(ent !== ""){
              const en = Number(ent);
              if(!(isFinite(en) && en > 0)) ent = "";
            }
          }

          const payload = { pos_side: side, pos_qty: qty, pos_entry_price: ent };

          const r = await fetch("/settings", {
            method:"POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify(payload)
          });

          const j = await r.json().catch(()=> ({}));
          if(!(r.status === 200 && j && j.ok)) return;

          // reload server truth
          await loadPos();
        }catch(_e){}
      }

      let t = null;
      function autosave(){
        try{
          if(t) clearTimeout(t);
          t = setTimeout(()=>{ try{ savePos(); }catch(_e){} }, 450);
        }catch(_e){}
      }

      // Wire listeners
      try{ if(sideEl) sideEl.addEventListener("change", autosave); }catch(_e){}
      try{ if(qtyEl) qtyEl.addEventListener("input", autosave); }catch(_e){}
      try{ if(entryEl) entryEl.addEventListener("input", autosave); }catch(_e){}

      // Boot load
      try{
        if(document.readyState === "loading"){
          document.addEventListener("DOMContentLoaded", loadPos);
        }else{
          loadPos();
        }
      }catch(_e){}
    }catch(_e){}
  })();
  // === END EZ_POS_PERSIST ===

