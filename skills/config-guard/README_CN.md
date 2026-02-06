# Config Guard 🛡️

[🇺🇸 English](./README.md)

[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://clawdhub.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](./SKILL.md)

## 防止 AI 改错配置把自己搞崩。

> Prompt 是建议，代码是法律。

OpenClaw 的 AI agent 能直接改 `openclaw.json`——控制网关、频道、模型、工具的核心配置。改错一个字段，网关崩溃，agent 下线，远程没法修。

这个 skill 就是防这个的。

## 血泪教训

真实事故（全部发生在同一天）：

| 发生了什么 | 根本原因 |
|---|---|
| 网关更新后崩溃 | AI 加了不存在的配置字段（`auth`、`fallbacks`） |
| 模型找不到 | AI 写了 `claude-sonnet-4.5`（点号）而不是 `claude-sonnet-4-5`（连字符） |
| Telegram 断了 | 改配置时把频道配置整段删了 |
| browser.profiles 报错 | AI 忘了必填的 `color` 字段（必须是 hex） |
| Plugin SDK 找不到 | 更新后模块路径变了，没有验证拦截 |

**7 个连锁故障，1 个根因：AI 不知道正确的配置格式，它在猜。**

## 功能

### 改配置之前：
1. **自动备份** — 改之前先存一份带时间戳的备份
2. **JSON 语法检查** — 拦截格式错误的 JSON
3. **Schema 验证** — 必填字段、类型、合法值
4. **语义检查** — 专抓 AI 容易犯的错：
   - 模型名用点号不用连字符
   - 缺少必填字段（`browser.profiles.color`）
   - 不存在的顶层 key
   - 敏感字段里放了占位符
5. **关键字段变更检测** — 如果 Telegram 频道、auth token、工具黑名单被改了会警告

### 改配置之后：
6. **网关健康检查** — 轮询 30 秒等网关恢复
7. **自动回滚** — 网关起不来就自动恢复备份

## 快速开始

```bash
# 通过 ClawHub 安装
clawdhub install config-guard

# 或者直接 clone
git clone https://github.com/jzOcb/config-guard
```

### 使用

```bash
# 验证当前配置
bash scripts/config-guard.sh check

# 验证 → 备份 → 应用 → 检查（失败自动回滚）
bash scripts/config-guard.sh apply --restart

# 对比当前配置和上次备份的差异
bash scripts/config-guard.sh diff

# 紧急回滚
bash scripts/config-guard.sh rollback
```

### 作为 git hook

```bash
cp scripts/pre-config-hook.sh /path/to/repo/.git/hooks/pre-commit
```

## 检查项

| 检查 | 能抓到什么 |
|---|---|
| JSON 语法 | 格式错误、多余逗号、key 没加引号 |
| 未知顶层 key | AI 瞎编的字段，如 `fallbacks`、`auth` |
| 模型名格式 | `claude-sonnet-4.5` → 应该是 `claude-sonnet-4-5` |
| browser.profiles.color | 缺少必填字段、非 hex 值 |
| 占位符值 | 敏感字段里的 `your-token-here`、`sk-xxx` |
| 空主模型 | 没配模型 = agent 不能思考 |
| Telegram 频道被删 | 频道配置被悄悄删除 |
| Auth token 被删 | 网关认证被意外删除 |
| 工具黑名单变更 | 安全相关的工具被从 deny list 移除 |

## AI Agent 使用规范

**改 openclaw.json 的强制流程：**

1. 改之前先跑 `config-guard.sh check`
2. 不确定的字段名不要猜 — 用 `gateway config.schema` 查
3. 一次只改一个字段
4. 改完跑 `config-guard.sh apply --restart`
5. 网关挂了 → `config-guard.sh rollback`

## 依赖

- `bash` 4+
- `python3`
- `curl`

## 🛡️ AI Agent 安全套件

| 工具 | 防止什么 |
|------|---------|
| **[agent-guardrails](https://github.com/jzOcb/agent-guardrails)** | AI 重写已验证代码、泄露密钥、绕过标准 |
| **[config-guard](https://github.com/jzOcb/config-guard)** | AI 写错配置、搞崩网关 |
| **[upgrade-guard](https://github.com/jzOcb/upgrade-guard)** | 版本升级破坏依赖、无法回滚 |
| **[token-guard](https://github.com/jzOcb/token-guard)** | Token 费用失控、预算超支 |
| **[process-guardian](https://github.com/jzOcb/process-guardian)** | 后台进程悄悄死掉、无自动恢复 |

📖 **完整故事：** [我审计了自己的 AI agent 系统，发现漏洞百出](https://x.com/xxx111god/status/2019455237048709336)

## 许可

MIT
