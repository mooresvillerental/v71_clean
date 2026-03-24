from pathlib import Path
import re

p = Path("ui/chart.html")
s = p.read_text("utf-8", errors="replace")

# 1) Make topbar wrap on small screens (prevents controls from "disappearing" off-screen)
s = re.sub(r'(\.topbar\{\s*[^}]*?)display:flex;([^}]*?\})',
           r'\1display:flex;\2',
           s, flags=re.S)

if "flex-wrap:wrap" not in s:
    s = re.sub(r'(\.topbar\{[^}]*?)\}',
               lambda m: m.group(1) + "flex-wrap:wrap;}\n",
               s, count=1, flags=re.S)

# 2) Insert ONE symbol dropdown (USD pairs) into the topbar before interval
if 'id="symbol"' not in s:
    anchor = '<select id="interval">'
    if anchor not in s:
        raise SystemExit("PATCH FAILED: could not find <select id=\"interval\">")
    symbol_block = '''
      <select id="symbol">
        <option value="BTC-USD" selected>BTC-USD</option>
        <option value="ETH-USD">ETH-USD</option>
        <option value="SOL-USD">SOL-USD</option>
        <option value="DOGE-USD">DOGE-USD</option>
      </select>

'''
    s = s.replace(anchor, symbol_block + "      " + anchor, 1)

# 3) Wire JS: symbol select + persistence + add &symbol= to /ohlc and /signals requests
if "EZ_SYMBOL_DROPDOWN_WIRE_V1" not in s:
    # Find a safe insertion point near the top of the script
    m = re.search(r'const\s+dbgEl\s*=\s*document\.getElementById\("dbg"\);\s*', s)
    if not m:
        raise SystemExit("PATCH FAILED: could not find dbgEl init")

    insert = '''
  // EZ_SYMBOL_DROPDOWN_WIRE_V1
  const symbolSel = document.getElementById("symbol");
  function getSymbol(){
    try{
      const u = new URL(location.href);
      const q = (u.searchParams.get("symbol") || "").toUpperCase().trim();
      if (q) return q;
    }catch(e){}
    try{
      const ls = (localStorage.getItem("ez_symbol") || "").toUpperCase().trim();
      if (ls) return ls;
    }catch(e){}
    return "BTC-USD";
  }
  function setSymbolUI(sym){
    if (!symbolSel) return;
    const want = (sym || "BTC-USD").toUpperCase().trim();
    let found = False
    for (const opt of symbolSel.options){
      if ((opt.value||"").toUpperCase() === want){ symbolSel.value = opt.value; found = True; break; }
    }
    if (!found){ symbolSel.value = "BTC-USD"; }
  }
'''
    # Python True/False fix in the inserted JS
    insert = insert.replace("False", "false").replace("True", "true")

    s = s[:m.end()] + insert + s[m.end():]

    # Add symbol init after chart init (right after it confirms LightweightCharts loaded is fine)
    # We'll hook right after `const container = document.getElementById("chart");`
    m2 = re.search(r'const\s+container\s*=\s*document\.getElementById\("chart"\);\s*', s)
    if not m2:
        raise SystemExit("PATCH FAILED: could not find container init")
    init_block = '''
    // init symbol dropdown from URL/localStorage
    try{
      if (symbolSel){
        setSymbolUI(getSymbol());
        symbolSel.addEventListener("change", () => {
          try{ localStorage.setItem("ez_symbol", symbolSel.value); }catch(e){}
          try{ loadOHLC(); loadSignals(); }catch(e){}
        });
      }
    }catch(e){}
'''
    s = s[:m2.end()] + init_block + s[m2.end():]

# 4) Patch /ohlc and /signals fetch URLs to include symbol=
def patch_url(fn_name, path_token):
    global s
    # Replace the first occurrence inside each loader
    pat = rf'(async function {fn_name}\(\)\{{[\s\S]*?jget\(")({re.escape(path_token)}\?interval="\+encodeURIComponent\(iv\)\+"\&ts="\+Date\.now\(\))'
    m = re.search(pat, s)
    if not m:
        return False
    # Inject &symbol=
    repl = r'\1' + path_token + r'?interval="+encodeURIComponent(iv)+"&symbol="+encodeURIComponent((symbolSel&&symbolSel.value)||"BTC-USD")+"&ts="+Date.now()'
    s = re.sub(pat, repl, s, count=1)
    return True

ok1 = patch_url("loadOHLC", "/ohlc")
ok2 = patch_url("loadSignals", "/signals")

if not ok1 or not ok2:
    # fallback: simple string replacements if the structure differs slightly
    s = s.replace('"/ohlc?interval="+encodeURIComponent(iv)+"&ts="+Date.now()',
                  '"/ohlc?interval="+encodeURIComponent(iv)+"&symbol="+encodeURIComponent((symbolSel&&symbolSel.value)||"BTC-USD")+"&ts="+Date.now()')
    s = s.replace('"/signals?interval="+encodeURIComponent(iv)+"&ts="+Date.now()',
                  '"/signals?interval="+encodeURIComponent(iv)+"&symbol="+encodeURIComponent((symbolSel&&symbolSel.value)||"BTC-USD")+"&ts="+Date.now()')

p.write_text(s, "utf-8")
print("OK ✅ Added ONE USD symbol dropdown + wired symbol into /ohlc and /signals.")
