import re
from pathlib import Path
from statistics import mean

BT = Path("/data/data/com.termux/files/home/v71_clean/backtests")

log_files = sorted(BT.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)

run_header_re = re.compile(r"^=== RUN:\s*(.+?)\s*===$")
label_re = re.compile(r"^LABEL\s*:\s*(.+)$")
metrics_re = re.compile(
    r"METRICS\(off(?P<off>\d+)\): final=(?P<final>[-\d.]+)\s+dd=(?P<dd>[-\d.]+)\s+trades=(?P<trades>\d+)\s+->\s+(?P<status>\w+)"
)
summary_pass_re = re.compile(r"pass_count=(\d+)/(\d+)")
summary_avg_re = re.compile(r"avg_final=([-\d.]+)")
summary_worst_dd_re = re.compile(r"worst_dd=([-\d.]+)")
robust_re = re.compile(r"ROBUST_GATE:\s*(\w+)")

records = []

for log in log_files:
    text = log.read_text(errors="ignore")
    lines = text.splitlines()

    label = None
    run_name = None
    metrics = []
    pass_count = None
    pass_total = None
    avg_final = None
    worst_dd = None
    robust = None

    for line in lines:
        m = run_header_re.search(line.strip())
        if m:
            run_name = m.group(1).strip()

        m = label_re.search(line.strip())
        if m:
            label = m.group(1).strip()

        m = metrics_re.search(line.strip())
        if m:
            metrics.append({
                "offset": int(m.group("off")),
                "final": float(m.group("final")),
                "dd": float(m.group("dd")),
                "trades": int(m.group("trades")),
                "status": m.group("status"),
            })

        m = summary_pass_re.search(line.strip())
        if m:
            pass_count = int(m.group(1))
            pass_total = int(m.group(2))

        m = summary_avg_re.search(line.strip())
        if m:
            avg_final = float(m.group(1))

        m = summary_worst_dd_re.search(line.strip())
        if m:
            worst_dd = float(m.group(1))

        m = robust_re.search(line.strip())
        if m:
            robust = m.group(1)

    if not metrics and not label and not run_name:
        continue

    if avg_final is None and metrics:
        avg_final = mean(x["final"] for x in metrics)
    if worst_dd is None and metrics:
        worst_dd = max(x["dd"] for x in metrics)

    avg_trades = mean(x["trades"] for x in metrics) if metrics else None
    offsets = ",".join(str(x["offset"]) for x in metrics) if metrics else ""

    family = label or run_name or log.name

    records.append({
        "log": log.name,
        "family": family,
        "offsets": offsets,
        "avg_final": avg_final,
        "worst_dd": worst_dd,
        "avg_trades": avg_trades,
        "pass_count": f"{pass_count}/{pass_total}" if pass_count is not None and pass_total is not None else "",
        "robust": robust or "",
    })

def sort_key(r):
    robust_rank = 0 if r["robust"] == "PASS" else 1
    avg_final = -(r["avg_final"] if r["avg_final"] is not None else -999999)
    worst_dd = r["worst_dd"] if r["worst_dd"] is not None else 999999
    return (robust_rank, avg_final, worst_dd)

records.sort(key=sort_key)

print("\n===== EZTRADER BACKTEST LOG SUMMARY =====\n")
print(f"{'FAMILY':40} {'AVG_FINAL':>10} {'WORST_DD':>10} {'AVG_TR':>8} {'PASS':>7} {'ROBUST':>8}  OFFSETS")
print("-" * 100)

for r in records[:40]:
    fam = r["family"][:40]
    avg_final = f"{r['avg_final']:.2f}" if r["avg_final"] is not None else ""
    worst_dd = f"{r['worst_dd']:.2f}" if r["worst_dd"] is not None else ""
    avg_tr = f"{r['avg_trades']:.1f}" if r["avg_trades"] is not None else ""
    print(f"{fam:40} {avg_final:>10} {worst_dd:>10} {avg_tr:>8} {r['pass_count']:>7} {r['robust']:>8}  {r['offsets']}")

print("\nTop regime-related rows:\n")
for r in records:
    text = (r["family"] + " " + r["log"]).lower()
    if "regime" in text:
        avg_final = f"{r['avg_final']:.2f}" if r["avg_final"] is not None else ""
        worst_dd = f"{r['worst_dd']:.2f}" if r["worst_dd"] is not None else ""
        avg_tr = f"{r['avg_trades']:.1f}" if r["avg_trades"] is not None else ""
        print(f"{r['family'][:55]:55} avg_final={avg_final:>8} dd={worst_dd:>8} avg_tr={avg_tr:>8} pass={r['pass_count']:>7} robust={r['robust']}")
print()
