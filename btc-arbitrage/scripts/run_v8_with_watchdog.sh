#!/bin/bash
# Watchdog for BTC Paper Trader V8
# Restarts on crash, logs all events

SCRIPT="/home/clawdbot/clawd/btc-arbitrage/src/realtime_paper_trader_v8.py"
LOG_DIR="/home/clawdbot/clawd/btc-arbitrage/logs"
WATCHDOG_LOG="$LOG_DIR/rt_v8_watchdog.log"
DURATION="${1:-480}"  # Default 8 hours
MAX_RESTARTS=10
RESTART_DELAY=10

mkdir -p "$LOG_DIR"

restart_count=0

log() {
    echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [WATCHDOG-V8] $1" | tee -a "$WATCHDOG_LOG"
}

log "Starting V8 watchdog (duration=${DURATION}min, max_restarts=${MAX_RESTARTS})"

while [ $restart_count -lt $MAX_RESTARTS ]; do
    log "Launch #$((restart_count + 1)): python3 $SCRIPT $DURATION"
    
    python3 "$SCRIPT" "$DURATION" 2>&1 | tee -a "$WATCHDOG_LOG"
    EXIT_CODE=$?
    
    log "Process exited with code $EXIT_CODE"
    
    # Clean exit (signal handler set graceful_shutdown)
    if [ $EXIT_CODE -eq 0 ]; then
        log "Clean exit. Stopping watchdog."
        break
    fi
    
    restart_count=$((restart_count + 1))
    
    if [ $restart_count -lt $MAX_RESTARTS ]; then
        log "Restarting in ${RESTART_DELAY}s... (restart $restart_count/$MAX_RESTARTS)"
        sleep $RESTART_DELAY
    else
        log "Max restarts reached ($MAX_RESTARTS). Stopping."
    fi
done

log "Watchdog exiting (restarts=$restart_count)"
