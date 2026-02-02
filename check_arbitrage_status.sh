#!/bin/bash
# 简单的仲裁状态检查脚本

LOG_FILE="/home/clawdbot/clawd/arbitrage_status.log"

# 检查仲裁相关文件或进程
echo "$(date): 检查仲裁状态" >> "$LOG_FILE"

# 检查 BTC 仲裁进程
if pgrep -f "btc_arbitrage" > /dev/null; then
    echo "BTC 仲裁进程运行正常" >> "$LOG_FILE"
else
    echo "警告：BTC 仲裁进程未运行" >> "$LOG_FILE"
fi

# 检查最近的交易日志
if [ -f "/workspace/btc-arbitrage/trades.log" ]; then
    LAST_TRADE=$(tail -n 1 "/workspace/btc-arbitrage/trades.log")
    echo "最近交易: $LAST_TRADE" >> "$LOG_FILE"
fi
