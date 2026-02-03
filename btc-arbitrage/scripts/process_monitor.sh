#!/bin/bash
# process_monitor.sh — Autonomous process health monitor
# Runs every 5 minutes via cron
# Checks ALL managed processes, alerts Jason if anything dies unexpectedly
# 
# This exists because: processes launched by the agent keep dying silently.
# Nobody knows until Jason manually asks. That's unacceptable.

set -uo pipefail

PROJECT_ROOT="/home/clawdbot/clawd/btc-arbitrage"
MONITOR_STATE="/tmp/process_monitor_state.json"
ALERT_FLAG="/tmp/process_alert.flag"
ALERT_COOLDOWN=900  # 15 min between alerts for same process
LOG="/tmp/process_monitor.log"

log() {
    echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $1" >> "$LOG"
}

# Initialize state file if missing
if [ ! -f "$MONITOR_STATE" ]; then
    echo '{}' > "$MONITOR_STATE"
fi

ALERTS=""

# ═══════════════════════════════════════════════
# CHECK 1: BTC v6 Bot
# ═══════════════════════════════════════════════
check_btc_v6() {
    local PID_FILE="/tmp/rt_v6_pid.txt"
    local LIVE_LOG="$PROJECT_ROOT/logs/rt_v6_live.log"
    
    if [ ! -f "$PID_FILE" ]; then
        # No PID file = bot was never started or completed, not an alert
        return
    fi
    
    local PID=$(cat "$PID_FILE")
    
    if ps -p "$PID" > /dev/null 2>&1; then
        # Running — check if it's actually producing output
        if [ -f "$LIVE_LOG" ]; then
            local LOG_AGE=$(( $(date +%s) - $(stat -c %Y "$LIVE_LOG") ))
            if [ $LOG_AGE -gt 300 ]; then
                ALERTS="${ALERTS}🔴 BTC v6: Process alive (PID $PID) but no log output for ${LOG_AGE}s — might be hung\n"
                log "WARN: v6 alive but stale log (${LOG_AGE}s)"
            else
                log "OK: v6 running (PID $PID, log ${LOG_AGE}s old)"
            fi
        fi
        return
    fi
    
    # Process is dead — check if it completed normally
    if [ -f "$LIVE_LOG" ]; then
        local SUMMARY_LINE=$(grep "^Duration:" "$LIVE_LOG" | tail -1)
        local DURATION=$(echo "$SUMMARY_LINE" | grep -oP '\d+(?=min)' || echo "0")
        
        if [ "$DURATION" -ge 400 ]; then
            log "OK: v6 completed normally (${DURATION}min)"
            return
        fi
        
        # Check for signal
        local SIGNAL_LINE=$(grep "SIGNAL RECEIVED" "$LIVE_LOG" | tail -1)
        
        # Died prematurely
        local LAST_PNL=$(grep -oP 'Total: \$\K[+-]?[0-9.]+' "$LIVE_LOG" 2>/dev/null | tail -1 || echo "?")
        local TRADE_COUNT=$(grep -c "CLOSE" "$LIVE_LOG" 2>/dev/null || echo "0")
        
        ALERTS="${ALERTS}🔴 BTC v6: 进程已死 (PID $PID)\n"
        ALERTS="${ALERTS}   运行: ${DURATION}min | 交易: ${TRADE_COUNT} | P&L: \$${LAST_PNL}\n"
        if [ -n "$SIGNAL_LINE" ]; then
            ALERTS="${ALERTS}   原因: ${SIGNAL_LINE}\n"
        fi
        ALERTS="${ALERTS}   正在自动重启...\n"
        
        log "ALERT: v6 died (${DURATION}min, PnL $LAST_PNL)"
        
        # Auto-restart
        cd "$PROJECT_ROOT"
        bash scripts/launch_v6_detached.sh 480 >> "$LOG" 2>&1
        log "RESTART: v6 restarted"
    fi
}

# ═══════════════════════════════════════════════
# CHECK 2: Watchdog process
# ═══════════════════════════════════════════════
check_watchdog() {
    local WD_PID_FILE="/tmp/rt_v6_watchdog_pid.txt"
    
    if [ ! -f "$WD_PID_FILE" ]; then
        return
    fi
    
    local WD_PID=$(cat "$WD_PID_FILE")
    if ! ps -p "$WD_PID" > /dev/null 2>&1; then
        log "WARN: Watchdog dead (PID $WD_PID)"
        # Watchdog dying is handled by check_btc_v6 restart
    fi
}

# ═══════════════════════════════════════════════
# CHECK 3: Kalshi cron health
# ═══════════════════════════════════════════════
check_kalshi() {
    # Check if kalshi scan ran recently (should run every hour at :15)
    local SCAN_LOG="/home/clawdbot/clawd/kalshi_market_scan.log"
    if [ -f "$SCAN_LOG" ]; then
        local SCAN_AGE=$(( $(date +%s) - $(stat -c %Y "$SCAN_LOG") ))
        if [ $SCAN_AGE -gt 7200 ]; then
            ALERTS="${ALERTS}⚠️ Kalshi: 市场扫描超过2小时未运行 (${SCAN_AGE}s)\n"
            log "WARN: kalshi scan stale (${SCAN_AGE}s)"
        else
            log "OK: kalshi scan recent (${SCAN_AGE}s)"
        fi
    fi
}

# ═══════════════════════════════════════════════
# RUN ALL CHECKS
# ═══════════════════════════════════════════════
check_btc_v6
check_watchdog
check_kalshi

# ═══════════════════════════════════════════════
# SEND ALERTS (if any)
# ═══════════════════════════════════════════════
if [ -n "$ALERTS" ]; then
    # Check cooldown
    if [ -f "$ALERT_FLAG" ]; then
        local ALERT_AGE=$(( $(date +%s) - $(stat -c %Y "$ALERT_FLAG") ))
        if [ $ALERT_AGE -lt $ALERT_COOLDOWN ]; then
            log "SUPPRESSED: Alert within cooldown (${ALERT_AGE}s < ${ALERT_COOLDOWN}s)"
            exit 0
        fi
    fi
    
    touch "$ALERT_FLAG"
    
    # Write alert for heartbeat/clawdbot to pick up and send
    ALERT_MSG="🚨 **Process Monitor Alert**\n\n${ALERTS}\n_自动监控 $(date -u '+%H:%M UTC')_"
    echo -e "$ALERT_MSG" > /tmp/process_monitor_alert.txt
    touch /tmp/process_monitor_alert.flag
    
    log "ALERT SENT: $(echo -e "$ALERTS" | head -1)"
fi
