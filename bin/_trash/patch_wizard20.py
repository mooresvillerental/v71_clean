import re, sys

PATH = "settings_wizard.py"

with open(PATH, "r", encoding="utf-8") as f:
    s = f.read()

# Find the end of option 19 block (your file shows: if choice == "19": ctrl = interactive_apply_preset(ctrl1) continue)
m = re.search(r'if\s+choice\s*==\s*"19"\s*:\s*[\s\S]*?\n\s*continue\s*\n', s)
if not m:
    raise SystemExit("Patch failed: couldn't find the choice == \"19\" block. (File differs from expected.)")

insert_at = m.end()

# If option 20 already exists, remove it first to avoid duplicates / bad indentation
s = re.sub(r'\n\s*if\s+choice\s*==\s*"20"\s*:[\s\S]*?\n\s*continue\s*\n', "\n", s)

block = r'''
    if choice == "20":
        # Set existing BTC holdings + cost basis (one-time)
        state = _load_state()

        print("\nSet Existing BTC (for tracking profits from BEFORE using this app)")
        ans = input("Did you own BTC before using this app? (y/N): ").strip().lower()
        if ans not in ("y", "yes"):
            print("Skipped.")
            continue

        btc_qty = _get_float("BTC amount owned: ", 0.0)
        if btc_qty <= 0:
            print("No BTC entered. Skipped.")
            continue

        avg_price = _get_float("Average buy price per BTC (USD): ", 0.0)
        if avg_price <= 0:
            print("Invalid price. Skipped.")
            continue

        symbol = "BTC-USD"

        # Initialize holdings
        holdings = state.get("holdings", {})
        if not isinstance(holdings, dict):
            holdings = {}
        holdings[symbol] = float(btc_qty)
        state["holdings"] = holdings

        # Initialize cost basis (matches v70 expectations)
        cost_basis = state.get("cost_basis", {})
        if not isinstance(cost_basis, dict):
            cost_basis = {}
        cost_basis[symbol] = {
            "total_cost_usd": float(btc_qty) * float(avg_price),
            "total_qty": float(btc_qty),
        }
        state["cost_basis"] = cost_basis

        _save_state(state)

        print("\nSaved:")
        print(f" BTC owned: {btc_qty:.8f}")
        print(f" Avg entry: ${avg_price:,.2f}")
        print(f" Total cost: ${btc_qty * avg_price:,.2f}")
        print("Cost basis initialized successfully.")
        continue

'''

s2 = s[:insert_at] + block + s[insert_at:]

with open(PATH, "w", encoding="utf-8") as f:
    f.write(s2)

print("✅ Patched Option 20 into", PATH)
