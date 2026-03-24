from pathlib import Path
import re, time

p = Path("app/ezcore_v1/core/engine.py")
txt = p.read_text("utf-8", errors="ignore")

ts = time.strftime("%Y%m%d_%H%M%S")
backup = p.with_name(p.name + ".bak_smart_selector_" + ts)
backup.write_text(txt, encoding="utf-8")
print("BACKUP:", backup)

# ---------- ensure selector knobs exist ----------
m_cfg = re.search(r"^(\s+)self\.cfg\s*=\s*cfg\s*$", txt, flags=re.M)
if not m_cfg:
    raise SystemExit("Could not find self.cfg = cfg")

indent = m_cfg.group(1)

insert_block = f"""
{indent}# --- selector knobs ---
{indent}self.EZ_DISABLE_B = bool(getattr(self, "EZ_DISABLE_B", False))
{indent}self.EZ_B_BENCH_HOURS = int(getattr(self, "EZ_B_BENCH_HOURS", 6))
{indent}self.EZ_B_BENCH_UNTIL_TS = int(getattr(self, "EZ_B_BENCH_UNTIL_TS", 0))
"""

if "EZ_DISABLE_B" not in txt:
    txt = txt[:m_cfg.end()] + insert_block + txt[m_cfg.end():]

# ---------- replace adapt function ----------
fn = re.search(r"\n(\s*)def _maybe_adapt_weights\(self\) -> None:\n", txt)
if not fn:
    raise SystemExit("adapt function not found")

indent_fn = fn.group(1)
body = indent_fn + "    "

start = fn.end()

next_def = re.search(rf"\n{indent_fn}def ", txt[start:])
end = start + next_def.start() if next_def else len(txt)

new_fn = f"""
{indent_fn}def _maybe_adapt_weights(self) -> None:
{body}if not bool(getattr(self, "EZ_ADAPTIVE_WEIGHTS", False)):
{body}    return
{body}try:
{body}    import json, os, time as _time
{body}    path = "logs/ezcore_v1_signal_analytics.json"
{body}    if not os.path.exists(path):
{body}        return
{body}    data = json.load(open(path,"r",encoding="utf-8"))

{body}    strat = data.get("B_VOL_BREAKOUT",{{}})
{body}    b1 = strat.get("BUY",{{}}).get("1h",{{}})
{body}    a1 = data.get("A_TREND_PULLBACK",{{}}).get("BUY",{{}}).get("1h",{{}})

{body}    nb = int(b1.get("n",0))
{body}    na = int(a1.get("n",0))

{body}    b_win = float(b1.get("win_pct",0))
{body}    b_avg = float(b1.get("avg_move_pct",0))

{body}    min_nb = int(getattr(self,"EZ_ADAPT_MIN_N_B_1H",8))
{body}    if nb < min_nb:
{body}        return

{body}    if b_win <= 5 and b_avg <= -0.5:
{body}        self.EZ_DISABLE_B = True
{body}        self.EZ_B_BENCH_UNTIL_TS = int(_time.time()) + int(getattr(self,"EZ_B_BENCH_HOURS",6))*3600

{body}    else:
{body}        if int(_time.time()) >= int(getattr(self,"EZ_B_BENCH_UNTIL_TS",0)):
{body}            self.EZ_DISABLE_B = False
{body}            self.EZ_B_BENCH_UNTIL_TS = 0

{body}except Exception:
{body}    pass
"""

txt = txt[:fn.start()] + new_fn + txt[end:]

p.write_text(txt, encoding="utf-8")
print("PATCH COMPLETE")
