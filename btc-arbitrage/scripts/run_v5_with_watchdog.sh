#!/bin/bash
# 进程守护脚本 - v5 Dual Market (15min + Hourly)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="/tmp/rt_v5_pid.txt"
RESTART_FLAG="/tmp/rt_v5_restart.flag"
MAX_RESTARTS=3
DURATION_MIN=${1:-480}

cd "$PROJECT_ROOT"

restart_count=0
start_time=$(date +%s)

echo "🚀 启动v5 Dual Market Paper Trader with Watchdog"
echo "Duration: ${DURATION_MIN}min | Max Restarts: $MAX_RESTARTS"
echo "Markets: 15min + Hourly"
echo "========================================"

while [ $restart_count -lt $MAX_RESTARTS ]; do
    echo -e "\n[$(date '+%Y-%m-%d %H:%M:%S')] 启动 v5 (attempt $((restart_count+1))/$MAX_RESTARTS)"
    
    python3 src/realtime_paper_trader_v5_dual.py $DURATION_MIN &
    pid=$!
    echo $pid > "$PID_FILE"
    echo "✅ Started with PID: $pid"
    
    echo "$(date +%s)|$pid|$restart_count" > "$RESTART_FLAG"
    
    wait $pid
    exit_code=$?
    
    elapsed=$(($(date +%s) - start_time))
    echo "⚠️ Process exited with code $exit_code after ${elapsed}s"
    
    expected_duration=$((DURATION_MIN * 60))
    if [ $elapsed -ge $((expected_duration - 60)) ]; then
        echo "✅ Process completed successfully (ran for ${elapsed}s / expected ${expected_duration}s)"
        rm -f "$RESTART_FLAG"
        exit 0
    fi
    
    restart_count=$((restart_count+1))
    
    if [ $restart_count -lt $MAX_RESTARTS ]; then
        echo "🔄 Will restart in 10 seconds..."
        sleep 10
    else
        echo "❌ Max restarts reached. Giving up."
        rm -f "$RESTART_FLAG"
        exit 1
    fi
done

rm -f "$RESTART_FLAG"
