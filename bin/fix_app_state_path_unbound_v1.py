from pathlib import Path
import re, sys

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

m_get = re.search(r'^(\s*)def do_GET\(self\):\s*$', s, flags=re.M)
m_post = re.search(r'^\s*def do_POST\(self\):\s*$', s, flags=re.M)
if not m_get or not m_post or m_post.start() <= m_get.start():
    raise SystemExit("FIX FAILED: could not locate do_GET/do_POST boundaries")

get_indent = m_get.group(1)           # indentation of def do_GET
body_indent = get_indent + "    "     # indentation inside do_GET body

head = s[:m_get.end()]
mid  = s[m_get.end():m_post.start()]
tail = s[m_post.start():]

# A) rename any assignment to APP_STATE_PATH inside do_GET body ONLY
# (this is what causes UnboundLocalError)
mid2 = re.sub(r'(?m)^(\s*)APP_STATE_PATH(\s*)=', r'\1_APP_STATE_PATH\2=', mid)

# B) ensure "global APP_STATE_PATH" exists right after def do_GET(self):
# Insert after the very first newline in mid2 (start of body)
if re.search(r'(?m)^\s*global\s+APP_STATE_PATH\s*$', mid2) is None:
    # find first linebreak
    nl = mid2.find("\n")
    if nl == -1:
        raise SystemExit("FIX FAILED: unexpected do_GET body format")
    insert = "\n" + body_indent + "global APP_STATE_PATH\n"
    mid2 = mid2[:nl+1] + body_indent + "global APP_STATE_PATH\n" + mid2[nl+1:]

# If we changed anything, write back
if mid2 == mid and head + mid + tail == s:
    print("No changes needed (no APP_STATE_PATH assignment found in do_GET).")
else:
    s2 = head + mid2 + tail
    p.write_text(s2, "utf-8")
    print("OK ✅ Fixed APP_STATE_PATH scoping inside do_GET")

