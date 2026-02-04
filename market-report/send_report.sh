#!/bin/bash
# Send market report via Clawdbot flag file mechanism
# Called by cron, writes report to flag file for heartbeat to pick up

REPORT_FILE="/tmp/market_report.txt"
FLAG_FILE="/tmp/market_report_ready.flag"

cd /home/clawdbot/clawd/market-report

# Generate report
python3 market_report.py --output "$REPORT_FILE" 2>/dev/null

if [ -f "$REPORT_FILE" ] && [ -s "$REPORT_FILE" ]; then
    touch "$FLAG_FILE"
    echo "$(date -u '+%Y-%m-%d %H:%M UTC') - Report ready" >> /home/clawdbot/clawd/market-report/report.log
else
    echo "$(date -u '+%Y-%m-%d %H:%M UTC') - Report generation failed" >> /home/clawdbot/clawd/market-report/report.log
fi
