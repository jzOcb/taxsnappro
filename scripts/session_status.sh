#!/bin/bash

# 会话状态监控脚本
LOG_FILE="/workspace/session_status_debug.log"

# 记录日志
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" >> "$LOG_FILE"
}

log "开始会话状态监控"

# 收集基本系统信息
log "系统信息："
uname -a >> "$LOG_FILE"

# 检查当前会话
log "当前会话详情："
who am i >> "$LOG_FILE"

# 模拟 token 使用情况
TOTAL_TOKENS=100000
USED_TOKENS=$(( RANDOM % 50000 ))
REMAINING_TOKENS=$(( TOTAL_TOKENS - USED_TOKENS ))
USAGE_PERCENTAGE=$(( USED_TOKENS * 100 / TOTAL_TOKENS ))

log "Token 使用情况："
log "总 Token 数: $TOTAL_TOKENS"
log "已使用 Token: $USED_TOKENS"
log "剩余 Token: $REMAINING_TOKENS"
log "使用百分比: $USAGE_PERCENTAGE%"

# 输出结果
echo "Token Usage: $USAGE_PERCENTAGE%"

log "会话状态监控完成"
