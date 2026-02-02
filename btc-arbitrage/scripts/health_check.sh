#!/bin/bash
# Health check for overnight tasks

echo "🔍 BTC Arbitrage Health Check - $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo ""

# Check PIDs
MONITOR_RUNNING=0
PAPER_RUNNING=0

if [ -f /tmp/monitor_pid.txt ]; then
    PID1=$(cat /tmp/monitor_pid.txt)
    if kill -0 $PID1 2>/dev/null; then
        echo "✅ Monitor (PID $PID1): Running"
        MONITOR_RUNNING=1
    else
        echo "❌ Monitor (PID $PID1): Dead"
    fi
fi

if [ -f /tmp/paper_trade_pid.txt ]; then
    PID2=$(cat /tmp/paper_trade_pid.txt)
    if kill -0 $PID2 2>/dev/null; then
        echo "✅ Paper Trade (PID $PID2): Running"
        PAPER_RUNNING=1
    else
        echo "❌ Paper Trade (PID $PID2): Dead"
    fi
fi

echo ""

# Show latest progress
if [ $MONITOR_RUNNING -eq 1 ]; then
    echo "📊 Monitor Progress:"
    tail -3 /workspace/btc-arbitrage/logs/monitor.log
    echo ""
fi

if [ $PAPER_RUNNING -eq 1 ]; then
    echo "💰 Paper Trade Progress:"
    tail -3 /workspace/btc-arbitrage/logs/paper_trade.log
    echo ""
fi

# Check if both dead - restart
if [ $MONITOR_RUNNING -eq 0 ] && [ $PAPER_RUNNING -eq 0 ]; then
    echo "⚠️  Both processes dead - RESTARTING..."
    cd /workspace/btc-arbitrage && ./run_overnight.sh
fi
