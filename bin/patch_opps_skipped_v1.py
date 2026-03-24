from pathlib import Path
import re, sys

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_OPPORTUNITIES_ROUTE_V1"
m = re.search(r'^\s*#\s*' + re.escape(MARK) + r'\s*$', s, flags=re.M)
if not m:
    raise SystemExit("PATCH FAILED: could not find opportunities marker")

start = m.start()
sub = s[start:start+12000]

# 1) Ensure we have a skipped list initialized near opps/best creation.
# Look for: best = {}
m_best = re.search(r'^(?P<ind>[ \t]*)best\s*=\s*\{\s*\}\s*$', sub, flags=re.M)
if not m_best:
    raise SystemExit("PATCH FAILED: could not find 'best = {}' inside opportunities block")

ind = m_best.group("ind")
best_line_pos = start + m_best.end()

if "skipped = []" not in sub:
    insert = f"\n{ind}skipped = []  # debug: symbols skipped + why\n"
    s = s[:best_line_pos] + insert + s[best_line_pos:]
    # refresh slice
    sub = s[start:start+12000]

# 2) Add skip reasons in two spots:
#    - missing pair
#    - empty candles
# a) Missing pair: find 'if not pair:' then add skipped append before continue
sub2 = s[start:start+12000]
pat_pair = r'^(?P<ind>[ \t]*)if not pair:\s*\n(?P=ind)\s*continue\s*$'
m_pair = re.search(pat_pair, sub2, flags=re.M)
if m_pair and "skipped.append" not in sub2[m_pair.start():m_pair.end()]:
    ind2 = m_pair.group("ind")
    repl = (
        f"{ind2}if not pair:\n"
        f"{ind2}    skipped.append({{\"symbol\": sym, \"why\": \"no_pair_mapping\"}})\n"
        f"{ind2}    continue"
    )
    sub2 = re.sub(pat_pair, repl, sub2, count=1, flags=re.M)
    s = s[:start] + sub2 + s[start+12000:]

# b) Empty candles: find 'if not candles:' then add skipped append
sub3 = s[start:start+12000]
pat_cand = r'^(?P<ind>[ \t]*)if not candles:\s*\n(?P=ind)\s*continue\s*$'
m_c = re.search(pat_cand, sub3, flags=re.M)
if m_c and "skipped.append" not in sub3[m_c.start():m_c.end()]:
    ind3 = m_c.group("ind")
    repl2 = (
        f"{ind3}if not candles:\n"
        f"{ind3}    skipped.append({{\"symbol\": sym, \"why\": \"no_candles\"}})\n"
        f"{ind3}    continue"
    )
    sub3 = re.sub(pat_cand, repl2, sub3, count=1, flags=re.M)
    s = s[:start] + sub3 + s[start+12000:]

# 3) Add skipped into JSON response near "top": opps[:limit],
sub4 = s[start:start+14000]
pat_resp = r'("top"\s*:\s*opps\[:limit\]\s*,\s*\n)'
m_r = re.search(pat_resp, sub4)
if not m_r:
    raise SystemExit("PATCH FAILED: could not find response line: top: opps[:limit],")

if '"skipped"' not in sub4[m_r.start():m_r.start()+400]:
    inj = m_r.group(1) + '                  "skipped": skipped,\n'
    sub4 = re.sub(pat_resp, lambda _m: inj, sub4, count=1)
    s = s[:start] + sub4 + s[start+14000:]

p.write_text(s, "utf-8")
print("OK ✅ Added opportunities skipped[] debug")
