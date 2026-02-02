#!/bin/bash
echo "=== Process Check ==="
if [ -f /tmp/monitor_pid.txt ]; then
    PID1=$(cat /tmp/monitor_pid.txt)
    if kill -0 $PID1 2>/dev/null; then
        echo "Monitor (PID $PID1): ✅ Running"
    else
        echo "Monitor (PID $PID1): ❌ Dead"
    fi
fi

if [ -f /tmp/paper_trade_pid.txt ]; then
    PID2=$(cat /tmp/paper_trade_pid.txt)
    if kill -0 $PID2 2>/dev/null; then
        echo "Paper Trade (PID $PID2): ✅ Running"
    else
        echo "Paper Trade (PID $PID2): ❌ Dead"
    fi
fi

echo ""
echo "=== Latest Log Output ==="
echo "--- Monitor ---"
tail -5 /workspace/btc-arbitrage/logs/monitor.log
echo ""
echo "--- Paper Trade ---"
tail -5 /workspace/btc-arbitrage/logs/paper_trade.log
