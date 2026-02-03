#!/bin/bash
# Launch v6 bot fully detached from parent process
# Uses setsid + nohup to survive parent process death
# This prevents the bot from being killed when exec sessions are cleaned up

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DURATION_MIN=${1:-480}
LOG_FILE="/tmp/v6_watchdog.log"
PID_FILE="/tmp/rt_v6_pid.txt"
WATCHDOG_PID_FILE="/tmp/rt_v6_watchdog_pid.txt"

# Kill any existing v6 processes
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    kill "$OLD_PID" 2>/dev/null && echo "Killed old bot PID: $OLD_PID" || true
fi
if [ -f "$WATCHDOG_PID_FILE" ]; then
    OLD_WD=$(cat "$WATCHDOG_PID_FILE")
    kill "$OLD_WD" 2>/dev/null && echo "Killed old watchdog PID: $OLD_WD" || true
fi
sleep 2

# Launch watchdog in a new session, fully detached
cd "$PROJECT_ROOT"
setsid nohup bash scripts/run_v6_with_watchdog.sh "$DURATION_MIN" > "$LOG_FILE" 2>&1 &
WATCHDOG_PID=$!
echo $WATCHDOG_PID > "$WATCHDOG_PID_FILE"
disown $WATCHDOG_PID

# Wait for the python process to start
sleep 3

# Verify
if [ -f "$PID_FILE" ]; then
    BOT_PID=$(cat "$PID_FILE")
    if ps -p "$BOT_PID" > /dev/null 2>&1; then
        echo "✅ v6 bot launched successfully"
        echo "   Bot PID: $BOT_PID"
        echo "   Watchdog PID: $WATCHDOG_PID"
        echo "   Duration: ${DURATION_MIN} minutes"
        echo "   Log: $LOG_FILE"
        echo "   Live log: logs/rt_v6_live.log"
    else
        echo "❌ Bot process not running (PID: $BOT_PID)"
        tail -20 "$LOG_FILE"
        exit 1
    fi
else
    echo "❌ PID file not created"
    tail -20 "$LOG_FILE"
    exit 1
fi
