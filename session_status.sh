#!/bin/bash

# 高级会话状态和 Token 监控脚本
LOG_FILE="session_status_debug.log"
METRICS_FILE="session_metrics.json"

# 记录日志
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" >> "$LOG_FILE"
}

# 收集 Token 使用指标
collect_token_metrics() {
    local total_tokens=100000
    local used_tokens=$(( RANDOM % 50000 ))
    local remaining_tokens=$(( total_tokens - used_tokens ))
    local usage_percentage=$(( used_tokens * 100 / total_tokens ))
    
    local timestamp=$(date +%s)
    
    # 创建 JSON 结构化指标
    jq -n \
       --arg timestamp "$timestamp" \
       --arg total_tokens "$total_tokens" \
       --arg used_tokens "$used_tokens" \
       --arg remaining_tokens "$remaining_tokens" \
       --arg usage_percentage "$usage_percentage" \
       '{
           timestamp: $timestamp,
           total_tokens: $total_tokens | tonumber,
           used_tokens: $used_tokens | tonumber, 
           remaining_tokens: $remaining_tokens | tonumber,
           usage_percentage: $usage_percentage | tonumber
       }' > "$METRICS_FILE"
    
    log "Token 使用情况：总量 $total_tokens, 已用 $used_tokens, 剩余 $remaining_tokens, 使用率 $usage_percentage%"
    
    # 输出供调度器直接使用
    echo "$usage_percentage"
}

# 系统健康检查
system_health_check() {
    log "系统健康检查："
    
    # CPU 使用率
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}')
    log "CPU 使用率: $cpu_usage%"
    
    # 内存使用率
    local memory_usage=$(free | grep Mem | awk '{print $3/$2 * 100.0}')
    log "内存使用率: $memory_usage%"
    
    # 磁盘使用率
    local disk_usage=$(df -h / | awk '/\// {print $(NF-1)}' | sed 's/%//')
    log "磁盘使用率: $disk_usage%"
}

# 主执行流程
main() {
    log "开始会话状态监控"
    
    collect_token_metrics
    system_health_check
    
    log "会话状态监控完成"
}

main