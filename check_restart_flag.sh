#!/bin/bash
# Check if processes were auto-restarted

if [ -f /tmp/btc_arbitrage_restarted.flag ]; then
    RESTART_TIME=$(cat /tmp/btc_arbitrage_restarted.flag)
    echo "⚠️ **BTC Arbitrage 自动重启**"
    echo ""
    echo "重启时间: $RESTART_TIME"
    echo ""
    echo "当前状态:"
    bash /workspace/btc-arbitrage/scripts/health_check.sh | tail -8
    
    # Clear flag
    rm /tmp/btc_arbitrage_restarted.flag
else
    echo "HEARTBEAT_OK"
fi
