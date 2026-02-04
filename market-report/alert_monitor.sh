#!/bin/bash
# Market alert monitor - runs every 5 minutes during market hours
# Only creates flag file if significant moves detected

REPORT_FILE="/tmp/market_alert.txt"
FLAG_FILE="/tmp/market_alert_ready.flag"

cd /home/clawdbot/clawd/market-report

# Check if US market is open (roughly 9:30-16:00 ET = 14:30-21:00 UTC)
HOUR_UTC=$(date -u +%H)
DOW=$(date -u +%u)  # 1=Monday, 7=Sunday

# Skip weekends
if [ "$DOW" -ge 6 ]; then
    exit 0
fi

# Skip outside market hours (with some buffer)
if [ "$HOUR_UTC" -lt 14 ] || [ "$HOUR_UTC" -ge 21 ]; then
    exit 0
fi

# Run alert-only check
python3 market_report.py --alert-only --output "$REPORT_FILE" 2>/dev/null

# Exit code 0 with empty/no file means no alerts
if [ -f "$REPORT_FILE" ] && [ -s "$REPORT_FILE" ]; then
    # Don't spam - check if we already sent an alert in the last 30 min
    LAST_ALERT="/tmp/market_last_alert_time"
    if [ -f "$LAST_ALERT" ]; then
        LAST=$(cat "$LAST_ALERT")
        NOW=$(date +%s)
        DIFF=$((NOW - LAST))
        if [ "$DIFF" -lt 1800 ]; then
            exit 0  # Too soon since last alert
        fi
    fi
    
    # Generate full report (not just alerts) for context
    python3 market_report.py --output "$REPORT_FILE" 2>/dev/null
    touch "$FLAG_FILE"
    date +%s > "$LAST_ALERT"
    echo "$(date -u '+%Y-%m-%d %H:%M UTC') - ALERT triggered" >> /home/clawdbot/clawd/market-report/report.log
fi
