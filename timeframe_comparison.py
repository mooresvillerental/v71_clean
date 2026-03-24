
import os
import json
import subprocess

tests = [
    ("15m_engine", "EZ_USE_1H_TREND=0"),
    ("1h_bias_engine", "EZ_USE_1H_TREND=1"),
]

print("=== TIMEFRAME COMPARISON ===")

for name, envflag in tests:

    os.system("rm -f app/ezcore_v1_state.json logs/ezcore_v1.log logs/ezcore_v1_events.jsonl")

    cmd = f"{envflag} EZ_SILENT_TESTS=1 python backtest_long_run.py"
    subprocess.run(cmd, shell=True)

    print("\n---", name, "---")

    subprocess.run("python perf_report.py", shell=True)

print("\n=== TEST COMPLETE ===")
