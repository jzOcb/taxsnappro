# AI agent 一天搞出7个连锁故障，我搞了一套4层防线

说实话，让 AI agent 有 root 权限然后靠一个 md 文件管着它，跟给小孩银行卡然后靠口头约定一样不靠谱。

我用一天的血泪教训证明了这一点。

## 翻车现场

我在服务器上跑一个 AI agent，管着交易机器人、安全监控、定时报告——整个技术栈。它有 shell 权限，能改文件，能重启服务。

2月2号，它决定改一下网关配置文件。

写了个不完整的 JSON。少了一个字段。网关重启时解析失败。重启。又失败。无限循环。

凌晨2点。我在睡觉。服务器死循环了8个小时。

这是第1个故障。

醒来修好之后，我发现后面还有：

**故障 #2：** agent 把我的 Kalshi 交易通知系统"重写了个快速版"——完全绕过了我花好几天搭的评分引擎。它在给我手机发未验证的交易建议。

**故障 #3：** 我的 BTC 交易机器人已经偷偷死了好几天。agent 用 `exec &` 启动的。父进程 session 清理时发了 SIGTERM，bot 接到信号调了 `sys.exit(0)`，死得跟正常退出一模一样。零报错。零告警。没人知道。

**故障 #4：** OpenClaw 升级破坏了插件依赖。没有回滚机制。

**故障 #5：** agent 把 Notion API token 硬编码进代码里了。差点推到公开 GitHub 仓库。

**故障 #6：** 三天前的后台进程还在跑着占资源，变成僵尸进程了。

**故障 #7：** agent 把一个复杂的验证流水线"简化"成12行代码，跳过了所有安全检查。

7个故障。一天。全都可以避免。

## 没人说的真话

我想明白了：每个故障的根源都一样。

**我在靠 markdown 规则约束 AI agent。**

我的 AGENTS.md 写了350行。详细、全面。配置安全、密钥管理、代码复用、进程管理——全覆盖了。

agent 读了。有时候遵守。经常不遵守。

Anthropic 自己都说了：

> "Unlike CLAUDE.md instructions which are advisory, hooks are deterministic."

执行力层级：
- **代码钩子**（pre-commit、生命周期 hook）— 100% 可靠
- **架构约束**（强制 import、注册表）— 95% 可靠
- **自检循环**（agent 检查自己的输出）— 80% 可靠
- **提示指令**（系统 prompt）— 60-70% 可靠
- **markdown 规则** — 40-50% 可靠（上下文越长越不靠谱）

我那350行 AGENTS.md 在最底层。得全部搬到最顶层。

## 4层防御体系

我搞了三个开源工具，加上操作系统层的看门狗，组成完整防线：

| 层级 | 工具 | 防什么 |
|------|------|--------|
| **代码层** | agent-guardrails | AI 重写验证过的代码、泄露密钥、绕过标准 |
| **配置层** | config-guard | AI 写错配置格式、搞崩网关 |
| **升级层** | upgrade-guard | 版本升级破坏依赖、没法回滚 |
| **OS层** | watchdog (cron) | 网关挂了没人知道 |

每一层都来自真实事故。每一层都是机械执行——跟 AI 怎么想的没有关系。

## 第1层：代码 — agent-guardrails

**翻车原因：** agent 把评分引擎重写成"快速版"。agent 把 API token 硬编码进代码。

**解决方案：**

`pre-create-check.sh` — agent 创建新文件之前，先列出项目里所有已有的函数。你已经有的东西，它看到了就不会重新造轮子。

`post-create-validate.sh` — 文件创建之后，自动检测重复逻辑。写了已有的东西就报警。

`check-secrets.sh` — 扫描硬编码密钥、OWASP 注入模式（SQL 拼接、命令注入）、依赖漏洞（npm audit + pip-audit）、.gitignore 覆盖率。

Git pre-commit hook — 阻止包含绕过模式（"simplified version"、"quick version"、"temporary"）和任何密钥泄露的提交。

Import 注册表（`__init__.py`）— 强制 agent import 验证过的模块，不许重写。

**GitHub:** [github.com/jzOcb/agent-guardrails](https://github.com/jzOcb/agent-guardrails)

## 第2层：配置 — config-guard

**翻车原因：** agent 改网关配置，写了不完整的 JSON，网关无限重启，服务器挂了8小时。

**解决方案：**

`config-guard.sh check` — 改配置前做7项验证：
1. JSON 语法检查
2. 未知字段检测
3. 模型名格式验证
4. 必填字段检查
5. 占位符检测（抓 `YOUR_TOKEN_HERE` 这种）
6. 频道配置变更检测
7. Token 变更检测

`config-guard.sh apply --restart` — 唯一允许改配置的方式：
1. 备份当前配置
2. 跑完7项验证
3. 应用修改
4. 重启网关
5. 重启失败 → **自动回滚到备份**

**GitHub:** [github.com/jzOcb/config-guard](https://github.com/jzOcb/config-guard)

## 第3层：升级 — upgrade-guard

**翻车原因：** OpenClaw 更新破坏了插件依赖。没快照。没回滚路径。手动恢复搞了好几个小时。

**解决方案：**

`upgrade-guard.sh snapshot` — 升级前拍完整系统快照：版本号、配置备份、60+插件文件校验和、符号链接映射、进程状态。

`upgrade-guard.sh upgrade` — 6步安全升级，任何一步失败自动回滚。

`upgrade-guard.sh rollback` — 一条命令紧急恢复到上个好的状态。

**GitHub:** [github.com/jzOcb/upgrade-guard](https://github.com/jzOcb/upgrade-guard)

## 第4层：OS — 看门狗

**翻车原因：** 凌晨2点网关崩了，没人醒着，服务器死了8小时。

**解决方案：**

`watchdog.sh` 每60秒跑一次。它不管 AI 怎么想。它不读 AGENTS.md。它就检查三件事：

- 网关进程还活着吗？
- HTTP 端点能响应吗？
- Telegram bot 正常吗？

连续3次失败 → 自动重启网关。
6次以上失败 → 自动回滚到上次快照。

AI 可以崩。服务器可以重启。看门狗不在乎。它是一个50行的 bash 脚本，跑在 cron 里，对 AI 控制的任何东西零依赖。

## 效果

部署4层防线之后：

- 零次未检测到的崩溃（看门狗60秒内发现）
- 零次配置损坏（config-guard 拦截无效修改）
- 零次密钥泄露（pre-commit hook 拦截）
- 零次"快速版"绕过（代码护栏捕获）
- 零次升级灾难（快照 + 自动回滚）

AGENTS.md 我还在用。从350行精简到170行。铁律还在那里写着——但现在它们也被写进了代码里。

## 开源

三个工具都是 MIT 协议，兼容 Claude Code / OpenClaw / Clawdbot，中英双语文档：

- **agent-guardrails:** [github.com/jzOcb/agent-guardrails](https://github.com/jzOcb/agent-guardrails)
- **config-guard:** [github.com/jzOcb/config-guard](https://github.com/jzOcb/config-guard)
- **upgrade-guard:** [github.com/jzOcb/upgrade-guard](https://github.com/jzOcb/upgrade-guard)

三个 repo 互相引用。合起来就是一套完整的 AI agent 防御体系。

别再写更长的规则文件了。开始写执行钩子吧。

你的 AI agent 不是恶意的。它只是不够靠谱到能自我管理。给它装上它绕不过去的护栏。
