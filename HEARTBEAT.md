# HEARTBEAT.md

## Token 使用监控
- 每4-6小时检查一次（查 heartbeat-state.json 里的 last_token_check）
- 用 session_status 工具检查当前使用量
- 如果今日或本周剩余<30%，用中文简短警告⚠️
- 更新 heartbeat-state.json 的 lastChecks.token_monitor 时间戳

## Kanban 同步检查
- 每2小时检查一次（查 heartbeat-state.json 里的 lastChecks.kanban_sync）
- 运行: `bash scripts/sync-status-to-kanban.sh`
- 更新 heartbeat-state.json 的 lastChecks.kanban_sync 时间戳

## ✅ 已迁移到 Cron AgentTurn（不再需要heartbeat处理）
以下任务已改为cron直接deliver，不再经过heartbeat flag轮询：
- Kalshi 每小时扫描 → cron "Kalshi Hourly Scan" (:15)
- Kalshi 持仓监控 → cron "Kalshi Position Monitor" (:30)
- BTC 30分钟更新 → cron "BTC 30min Update" (:00/:30)
- 进程健康监控 → cron "Process Health Monitor" (*/5min)
- 美股异动预警 → cron "market-alert-monitor"
- 美股收盘报告 → cron "market-report-close"
