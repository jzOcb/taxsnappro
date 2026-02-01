# 🔒 OpenClaw Hardening Kit

安全加固 + Token优化，一键搞定你的 OpenClaw / Clawdbot 部署。

[🇬🇧 English](./README.md)

> **适用人群：** 在VPS/云服务器上跑OpenClaw的用户。本地Mac用户也可参考Token优化部分。

---

## 为什么需要这个？

OpenClaw默认配置**不安全**。官方文档原话：

> *"Running an AI agent with shell access on your machine is... spicy. There is no 'perfectly secure' setup."*

具体风险：
- SSH密码登录暴露 → 暴力破解
- Gateway端口公网可达 → 未授权访问
- API Key明文存储 → 泄露风险
- Session日志明文 → 隐私泄露
- 全部流量走最贵模型 → 烧钱

**本仓库提供一套经过实战验证的加固方案。**

---

## 快速开始

```bash
git clone https://github.com/jzOcb/openclaw-hardening.git
cd openclaw-hardening

# 1. 审计当前安全状况
bash security/audit.sh

# 2. 一键加固（交互式，每步确认）
sudo bash security/harden.sh

# 3. 应用Gateway安全配置
cp config/openclaw-secure.json5 ~/.openclaw/openclaw.json.example
# 手动合并到你的 openclaw.json

# 4. 安装推荐skills
bash setup/install-skills.sh
```

---

## 📁 仓库结构

```
openclaw-hardening/
├── README.md                    # 你在看的这个
├── security/
│   ├── audit.sh                 # 安全审计（9项检查）
│   └── harden.sh                # 一键加固（UFW+SSH+fail2ban+Tailscale）
├── config/
│   ├── openclaw-secure.json5    # Gateway安全配置模板
│   └── token-optimization.json5 # Token优化配置模板
├── setup/
│   └── install-skills.sh        # 推荐skills一键安装
└── docs/
    ├── SECURITY.md              # 安全加固详解
    ├── TOKEN-OPTIMIZATION.md    # Token优化详解
    └── MODEL-ROUTING.md         # 多模型配置指南
```

---

## 🛡️ 安全加固

### audit.sh — 审计脚本

检查9项安全指标：

| # | 检查项 | 说明 |
|---|--------|------|
| 1 | SSH配置 | 端口、密码登录、Root登录 |
| 2 | 防火墙 | UFW是否启用 |
| 3 | fail2ban | 暴力破解防护 |
| 4 | 开放端口 | 不必要的端口暴露 |
| 5 | Gateway配置 | 绑定地址、认证模式 |
| 6 | Tailscale | 安全远程访问 |
| 7 | 凭证存储 | API Key明文检查 |
| 8 | 文件权限 | 配置和日志文件权限 |
| 9 | 浏览器控制 | 端口18791暴露检查 |

```bash
bash security/audit.sh
```

### harden.sh — 加固脚本

交互式执行，每步确认：

1. **UFW防火墙** — 只开SSH端口，拒绝其他入站
2. **SSH加固** — 改端口、禁密码、禁Root、限重试
3. **fail2ban** — 3次失败封IP 1小时
4. **Tailscale引导** — 安全远程访问（替代公网暴露）

```bash
sudo bash security/harden.sh
```

> ⚠️ **重要：** 跑harden.sh时保持当前SSH连接，先开第二个窗口测试新端口！

---

## 💰 Token优化

### 问题

OpenClaw默认用同一个模型处理所有任务。如果你用的是Claude Opus，每次心跳、每个sub-agent都在烧最贵的token。

### 方案：模型分层

| 任务类型 | 推荐模型 | 相对成本 |
|---------|---------|---------|
| 主对话 | Claude Opus 4.5 | $$$$$ |
| Sub-agent | Claude Sonnet 4 | $ |
| 心跳扫描 | Claude Sonnet 4 | $ |
| Fallback | Claude Sonnet 4 | $ |

### 配置

将以下内容合并到 `~/.openclaw/openclaw.json`：

```json5
{
  agents: {
    defaults: {
      // 主模型
      model: { primary: "anthropic/claude-opus-4-5" },
      
      // Sub-agent用便宜模型
      subagents: { model: "anthropic/claude-sonnet-4-5" },
      
      // 注意：fallbacks 在 2026.1.24-1 版本不支持
      // 需要时用 /model 命令手动切换
      
      // 心跳间隔（55min保持1h缓存热）
      heartbeat: { every: "55m" },
      
      // 自动裁剪旧tool输出
      contextPruning: { mode: "cache-ttl", ttl: "1h" },
    }
  }
}
```

### 效果

- 心跳不再烧Opus → **省5x**
- Sub-agent自动用Sonnet → **省5x**
- Cache warming减少重复缓存 → **省cache write费用**
- 预估总体节省 **30-50%**

### 进阶：手动切换

在聊天中随时切换模型：
```
/model              # 搜索可用模型
/model sonnet       # 切到Sonnet
/new                # 建议切模型前开新窗口
```

> 💡 来源：[歸藏(@op7418)的Clawdbot教程](https://x.com/op7418/status/2017647987854610930)

---

## 🔌 推荐Skills

我们精选了15个高价值skills：

| 分类 | Skill | 用途 |
|------|-------|------|
| 安全 | clawdbot-security-suite | 命令消毒、模式检测 |
| 基础设施 | digital-ocean | DO服务器管理 |
| 基础设施 | tailscale | Tailscale网络管理 |
| 金融 | polymarket | 预测市场数据 |
| 金融 | ibkr-trader | IBKR交易自动化 |
| 金融 | yahoo-finance | 股票财务数据 |
| 搜索 | brave-search | Brave搜索API |
| 搜索 | tavily | AI优化搜索 |
| 搜索 | last30days | 近30天Reddit/X/Web |
| 工具 | duckdb-en | SQL数据分析 |
| 工具 | youtube-summarizer | YouTube摘要 |
| 工具 | auto-updater | 自动更新 |
| 工具 | search | 通用网页搜索 |
| 维护 | skills-audit | Skills安全审计 |
| 文档 | clawddocs | 官方文档专家 |

```bash
bash setup/install-skills.sh
```

---

## 🙏 致谢

- [OpenClaw官方安全文档](https://docs.clawd.bot)
- [歸藏(@op7418)](https://x.com/op7418) — 模型配置教程
- [huangserva(@servasyy_ai)](https://x.com/servasyy_ai) — 安全隐患深度分析
- [VoltAgent/awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — Skills目录

---

## 📜 License

MIT — 随便用，注明出处就好。

---

## 🤝 贡献

欢迎PR！特别是：
- 更多安全检查项
- 其他云平台的加固脚本（AWS、Hetzner等）
- 更多Token优化技巧
- 国产模型配置指南（Kimi、Minimax、GLM）
