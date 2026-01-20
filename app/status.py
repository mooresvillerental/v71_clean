import os, glob, subprocess, time

def _tail(path, n=30):
    try:
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()[-n:]
        return "".join(lines)
    except Exception as e:
        return f"(could not read {path}: {e})"

def get_status():
    home = os.path.expanduser("~")
    base = os.path.join(home, "v70_host")
    pidfile = os.path.join(base, "run", "server.pid")
    logs_glob = os.path.join(base, "logs", "server_*.log")
    watchdog_log = os.path.join(base, "logs", "watchdog.log")

    server_pid = None
    if os.path.isfile(pidfile):
        try:
            server_pid = int(open(pidfile, "r").read().strip())
        except Exception:
            server_pid = None

    server_alive = False
    if server_pid:
        try:
            os.kill(server_pid, 0)
            server_alive = True
        except Exception:
            server_alive = False

    # Find latest server log
    server_logs = sorted(glob.glob(logs_glob), key=lambda p: os.path.getmtime(p), reverse=True)
    last_server_log = server_logs[0] if server_logs else None

    # Check watchdog process via pgrep (best effort)
    watchdog_pids = []
    try:
        out = subprocess.check_output(["pgrep", "-f", "watch_server.sh"], stderr=subprocess.DEVNULL).decode().strip()
        watchdog_pids = [int(x) for x in out.splitlines() if x.strip().isdigit()]
    except Exception:
        watchdog_pids = []

    return {
        "ok": True,
        "ts": int(time.time()),
        "server": {
            "pid": server_pid,
            "alive": server_alive,
            "last_log": last_server_log,
            "last_log_tail": _tail(last_server_log, 30) if last_server_log else "(no server logs yet)",
        },
        "watchdog": {
            "pids": watchdog_pids,
            "log_tail": _tail(watchdog_log, 30),
        },
    }
