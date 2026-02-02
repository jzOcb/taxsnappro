#!/bin/bash

LOG_FILE="/workspace/heartbeat_monitor.log"

# 记录日志
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" >> "$LOG_FILE"
}

# 检查并重启 Heartbeat 服务
monitor_heartbeat() {
    log "开始 Heartbeat 监控"
    
    # 检查调度器是否运行
    if ! pgrep -f "heartbeat_scheduler.py" > /dev/null; then
        log "Heartbeat 调度器未运行，尝试重启"
        systemctl restart heartbeat.service
        
        # 等待并再次验证
        sleep 10
        if ! pgrep -f "heartbeat_scheduler.py" > /dev/null; then
            log "重启失败，发送告警"
            # 可以添加告警通知逻辑
        fi
    fi
    
    # 检查日志文件大小
    log_size=$(du -k "heartbeat.log" | cut -f1)
    if [ "$log_size" -gt 10240 ]; then  # 10MB
        log "日志文件过大，进行轮转"
        mv heartbeat.log "heartbeat.log.$(date +%Y%m%d%H%M%S)"
        touch heartbeat.log
    fi
    
    log "Heartbeat 监控完成"
}

# 主执行流程
main() {
    monitor_heartbeat
}

main