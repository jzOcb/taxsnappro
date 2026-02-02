#!/bin/bash

LOG_FILE="/home/clawdbot/clawd/heartbeat.log"
ERROR_LOG="/workspace/heartbeat_errors.log"

# 监控错误和异常
echo "=== Heartbeat 监控 ===" > "$ERROR_LOG"
echo "开始时间: $(date)" >> "$ERROR_LOG"

grep -E "ERROR|CRITICAL|WARNING" "$LOG_FILE" >> "$ERROR_LOG"

echo "=== 最近错误总结 ===" >> "$ERROR_LOG"
wc -l "$ERROR_LOG"

# 检查日志文件大小
LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
echo "日志文件大小: $LOG_SIZE" >> "$ERROR_LOG"

# 如果日志过大，进行轮转
if [ $(du -k "$LOG_FILE" | cut -f1) -gt 10240 ]; then
    echo "日志文件过大，进行轮转" >> "$ERROR_LOG"
    mv "$LOG_FILE" "${LOG_FILE}.$(date +%Y%m%d%H%M%S)"
    touch "$LOG_FILE"
fi

