import subprocess
import threading
import time

def run_watcher():
    subprocess.run(["python", "ezmarketing_site/ezmarketing_watcher.py"])

def run_daily():
    while True:
        subprocess.run(["python", "ezmarketing_site/daily_summary.py"])
        time.sleep(86400)  # run once per day

if __name__ == "__main__":
    print("[EZMarketing] Starting automation system...")

    t1 = threading.Thread(target=run_watcher)
    t2 = threading.Thread(target=run_daily)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
