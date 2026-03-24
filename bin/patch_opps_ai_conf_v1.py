from pathlib import Path
import re, sys, subprocess

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_OPPORTUNITIES_ROUTE_V1"
m = re.search(r'^\s*#\s*' + re.escape(MARK) + r'\s*$', s, flags=re.M)
if not m:
    print("PATCH FAILED: opportunities marker not found:", MARK)
    sys.exit(1)

# Delimit the opportunities block up to the chart anchor
anchor = re.search(r'^\s*# --- Chart endpoint: live price \(read-only\) ---\s*$', s[m.end():], flags=re.M)
if not anchor:
    print("PATCH FAILED: could not find chart anchor after opportunities marker")
    sys.exit(1)

start = m.end()
end = m.end() + anchor.start()

sub = s[start:end]

if "base_confidence" in sub and "ai_confidence" in sub and "ai_explanation" in sub:
    print("Already patched ✅ (AI confidence fields already present)")
    sys.exit(0)

# Find: line "o = {"
mo = re.search(r'^(?P<ind>[ \t]*)o\s*=\s*\{\s*$', sub, flags=re.M)
if not mo:
    print("PATCH FAILED: could not find `o = {` inside opportunities block")
    sys.exit(1)

ind = mo.group("ind")

compute_block = (
f"{ind}# --- confidence (0-100) + AI overlay (read-only) ---\n"
f"{ind}base_conf = 0\n"
f"{ind}try:\n"
f"{ind}    if action in ('BUY','SELL'):\n"
f"{ind}        base_conf = int(max(0, min(100, round(float(score) * 6.0))))\n"
f"{ind}except Exception:\n"
f"{ind}    base_conf = 0\n"
f"{ind}\n"
f"{ind}features = {{}}\n"
f"{ind}try:\n"
f"{ind}    win = closes[-30:] if (isinstance(closes, list) and len(closes) >= 30) else list(closes or [])\n"
f"{ind}    if win and len(win) >= 2:\n"
f"{ind}        base0 = float(win[0])\n"
f"{ind}        lastf = float(win[-1])\n"
f"{ind}        if base0:\n"
f"{ind}            features['trend_slope_pct'] = (lastf - base0) / base0 * 100.0\n"
f"{ind}        hi = max(win)\n"
f"{ind}        lo = min(win)\n"
f"{ind}        if lastf:\n"
f"{ind}            features['vol_pct'] = (float(hi) - float(lo)) / float(lastf) * 100.0\n"
f"{ind}        # simple peak-risk proxy (placeholder for your peak watchers)\n"
f"{ind}        if action == 'SELL' and hi:\n"
f"{ind}            features['peak_risk'] = (float(lastf) / float(hi)) * 100.0\n"
f"{ind}        elif action == 'BUY' and lastf:\n"
f"{ind}            features['peak_risk'] = (float(lo) / float(lastf)) * 100.0\n"
f"{ind}except Exception:\n"
f"{ind}    features = {{}}\n"
f"{ind}\n"
f"{ind}ai_conf = base_conf\n"
f"{ind}ai_delta = 0\n"
f"{ind}ai_expl = 'AI overlay inactive.'\n"
f"{ind}try:\n"
f"{ind}    from app.ai_advisor import ai_adjust_confidence\n"
f"{ind}    adv = ai_adjust_confidence(symbol=sym, action=action, base_confidence=base_conf, features=features)\n"
f"{ind}    ai_conf = int(getattr(adv, 'ai_confidence', base_conf))\n"
f"{ind}    ai_delta = int(getattr(adv, 'delta', 0))\n"
f"{ind}    ai_expl = str(getattr(adv, 'explanation', '')).strip() or ai_expl\n"
f"{ind}except Exception:\n"
f"{ind}    pass\n"
)

# Insert compute block just before "o = {"
sub = sub[:mo.start()] + compute_block + "\n" + sub[mo.start():]

# Add keys into dict right after "reason": reason,
def inject_after_reason(match):
    return (
        match.group(1)
        + f"{ind}    'base_confidence': int(base_conf),\n"
        + f"{ind}    'ai_confidence': int(ai_conf),\n"
        + f"{ind}    'ai_delta': int(ai_delta),\n"
        + f"{ind}    'ai_explanation': ai_expl,\n"
    )

pat_reason = re.compile(rf"^({re.escape(ind)}\s*'reason'\s*:\s*reason\s*,\s*\n)", re.M)
if not pat_reason.search(sub):
    # also support double-quote style if your dict uses it
    pat_reason = re.compile(rf'^({re.escape(ind)}\s*"reason"\s*:\s*reason\s*,\s*\n)', re.M)

if not pat_reason.search(sub):
    print('PATCH FAILED: could not find reason line inside "o = {...}" to anchor injection')
    sys.exit(1)

sub = pat_reason.sub(inject_after_reason, sub, count=1)

# Write back
s2 = s[:start] + sub + s[end:]
p.write_text(s2, "utf-8")
print("OK ✅ /opportunities now returns base_confidence + ai_confidence + ai_explanation")
