#!/bin/bash
# V7 continuous runner - keeps restarting after each session
# For 48h+ data collection
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="/tmp/rt_v7_pid.txt"
SESSION_MIN=${1:-720}  # each session 12h
MAX_CRASH_RESTARTS=3
CRASH_COUNT=0

cd "$PROJECT_ROOT"

echo "🚀 V7 Continuous Runner"
echo "Session duration: ${SESSION_MIN}min | Crash restarts: $MAX_CRASH_RESTARTS"
echo "Will keep running until manually killed"
echo "========================================"

while true; do
    session_start=$(date +%s)
    echo -e "\n[$(date '+%Y-%m-%d %H:%M:%S')] 启动 V7 session (${SESSION_MIN}min)"
    
    python3 src/realtime_paper_trader_v7.py $SESSION_MIN &
    pid=$!
    echo $pid > "$PID_FILE"
    echo "✅ PID: $pid"
    
    wait $pid
    exit_code=$?
    session_elapsed=$(( $(date +%s) - session_start ))
    expected=$(( SESSION_MIN * 60 ))
    
    if [ $exit_code -eq 0 ] && [ $session_elapsed -ge $((expected - 120)) ]; then
        echo "✅ Session完成 (${session_elapsed}s). 10s后启动下一轮..."
        CRASH_COUNT=0
        sleep 10
    else
        CRASH_COUNT=$((CRASH_COUNT + 1))
        echo "⚠️ Crash #$CRASH_COUNT (exit=$exit_code, ran ${session_elapsed}s)"
        if [ $CRASH_COUNT -ge $MAX_CRASH_RESTARTS ]; then
            echo "❌ 连续crash ${MAX_CRASH_RESTARTS}次，停止"
            exit 1
        fi
        echo "🔄 10s后重启..."
        sleep 10
    fi
done
