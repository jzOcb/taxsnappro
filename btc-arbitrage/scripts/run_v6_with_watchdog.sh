#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="/tmp/rt_v6_pid.txt"
RESTART_FLAG="/tmp/rt_v6_restart.flag"
MAX_RESTARTS=3
DURATION_MIN=${1:-480}

cd "$PROJECT_ROOT"

restart_count=0
start_time=$(date +%s)

echo "🚀 v6 - RESEARCH-NOTES.md Improvements"
echo "Duration: ${DURATION_MIN}min | Max Restarts: $MAX_RESTARTS"
echo "========================================"

while [ $restart_count -lt $MAX_RESTARTS ]; do
    echo -e "\n[$(date '+%Y-%m-%d %H:%M:%S')] 启动 v6 (attempt $((restart_count+1))/$MAX_RESTARTS)"
    
    python3 src/realtime_paper_trader_v6.py $DURATION_MIN &
    pid=$!
    echo $pid > "$PID_FILE"
    echo "✅ Started with PID: $pid"
    
    echo "$(date +%s)|$pid|$restart_count" > "$RESTART_FLAG"
    
    wait $pid
    exit_code=$?
    
    elapsed=$(($(date +%s) - start_time))
    echo "Process exited with code $exit_code after ${elapsed}s"
    
    expected_duration=$((DURATION_MIN * 60))
    if [ $elapsed -ge $((expected_duration - 60)) ]; then
        echo "✅ Completed (${elapsed}s / ${expected_duration}s)"
        rm -f "$RESTART_FLAG"
        exit 0
    fi
    
    restart_count=$((restart_count+1))
    
    if [ $restart_count -lt $MAX_RESTARTS ]; then
        echo "🔄 Restarting in 10s..."
        sleep 10
    else
        echo "❌ Max restarts reached"
        rm -f "$RESTART_FLAG"
        exit 1
    fi
done

rm -f "$RESTART_FLAG"
