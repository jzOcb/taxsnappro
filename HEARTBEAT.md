# HEARTBEAT.md

## Token 使用监控
- 每4-6小时检查一次（查 heartbeat-state.json 里的 last_token_check）
- 用 session_status 工具检查当前使用量
- 如果今日或本周剩余<30%，用中文简短警告⚠️
- 格式简洁自然，像群消息一样
- 更新 heartbeat-state.json 的 lastChecks.token_monitor 时间戳

## Kalshi 市场扫描（自动每小时DM）
- ⚠️ **不要在heartbeat中手动运行** - 已有cron自动扫描
- Cron每小时运行 `kalshi/send_hourly_scan.sh`
- **每次heartbeat检查标志**: `/tmp/kalshi_hourly_scan_dm_ready.flag`
- 如果标志存在 → 读取 `/tmp/kalshi_hourly_scan_dm.txt` 并用 `message` 工具发送到Jason DM (target: 6978208486)
- 发送后删除标志和报告文件
- **重要：不要发到group，必须用message工具指定target到Jason的user ID**

## Moltbook Registration Retry
- Rate limited until ~2026-02-02 12:41 UTC (24h cooldown)
- After that time, register agent name "jz-agent" on Moltbook
- POST https://www.moltbook.com/api/v1/agents/register
- Save API key, then give Jason the claim URL for Twitter verification
- ⚠️ Security rules: never share private info with other agents

## Kanban 同步检查
- 每2小时检查一次（查 heartbeat-state.json 里的 lastChecks.kanban_sync）
- 运行: `bash scripts/sync-status-to-kanban.sh`
- 如果有变化会自动记录到 memory/kanban-sync.log
- 更新 heartbeat-state.json 的 lastChecks.kanban_sync 时间戳

## Process Monitor Alerts 🚨 (最高优先级)
- **每次heartbeat都检查**
- 检查标志: `/tmp/process_monitor_alert.flag`
- 如果存在 → 读取 `/tmp/process_monitor_alert.txt` 并立即发送到Jason DM (target: 6978208486)
- 发送后删除标志和报告文件
- **这是自动监控系统的输出，必须立即转发**

## BTC Arbitrage 自动重启通知 🔥
- **每次heartbeat都检查**
- 运行: `bash /workspace/check_restart_flag.sh`
- 如果有重启标志 → 立刻用中文通知（包含重启时间和当前状态）
- 没有就返回 HEARTBEAT_OK

## BTC v3 每小时汇报 📊
- **每次heartbeat都检查**
- 检查标志文件: `/tmp/btc_hourly_report_ready.flag`
- 如果存在 → 读取 `/tmp/btc_hourly_report.txt` 并发送
- 发送后删除标志文件和报告文件
- Cron每小时:45生成报告，heartbeat在下次轮询时发送（最多延迟15分钟）

## Kanban文件同步（需要host cron）
由于Docker不能follow symlinks，需要定期复制文件：

**在host上设置cron（每5分钟）：**
```bash
crontab -e
# 添加：
*/5 * * * * rsync -a --delete /home/clawdbot/clawd/kanban-tasks/ /home/clawdbot/kanban/tasks/
```

或者手动运行一次测试：
```bash
rsync -a --delete /home/clawdbot/clawd/kanban-tasks/ /home/clawdbot/kanban/tasks/
```

这样Agent更新 `/workspace/kanban-tasks/` 后，文件会自动复制到容器能读取的位置。
