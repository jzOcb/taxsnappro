#!/bin/bash
# Check all alert flags and output any alerts found.
# Exit 0 with no output = all clear.

has_alert=0

if [ -f /tmp/process_monitor_alert.flag ]; then
    [ -f /tmp/process_monitor_alert.txt ] && cat /tmp/process_monitor_alert.txt
    rm -f /tmp/process_monitor_alert.flag /tmp/process_monitor_alert.txt
    has_alert=1
fi

if [ -f /tmp/subagent_stuck_alert.flag ]; then
    echo "🚨 Sub-agent stuck alert"
    [ -f /tmp/subagent_stuck_alert.txt ] && cat /tmp/subagent_stuck_alert.txt
    rm -f /tmp/subagent_stuck_alert.flag /tmp/subagent_stuck_alert.txt
    has_alert=1
fi

if [ -f /tmp/btc_hourly_report_ready.flag ]; then
    [ -f /tmp/btc_hourly_report.txt ] && cat /tmp/btc_hourly_report.txt
    rm -f /tmp/btc_hourly_report_ready.flag /tmp/btc_hourly_report.txt
    has_alert=1
fi

if [ $has_alert -eq 0 ]; then
    echo "NO_ALERTS"
fi
