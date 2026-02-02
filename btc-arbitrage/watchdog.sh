#!/bin/bash
# Watchdog - 持续监控并自动重启死掉的进程

LOG_FILE="/workspace/btc-arbitrage/logs/watchdog.log"
CHECK_INTERVAL=120  # 2分钟检查一次

echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] 🐕 Watchdog started" | tee -a "$LOG_FILE"

while true; do
    sleep $CHECK_INTERVAL
    
    NEED_RESTART=0
    
    # Check monitor
    if [ -f /tmp/monitor_pid.txt ]; then
        PID1=$(cat /tmp/monitor_pid.txt)
        if ! kill -0 $PID1 2>/dev/null; then
            echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] ❌ Monitor (PID $PID1) is dead!" | tee -a "$LOG_FILE"
            NEED_RESTART=1
        fi
    else
        echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] ⚠️  Monitor PID file missing" | tee -a "$LOG_FILE"
        NEED_RESTART=1
    fi
    
    # Check paper trade
    if [ -f /tmp/paper_trade_pid.txt ]; then
        PID2=$(cat /tmp/paper_trade_pid.txt)
        if ! kill -0 $PID2 2>/dev/null; then
            echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] ❌ Paper Trade (PID $PID2) is dead!" | tee -a "$LOG_FILE"
            NEED_RESTART=1
        fi
    else
        echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] ⚠️  Paper Trade PID file missing" | tee -a "$LOG_FILE"
        NEED_RESTART=1
    fi
    
    # Restart if needed
    if [ $NEED_RESTART -eq 1 ]; then
        echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] 🔄 AUTO-RESTARTING..." | tee -a "$LOG_FILE"
        cd /workspace/btc-arbitrage && ./run_overnight.sh >> "$LOG_FILE" 2>&1
        echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] ✅ Restarted" | tee -a "$LOG_FILE"
        
        # Create restart notification flag
        echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" > /tmp/btc_arbitrage_restarted.flag
    fi
done
