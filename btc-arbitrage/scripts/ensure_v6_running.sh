#!/bin/bash
# Cron health check: ensure v6 bot is running
# Add to crontab: */5 * * * * bash /home/clawdbot/clawd/btc-arbitrage/scripts/ensure_v6_running.sh

PID_FILE="/tmp/rt_v6_pid.txt"
WATCHDOG_PID_FILE="/tmp/rt_v6_watchdog_pid.txt"
PROJECT_ROOT="/home/clawdbot/clawd/btc-arbitrage"
LOCK_FILE="/tmp/v6_ensure_lock"

# Prevent concurrent runs
if [ -f "$LOCK_FILE" ]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -c %Y "$LOCK_FILE") ))
    if [ $LOCK_AGE -lt 300 ]; then
        exit 0
    fi
fi
touch "$LOCK_FILE"

cleanup() { rm -f "$LOCK_FILE"; }
trap cleanup EXIT

# Check if bot is running
BOT_ALIVE=false
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        BOT_ALIVE=true
    fi
fi

if $BOT_ALIVE; then
    # Bot is running, nothing to do
    exit 0
fi

# Bot is dead. Check if it completed its full duration (don't restart if completed)
LIVE_LOG="$PROJECT_ROOT/logs/rt_v6_live.log"
if [ -f "$LIVE_LOG" ]; then
    LAST_LINE=$(tail -1 "$LIVE_LOG")
    # Check if the summary shows full duration (>= 400 minutes means it completed)
    DURATION=$(grep "^Duration:" "$LIVE_LOG" | tail -1 | grep -oP '\d+(?=min)' || echo "0")
    if [ "$DURATION" -ge 400 ]; then
        # Completed normally, don't restart
        echo "$(date): v6 completed normally (${DURATION}min). Not restarting." >> /tmp/v6_health.log
        exit 0
    fi
fi

# Bot died prematurely — restart it
echo "$(date): v6 bot died. Restarting..." >> /tmp/v6_health.log
cd "$PROJECT_ROOT"
bash scripts/launch_v6_detached.sh 480 >> /tmp/v6_health.log 2>&1

# Notify via flag file (heartbeat will pick this up)
echo "$(date): v6 auto-restarted by health check" > /tmp/v6_auto_restart.flag
