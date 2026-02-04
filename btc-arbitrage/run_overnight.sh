#!/bin/bash
cd /home/clawdbot/clawd/btc-arbitrage
nohup python3 -u scripts/monitor_overnight.py 480 60 > logs/monitor.log 2>&1 &
echo $! > /tmp/monitor_pid.txt
nohup python3 -u scripts/paper_trade_overnight.py 480 60 10 > logs/paper_trade.log 2>&1 &
echo $! > /tmp/paper_trade_pid.txt
echo "Started:"
echo "Monitor PID: $(cat /tmp/monitor_pid.txt)"
echo "Paper Trade PID: $(cat /tmp/paper_trade_pid.txt)"
