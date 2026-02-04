#!/bin/bash
# 更新 Heartbeat 监控脚本

# 日志路径更新
LOG_PATH="/home/clawdbot/clawd/heartbeat_monitor.log"

# BTC Arbitrage重启检查
RESTART_FLAG="/home/clawdbot/clawd/check_restart_flag.sh"

if [ -f "$RESTART_FLAG" ]; then
    RESTART_INFO=$(bash "$RESTART_FLAG")
    
    # 使用 message 工具发送通知
    message action=send \
        channel=telegram \
        to="-1003548880054" \
        message="⚠️ BTC Arbitrage 重启通知：
$RESTART_INFO"
    
    echo "[$(date)] BTC Arbitrage 重启通知: $RESTART_INFO" >> "$LOG_PATH"
fi