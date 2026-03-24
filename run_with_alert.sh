#!/data/data/com.termux/files/usr/bin/bash

START=$(date +%s)
STAMP=$(date +"%Y%m%d_%H%M%S")
LOGFILE="run_$STAMP.log"

echo "===== RUN STARTED: $(date) ====="
echo "Logging to $LOGFILE"
echo

# Run the command passed to this script
"$@" 2>&1 | tee "$LOGFILE"

END=$(date +%s)
RUNTIME=$((END - START))

echo
echo "===== RUN COMPLETE: $(date) ====="
echo "Runtime: ${RUNTIME} seconds"

# Try Termux notification (if available)
if command -v termux-notification >/dev/null 2>&1; then
  termux-notification --title "Backtest Complete" \
                      --content "Finished in ${RUNTIME}s"
fi

# Try beep (if available)
if command -v termux-beep >/dev/null 2>&1; then
  termux-beep
else
  # Fallback terminal bell
  echo -e "\a"
fi
