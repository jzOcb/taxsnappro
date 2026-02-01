# 🔒 Security & Optimization Plan

> ⚠️ 核心工作原则：先搜索互联网再动手
> 基于 OpenClaw GitHub issues, docs, Forbes/VentureBeat 报道, 社区讨论

## 当前风险评估

### 🔴 Critical: 服务器暴露

**问题：** 服务器 45.55.78.247 的 SSH (22) 和 Gateway 端口直接暴露在公网。
任何人可以：
- 尝试 SSH 暴力破解
- 扫描 Gateway WebSocket 端口
- 如果 Gateway 没设 auth，直接控制你的 agent

**证据：**
- VentureBeat: "OpenClaw proves agentic AI works. It also proves your security model doesn't."
- Forbes: "OpenClaw Introduces Secure Hosted Platform" (暗示自托管有风险)
- The Register: "Clawdbot sheds skin... can't slough off security issues"
- VentureBeat: "Infostealers added Clawdbot to their target lists"

**解决方案（按优先级）：**

#### 1. 立即：UFW 防火墙
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh          # 后续改为非标准端口
sudo ufw allow 443/tcp      # HTTPS if needed
# 不要开放 gateway 端口给公网！
sudo ufw enable
```

#### 2. SSH 加固
```bash
# /etc/ssh/sshd_config：
Port 2222                    # 换掉默认 22
PermitRootLogin no
PasswordAuthentication no    # 只允许 key 登录
MaxAuthTries 3
AllowUsers clawdbot

# fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

#### 3. Gateway 认证
```json5
{
  gateway: {
    bind: "loopback",         // 只监听 127.0.0.1
    auth: {
      mode: "token",          // 或 "password"
    },
    tailscale: { mode: "serve" }  // 推荐
  }
}
```

#### 4. Tailscale（推荐长期方案）
- Gateway 只绑定 loopback
- 通过 Tailscale Serve 安全暴露 UI
- SSH 也走 Tailscale（关闭公网 22）
- **零信任架构，免费方案够用**

---

### 🟡 High: Token 浪费

**问题：** GitHub #1594 — 用户 20-30 条消息烧完限额
- 大量 tool output 拖入上下文
- 6M tokens/小时，input 3.4M，cache 2.8M

**我们的情况：**
- Kalshi scanner 返回大量数据
- 每次注入 AGENTS.md + SOUL.md + memory 等
- Opus 价格是 Sonnet 的 5x

**解决方案：**

#### Token 节省行动

| 行动 | 预计节省 | 难度 |
|------|---------|------|
| 心跳用 Sonnet | ~70% heartbeat 成本 | 低 |
| 子 agent 用 Sonnet | ~70% 子任务成本 | ✅ 已在做 |
| 工具输出截断 | ~30% 上下文 | 低 |
| 精简 AGENTS.md | ~20% 系统提示 | 中 |
| 大查询写文件不返回 | ~40% 某些场景 | 中 |

---

### 🟡 High: Multi-Model 支持

**当前可用：**
- `/model <model>` — 切换 session 模型
- `session_status(model=...)` — per-session override
- spawn 子 agent 时指定 model

**推荐模型分配：**

| 场景 | 模型 | 理由 |
|------|------|------|
| 主对话 (Jason) | Opus | 最高质量 |
| 心跳/Cron | Sonnet | 重复检查 |
| 子 Agent | Sonnet | 编码够用 |
| 群聊 | Sonnet | 轻量交互 |
| 快速查询 | Haiku/Flash | 简单问答 |

**未来 — 自动路由 (PR #5873)：**
```json5
{
  models: {
    routing: {
      rules: [
        { match: { isCron: true }, model: "anthropic/claude-sonnet-4" },
        { match: { sessionKeyPrefix: "subagent:" }, model: "anthropic/claude-sonnet-4" },
        { match: { channel: "discord" }, model: "anthropic/claude-sonnet-4" },
        { match: { lane: "main" }, model: "anthropic/claude-opus-4-5" },
      ]
    }
  }
}
```

---

### 🟡 数据泄露风险

- ✅ MEMORY.md 只在 main session 加载
- ⚠️ 敏感 API key 不要放环境变量（用 gateway secret store）
- ⚠️ 群聊 prompt injection 风险

---

## 社区发现的其他风险

1. **Infostealer** — 恶意软件已将 Clawdbot 加入目标，窃取配置和 API key
2. **Agent 劫持** — Gateway 无认证 = 任何人可控制你的 agent
3. **Supply chain** — npm 依赖投毒
4. **Prompt injection** — 群聊中恶意指令注入
5. **数据外泄** — Agent 有邮件/日历权限，被劫持后果严重

---

## 安全加固路线图

### Phase 1: 今天（紧急）
- [ ] 服务器配置 UFW 防火墙
- [ ] SSH key-only + fail2ban
- [ ] 确认 Gateway auth token
- [ ] 检查所有开放端口

### Phase 2: 本周
- [ ] 安装 Tailscale
- [ ] SSH 换端口
- [ ] 配置模型路由
- [ ] 开启使用量日志

### Phase 3: 持续
- [ ] 定期安全审计
- [ ] Token 使用量监控
- [ ] 异常登录告警

---

## Token Optimization — Implemented Actions

### 1. Cache Warming (from docs)
Heartbeat interval should be just under Anthropic cache TTL to avoid re-caching:
```yaml
agents.defaults.heartbeat.every: "55m"   # keeps 1h cache warm
agents.defaults.models."anthropic/claude-opus-4-5".params.cacheRetention: "long"
```
**Jason TODO:** Add to openclaw.json when configuring Gateway.

### 2. Sub-agents for Heavy Work
- Kalshi full scan → spawn with Sonnet
- Research tasks → spawn with Sonnet  
- Only main conversation uses Opus

### 3. Workspace File Budget (~12.6K chars injected per turn)
- AGENTS.md: 8.5K ← largest, but essential guidance
- SOUL.md: 1.7K
- TOOLS.md: 1.1K
- Others: 1.3K combined
- Under 20K limit. No action needed yet.

### 4. Session Pruning (from docs)
Configure `cache-ttl` pruning to trim old tool outputs:
```yaml
agents.defaults.contextPruning:
  mode: "cache-ttl"
  ttl: "1h"
```

### 5. Compaction
Already using auto-compaction. Manual `/compact` when sessions get long.

---

## 歸藏教程要点 (来源: @op7418)

- `openclaw configure` — 命令行配模型最省事
- `openclaw.json` 中 `agents.fallbacks` — 控制模型降级链
- `/model` — 聊天中切换模型
- `/new` — 切模型前开新窗口
- 国产模型可用: Kimi K2.5, Minimax M2.1, GLM

*Updated: 2026-02-01 | Sources: OpenClaw docs, GitHub #1594 #5873 #5949, Forbes, VentureBeat, The Register, @op7418*
