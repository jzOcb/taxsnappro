# HEARTBEAT.md

## Token 使用监控
- 每4-6小时检查一次（查 heartbeat-state.json 里的 last_token_check）
- 用 session_status 工具检查当前使用量
- 如果今日或本周剩余<30%，用中文简短警告⚠️
- 格式简洁自然，像群消息一样
- 更新 heartbeat-state.json 的 lastChecks.token_monitor 时间戳

## Kalshi 市场扫描
- 每3-4小时跑一次（查 heartbeat-state.json 里的 lastChecks.kalshi_scan）
- 执行: `cd /workspace && python3 kalshi/notify.py`
- 如果有🎯 junk bonds 回报>10% 或 🚨价格变动>5¢ → 简短报告
- 没有 notable 结果就跳过通知（别刷屏）
- 更新时间戳

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
