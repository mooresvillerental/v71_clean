import subprocess
import time
import signal
import sys

PROCS = []

def start(name, cmd):
    print(f"[START] {name}: {' '.join(cmd)}")
    p = subprocess.Popen(cmd)
    PROCS.append((name, p))
    return p

def stop_all():
    print("\n[STOP] shutting down EZTRADER services...")
    for name, p in PROCS:
        try:
            if p.poll() is None:
                print(f"[STOP] {name}")
                p.terminate()
        except Exception:
            pass

    time.sleep(1)

    for name, p in PROCS:
        try:
            if p.poll() is None:
                print(f"[KILL] {name}")
                p.kill()
        except Exception:
            pass

def handle_exit(signum, frame):
    stop_all()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    print("=== EZTRADER LAUNCHER ===")
    print("Starting backend services...\n")

    start("signal_listener", [sys.executable, "signal_listener.py"])
    start("api_server", [sys.executable, "api_server_stdlib.py"])

    print("\nEZTRADER services are running.")
    print("API: http://127.0.0.1:8000/health")
    print("Press Ctrl+C to stop everything.\n")

    while True:
        for name, p in PROCS:
            code = p.poll()
            if code is not None:
                print(f"[EXIT] {name} stopped with code {code}")
                stop_all()
                sys.exit(code or 0)
        time.sleep(1)

if __name__ == "__main__":
    main()
