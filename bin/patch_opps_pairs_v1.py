from pathlib import Path
import re, sys

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_OPPORTUNITIES_ROUTE_V1"
m = re.search(r'^\s*#\s*' + re.escape(MARK) + r'\s*$', s, flags=re.M)
if not m:
    raise SystemExit("PATCH FAILED: could not find # EZ_OPPORTUNITIES_ROUTE_V1")

# Work only inside the opportunities block chunk (from marker forward a bit)
start = m.start()
chunk = s[start:start+9000]

# Find the PAIR dict in that chunk
m_pair = re.search(r'^(?P<ind>[ \t]*)PAIR\s*=\s*\{\s*$', chunk, flags=re.M)
if not m_pair:
    raise SystemExit("PATCH FAILED: could not find 'PAIR = {' inside opportunities block")

ind = m_pair.group("ind")

# Replace everything from "PAIR = {" up to its closing "}" at same indentation
# (first closing brace line that starts with same indentation and a "}")
m_close = re.search(r'^' + re.escape(ind) + r'\}\s*$', chunk[m_pair.end():], flags=re.M)
if not m_close:
    raise SystemExit("PATCH FAILED: could not find closing '}' for PAIR dict")

pair_start = start + m_pair.start()
pair_open_end = start + m_pair.end()
pair_close_end = pair_open_end + m_close.end()

new_pair = (
    f"{ind}PAIR = {{\n"
    f'{ind}    "BTC-USD": "XBTUSD",\n'
    f'{ind}    "ETH-USD": "ETHUSD",\n'
    f'{ind}    "SOL-USD": "SOLUSD",\n'
    f'{ind}    "XRP-USD": "XRPUSD",\n'
    f'{ind}    "DOGE-USD": "DOGEUSD",\n'
    f'{ind}    "ADA-USD": "ADAUSD",\n'
    f'{ind}    "AVAX-USD": "AVAXUSD",\n'
    f'{ind}    "LINK-USD": "LINKUSD",\n'
    f'{ind}    "MATIC-USD": "MATICUSD",\n'
    f'{ind}    "DOT-USD": "DOTUSD",\n'
    f'{ind}    "LTC-USD": "LTCUSD",\n'
    f'{ind}    "BCH-USD": "BCHUSD",\n'
    f'{ind}    "UNI-USD": "UNIUSD",\n'
    f'{ind}    "AAVE-USD": "AAVEUSD",\n'
    f'{ind}    "ATOM-USD": "ATOMUSD",\n'
    f"{ind}}}\n"
)

s2 = s[:pair_start] + new_pair + s[pair_close_end:]
p.write_text(s2, "utf-8")
print("OK ✅ Opportunities PAIR map expanded to 15 symbols")
