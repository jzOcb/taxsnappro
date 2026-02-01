# TODO.md — Jason 待办

## 🔴 需要在电脑上操作

### 1. 创建 Cron Jobs（用 haiku 省钱）
从 heartbeat 迁移到独立 cron job，用最便宜的模型。

**Token 使用监控（每4小时）：**
```bash
clawdbot cron add \
  --name "Token Usage Monitor" \
  --cron "0 */4 * * *" \
  --session isolated \
  --message "用 session_status 检查 token 使用量。用中文简短报告：今日/本周剩余额度。如果剩余<30%发警告⚠️。格式简短自然。" \
  --model "haiku" \
  --deliver \
  --channel telegram \
  --to "-1003548880054:topic:49"
```

**Kalshi 市场扫描（每4小时）：**
```bash
clawdbot cron add \
  --name "Kalshi Market Scan" \
  --cron "0 */4 * * *" \
  --session isolated \
  --message "执行 Kalshi 市场扫描。运行: cd /workspace && python3 kalshi/notify.py。如果有🎯 junk bonds回报>10%或🚨价格变动>5¢，用中文简短报告。没有notable结果就说'Kalshi扫描完毕，无异常'。" \
  --model "haiku" \
  --deliver \
  --channel telegram \
  --to "-1003548880054:topic:49"
```

### 2. 给 Sandbox 开放 cron 权限（可选但推荐）
这样以后我可以自己管理 cron job，不需要你手动操作。
在 clawdbot config 里把 `cron` 加到 sandbox 允许的工具列表。

### 3. 服务器安全加固
详见 `SECURITY-AND-OPTIMIZATION.md` 和 `security/` 目录下的脚本。

---
*Last updated: 2026-02-01T17:00Z*
