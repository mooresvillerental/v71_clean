from pathlib import Path
import re

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

# Remove the broken sizing block that starts with _hold_qty
s = re.sub(
    r'\n\s*# --- sizing / holdings \(read-only\) ---.*?(_rec_usd = float\(_hold_qty\) \* float\(last\)\n)',
    '\n',
    s,
    flags=re.S
)

# Also remove any inserted reco fields inside the opp dict
s = re.sub(
    r'\n\s*"holding_qty":.*?\n\s*"recommended_qty":.*?\n',
    '\n',
    s,
    flags=re.S
)

p.write_text(s, "utf-8")
print("OK ✅ Removed broken sizing/reco code")
