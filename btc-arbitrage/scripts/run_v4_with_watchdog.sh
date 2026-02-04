#!/bin/bash
# 进程守护脚本 - 监控v4

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="/tmp/rt_v4_pid.txt"
RESTART_FLAG="/tmp/rt_v4_restart.flag"
MAX_RESTARTS=3
DURATION_MIN=${1:-480}

cd "$PROJECT_ROOT"

restart_count=0
start_time=$(date +%s)

echo "🚀 启动v4 Paper Trader with Watchdog"
echo "Duration: ${DURATION_MIN}min | Max Restarts: $MAX_RESTARTS"
echo "Changes: Flash Crash DISABLED, Fixed async"
echo "========================================"

while [ $restart_count -lt $MAX_RESTARTS ]; do
    echo -e "\n[$(date '+%Y-%m-%d %H:%M:%S')] 启动 v4 (attempt $((restart_count+1))/$MAX_RESTARTS)"
    
    # 启动v4
    python3 src/realtime_paper_trader_v4.py $DURATION_MIN &
    pid=$!
    echo $pid > "$PID_FILE"
    echo "✅ Started with PID: $pid"
    
    # 记录启动标志
    echo "$(date +%s)|$pid|$restart_count" > "$RESTART_FLAG"
    
    # 等待进程结束
    wait $pid
    exit_code=$?
    
    elapsed=$(($(date +%s) - start_time))
    echo "⚠️ Process exited with code $exit_code after ${elapsed}s"
    
    # 检查是否正常结束
    expected_duration=$((DURATION_MIN * 60))
    if [ $elapsed -ge $((expected_duration - 60)) ]; then
        echo "✅ Process completed successfully (ran for ${elapsed}s / expected ${expected_duration}s)"
        rm -f "$RESTART_FLAG"
        exit 0
    fi
    
    # 非正常退出
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
