#!/bin/bash
# 每小时汇报v3运行状态和交易结果

set -e

PROJECT_ROOT="/home/clawdbot/clawd/btc-arbitrage"
cd "$PROJECT_ROOT"

# 读取PID (优先v6)
if [ -f /tmp/rt_v6_pid.txt ]; then
    PID=$(cat /tmp/rt_v6_pid.txt)
    VERSION="v6"
    LIVE_LOG="logs/rt_v6_live.log"
elif [ -f /tmp/rt_v5_pid.txt ]; then
    PID=$(cat /tmp/rt_v5_pid.txt)
    VERSION="v5"
    LIVE_LOG="logs/rt_v5_live.log"
elif [ -f /tmp/rt_v4_pid.txt ]; then
    PID=$(cat /tmp/rt_v4_pid.txt)
    VERSION="v4"
    LIVE_LOG="logs/rt_v4_live.log"
elif [ -f /tmp/rt_v3_pid.txt ]; then
    PID=$(cat /tmp/rt_v3_pid.txt)
    VERSION="v3"
    LIVE_LOG="logs/rt_v3_live.log"
else
    echo "⚠️ **BTC Arbitrage - 每小时汇报**"
    echo ""
    echo "❌ 找不到PID文件，进程可能未启动"
    exit 0
fi

# 检查进程状态
if ! ps -p $PID > /dev/null 2>&1; then
    # 检查是正常结束还是异常退出
    LAST_LINE=$(tail -1 "$LIVE_LOG" 2>/dev/null || echo "")
    LAST_PNL=$(grep -oP 'Total: \$\K[+-]?[0-9.]+' "$LIVE_LOG" 2>/dev/null | tail -1 || echo "")
    TOTAL_TRADES=$(grep -c "CLOSE" "$LIVE_LOG" 2>/dev/null || echo "0")
    LAST_LOG_TIME=$(stat -c %Y "$LIVE_LOG" 2>/dev/null || echo "0")
    PID_FILE_TIME=$(stat -c %Y "/tmp/rt_${VERSION}_pid.txt" 2>/dev/null || echo "0")
    
    # 如果最后一行包含PROFIT/CLOSE且日志时间接近PID写入时间，说明正常结束
    if echo "$LAST_LINE" | grep -qE "(PROFIT|CLOSE|Checkpoint|SESSION COMPLETE|SUMMARY|======)"; then
        echo "📊 **BTC $VERSION - 每小时汇报**"
        echo ""
        echo "✅ 进程已正常结束 (PID: $PID)"
        echo ""
        echo "**最终结果**: P&L \$${LAST_PNL:-N/A} | ${TOTAL_TRADES} 笔交易"
        echo ""
        echo "最后几条记录："
        tail -5 "$LIVE_LOG" 2>/dev/null
    else
        echo "⚠️ **BTC $VERSION - 每小时汇报**"
        echo ""
        echo "❌ 进程异常停止 (PID: $PID)"
        echo ""
        echo "最后日志："
        tail -10 "$LIVE_LOG" 2>/dev/null
    fi
    exit 0
fi

# 进程运行时间
ELAPSED=$(ps -p $PID -o etimes --no-headers | xargs)
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_HR=$((ELAPSED_MIN / 60))
ELAPSED_MIN_REM=$((ELAPSED_MIN % 60))

# 检查日志文件
if [ ! -f "$LIVE_LOG" ]; then
    echo "⚠️ 找不到日志文件: $LIVE_LOG"
    exit 0
fi

# 提取关键信息
LAST_STATUS=$(grep -E "^\[.*\] BRTI\*:" "$LIVE_LOG" | tail -1)
LAST_TRADE=$(grep -E "^\[.*\] (🎯|⚡|✅|❌)" "$LIVE_LOG" | tail -1)
CHECKPOINT=$(grep "💾 Checkpoint saved" "$LIVE_LOG" | tail -1)

# 统计交易
TOTAL_TRADES=$(grep -c "CLOSE" "$LIVE_LOG" 2>/dev/null || echo "0")
WINS=$(grep -cE "CLOSE \(PROFIT\)" "$LIVE_LOG" 2>/dev/null || echo "0")
LOSSES=$(grep -cE "CLOSE \(LOSS\)" "$LIVE_LOG" 2>/dev/null || echo "0")

# 获取当前P&L（从最后一次status line或CLOSE line）
CURRENT_PNL=$(grep -oP 'Total: \$\K[+-]?[0-9.]+' "$LIVE_LOG" 2>/dev/null | tail -1 || echo "")
if [ -z "$CURRENT_PNL" ]; then
    CURRENT_PNL=$(grep -oP 'P&L: \$\K[+-]?[0-9.]+' "$LIVE_LOG" 2>/dev/null | tail -1 || echo "0.00")
fi

# 读取checkpoint文件（如果存在）
CHECKPOINT_DATA=""
if [ -f "data/rt_v3_state.json" ]; then
    CHECKPOINT_TIME=$(stat -c %Y "data/rt_v3_state.json" 2>/dev/null || echo "0")
    NOW=$(date +%s)
    CHECKPOINT_AGE=$((NOW - CHECKPOINT_TIME))
    CHECKPOINT_AGE_MIN=$((CHECKPOINT_AGE / 60))
    
    if [ $CHECKPOINT_AGE_MIN -lt 10 ]; then
        CHECKPOINT_DATA="✅ Checkpoint最新 (${CHECKPOINT_AGE_MIN}分钟前)"
    else
        CHECKPOINT_DATA="⚠️ Checkpoint过期 (${CHECKPOINT_AGE_MIN}分钟前)"
    fi
fi

# 构建汇报消息
echo "📊 **BTC $VERSION - 每小时汇报**"
echo ""
echo "**运行状态**: ✅ 正常 (PID: $PID)"
echo "**运行时长**: ${ELAPSED_HR}小时${ELAPSED_MIN_REM}分钟 / 8小时"
echo ""
echo "**交易统计**:"
echo "- 总交易: ${TOTAL_TRADES} 笔"
echo "- 胜/负: ${WINS} / ${LOSSES}"
if [ "$TOTAL_TRADES" -gt 0 ]; then
    WIN_RATE=$((WINS * 100 / TOTAL_TRADES))
    echo "- 胜率: ${WIN_RATE}%"
fi
echo "- 当前P&L: \$${CURRENT_PNL}"
echo ""

if [ -n "$LAST_TRADE" ]; then
    echo "**最后一笔交易**:"
    echo "\`\`\`"
    echo "$LAST_TRADE" | sed 's/^[0-9-T:.]* //'
    echo "\`\`\`"
    echo ""
fi

if [ -n "$CHECKPOINT_DATA" ]; then
    echo "**Checkpoint**: $CHECKPOINT_DATA"
    echo ""
fi

REMAINING_MIN=$((480 - ELAPSED_MIN))
REMAINING_HR=$((REMAINING_MIN / 60))
REMAINING_MIN_REM=$((REMAINING_MIN % 60))
echo "**剩余时间**: ${REMAINING_HR}小时${REMAINING_MIN_REM}分钟"
