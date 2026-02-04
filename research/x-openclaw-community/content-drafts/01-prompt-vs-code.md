# 内容草稿 #1: "Prompt是建议，Code是法律"

## 核心论点
当全网都在教你用prompt让AI"自我加固"时，我们用代码钩子和框架级deny让AI"不得不服从"。

## 目标受众
- OpenClaw用户（特别是关注安全的）
- AI Agent开发者
- 中文tech社区（B站/SegmentFault/X）

## 文章结构

### 开头（Hook）
> "一夜爆火的OpenClaw让923个网关裸奔在公网上。CEO们纷纷预警：不要安装。ClawHub上发现了恶意skills注入base64编码的shell命令。
> 
> 所有人的解决方案？写一段prompt让AI自己给自己穿上防弹衣。
> 
> 问题是：你见过靠口头承诺执行的安全策略吗？"

### 第一部分：Prompt防御的根本缺陷
- AI是概率系统，不是确定性系统
- Prompt injection可以覆盖任何prompt规则
- 举例：SegmentFault那篇文章的"安全加固prompt"——看起来全面，但都是建议
- 数据支撑：Argus审计发现512个安全问题，其中255个密钥泄露

### 第二部分：代码是法律——我们的方法
**Iron Law #1: 配置修改必须验证**
```
血的教训：2026-02-02，一次错误的配置编辑导致服务器整夜宕机。
解决方案：不是写prompt说"小心配置"，而是：
- 修改前自动备份（代码强制）
- 修改后运行 clawdbot doctor（代码强制）
- gateway config.patch（框架级API，不允许手动编辑）
```

**Iron Law #2: 密钥绝不硬编码**
```
血的教训：Notion token差点push到公开GitHub。
解决方案：不是prompt说"不要暴露密钥"，而是：
- pre-commit hook自动扫描（代码拦截）
- os.getenv()无fallback值（代码强制失败）
- 发现泄露→立即报告+吊销（流程强制）
```

**Iron Law #3: Sub-agent输出永远不可信**
```
血的教训：Sub-agent声称"API未配置"，直接转发给用户，实际API完全正常。
解决方案：
- framework级别deny: sub-agent被禁止使用message、cron、gateway工具
- guard script: 完成后自动检测编造数据和路径泄露
- main agent必须验证后才转发
```

### 第三部分：机械执行 vs 道德约束
| | Prompt方法 | Code方法 |
|---|---|---|
| 执行保证 | AI"选择"遵守 | 框架强制执行 |
| 绕过可能 | prompt injection即可 | 需要修改代码 |
| 适用范围 | 单次对话 | 所有会话、所有agent |
| 失败模式 | 静默违规 | 代码报错+拦截 |
| 审计追踪 | 无 | git log + commit hooks |

### 第四部分：实战代码
展示几个关键脚本：
- `subagent-guard.sh`：检测编造数据
- `check-secrets.sh`：pre-commit密钥扫描
- `managed-process.sh`：进程生命周期管理
- `clawdbot.json` agents.deny配置

### 结尾
> "OpenClaw官方也在做guardrail系统（PR #6095，43个👍）。但那是LLM流量层的拦截——检查模型输入输出。
> 
> 我们做的是更底层的：agent行为层的强制执行。AI不需要"选择"遵守规则，因为违规的路径在代码层面就不存在。
> 
> Markdown里写的规则是建议。代码里写的规则是法律。"

## 发布策略
1. **X帖子（中文）**：核心论点 + 对比表格截图
2. **SegmentFault文章**：完整版
3. **B站视频**（如果Jason想做）：实操演示
4. **GitHub Discussion**：技术讨论版

## 关键数据引用
- 923个OpenClaw网关暴露在公网（来源：SegmentFault安全文章）
- 512个安全发现/8个CRITICAL（来源：Argus审计 GitHub #1796）
- ClawHub恶意software活动（来源：GitHub #8490，2026-02-04）
- 255个密钥泄露被扫描发现（来源：Argus审计）
- 改名10秒被抢注发币1600万美元（来源：SegmentFault）
