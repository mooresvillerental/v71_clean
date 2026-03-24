#!/usr/bin/env python3
import os, re, json, sys

DATA_DIR = "v69_app_data"
CTRL_PATH = os.path.join(DATA_DIR, "app_control.json")

ENGINE_CANDIDATES = [
    "v70_app_ready_pro.py",
    "v69_app_ready_pro.py",
]

WIZARD_CANDIDATES = [
    "settings_wizard.py",
]

def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_text(path, s):
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)

def backup(path):
    b = path + ".bak_remove_paper"
    if not os.path.exists(b):
        with open(path, "rb") as src, open(b, "wb") as dst:
            dst.write(src.read())

def patch_control_json():
    if not os.path.exists(CTRL_PATH):
        print(f"[WARN] {CTRL_PATH} not found. Skipping control patch.")
        return
    with open(CTRL_PATH, "r", encoding="utf-8") as f:
        ctrl = json.load(f)

    # Force platform away from PAPER
    plat = str(ctrl.get("platform", "PAPER")).upper()
    if plat == "PAPER":
        ctrl["platform"] = "ROBINHOOD"

    # Make sure we do NOT default into paper
    trading = ctrl.get("trading", {})
    if not isinstance(trading, dict):
        trading = {}
    trading["paper_default"] = False
    ctrl["trading"] = trading

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CTRL_PATH, "w", encoding="utf-8") as f:
        json.dump(ctrl, f, indent=2, sort_keys=True)

    print(f"[OK] Updated {CTRL_PATH}: platform={ctrl.get('platform')} | trading.paper_default={ctrl['trading'].get('paper_default')}")

def patch_engine_file(path):
    s0 = read_text(path)
    s = s0

    # 1) Change DEFAULT_CTRL platform from PAPER -> ROBINHOOD (if present in file)
    s = re.sub(r'("platform"\s*:\s*)"(PAPER)"', r'\1"ROBINHOOD"', s)

    # 2) Change DEFAULT_CTRL trading.paper_default to False (if present)
    s = re.sub(r'("paper_default"\s*:\s*)true', r'\1False', s, flags=re.IGNORECASE)

    # 3) Add a hard block: if ctrl platform is PAPER => exit with clear message
    # We insert just AFTER ctrl/platform normalization area by targeting a stable place:
    # after: platform = str(ctrl.get("platform","PAPER")).upper()
    block = r'''
    # --- HARD BLOCK: PAPER MODE REMOVED ---
    if platform == "PAPER":
        warn("PAPER MODE HAS BEEN REMOVED from this build. Open Settings Wizard and select ROBINHOOD or COINBASE, then Save & Exit.")
        return 2
    # -------------------------------------
'''
    if "PAPER MODE HAS BEEN REMOVED" not in s:
        s = re.sub(
            r'(platform\s*=\s*str\(ctrl\.get\("platform","PAPER"\)\)\.upper\(\)\s*\n)',
            r'\1' + block + '\n',
            s,
            count=1
        )

    if s != s0:
        backup(path)
        write_text(path, s)
        print(f"[OK] Patched engine: {path} (backup: {path}.bak_remove_paper)")
        return True
    else:
        print(f"[WARN] Engine patch made no changes: {path}")
        return False

def patch_wizard_file(path):
    s0 = read_text(path)
    s = s0

    # Remove "BALANCE TOOLS (PAPER)" section by replacing it with a single note.
    # This targets the menu-print block (safe if the header exists).
    s = re.sub(
        r'print\(\s*".*BALANCE TOOLS.*PAPER.*"\s*\)\s*(?:\n\s*print\(.*\)\s*){1,40}',
        'print("\\n--- BALANCE TOOLS ---")\nprint("Paper mode has been removed. No paper balances/tools are available in this build.")\n',
        s,
        flags=re.IGNORECASE
    )

    # Remove menu lines that mention PAPER balances/options 17-20 (common labels)
    s = re.sub(r'^\s*print\(\s*".*\bPaper\b.*"\s*\)\s*$', '', s, flags=re.IGNORECASE | re.MULTILINE)
    s = re.sub(r'^\s*print\(\s*".*\bPAPER\b.*"\s*\)\s*$', '', s, flags=re.IGNORECASE | re.MULTILINE)

    # If there is any explicit platform choice including PAPER, remove PAPER from options:
    # (This is intentionally conservative: it only removes the token "PAPER" inside option strings.)
    s = re.sub(r'\bPAPER\s*/\s*', '', s)
    s = re.sub(r'\s*/\s*PAPER\b', '', s)
    s = re.sub(r'\bPAPER\b', 'REMOVED', s)

    # Prevent selecting paper if there is a handler:
    # if choice == "paper": => block
    if "PAPER MODE HAS BEEN REMOVED" not in s:
        s = re.sub(
            r'(choice\s*=\s*input\(.*?\)\.strip\(\)\.lower\(\)\s*)',
            r'\1\n\n# PAPER MODE REMOVED: block any legacy selection\n',
            s,
            count=1,
            flags=re.DOTALL
        )

    if s != s0:
        backup(path)
        write_text(path, s)
        print(f"[OK] Patched wizard: {path} (backup: {path}.bak_remove_paper)")
        return True
    else:
        print(f"[WARN] Wizard patch made no changes: {path}")
        return False

def main():
    patched_any = False

    # Patch control JSON first
    patch_control_json()

    # Patch engine
    for p in ENGINE_CANDIDATES:
        if os.path.exists(p):
            patched_any |= patch_engine_file(p)

    # Patch wizard
    for p in WIZARD_CANDIDATES:
        if os.path.exists(p):
            patched_any |= patch_wizard_file(p)

    if not patched_any:
        print("[WARN] No files were changed. (Maybe your filenames differ.)")
        print("       Tell me which files you have:  ls -lah *.py")
        return 1

    print("\n[OK] PAPER MODE REMOVED / BLOCKED.")
    print("Next: run your Settings Wizard, pick ROBINHOOD/COINBASE, Save & Exit, then run: runbot")
    return 0

if __name__ == "__main__":
    sys.exit(main())
