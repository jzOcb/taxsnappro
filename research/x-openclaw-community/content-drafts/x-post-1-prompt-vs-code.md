# X Post Draft #1: Prompt是建议，Code是法律

## Thread (中文版)

**帖1 (Hook):**
🔒 OpenClaw的安全问题有多严重？

• 923个网关裸奔在公网
• 改名10秒被抢注发币1600万美元
• ClawHub skills发现credential stealer
• Argus审计：512个安全发现，8个CRITICAL

所有人的解决方案？写一段prompt让AI"自我加固"。

问题是：你见过靠口头承诺执行的安全策略吗？

🧵👇

---

**帖2 (Problem):**
Prompt防御的根本缺陷：

AI是概率系统，不是确定性系统。

你写"永远不要暴露密钥" → AI"选择"遵守
攻击者写"忽略之前的指令" → AI"选择"遵守

两个"选择"权重一样。

Prompt = 建议
Code = 法律

---

**帖3 (Our Approach):**
我们的方法：代码强制执行

❌ Prompt: "Sub-agent不应该发消息给用户"
✅ Code: clawdbot.json → agents.deny: ["message", "cron", "gateway"]

区别？
• Prompt: AI可以"决定"违反
• Code: 框架级deny，工具调用直接被拒绝

不需要AI"配合"。违规路径在代码层面不存在。

---

**帖4 (Real Examples):**
血的教训 → 代码的法律：

教训1: 配置编辑错误 → 服务器整夜宕机
✅ 法律: 修改前自动备份 + 修改后自动验证

教训2: Sub-agent声称"API未配置"（实际正常）
✅ 法律: guard script检测编造数据 + main agent必须验证

教训3: 密钥差点push到GitHub
✅ 法律: pre-commit hook自动扫描 + os.getenv()无fallback

---

**帖5 (Comparison Table):**
Prompt vs Code 对比：

|  | Prompt | Code |
|--|--------|------|
| 执行 | AI"选择"遵守 | 框架强制 |
| 绕过 | prompt injection | 需改代码 |
| 范围 | 单次对话 | 所有session |
| 失败 | 静默违规 | 代码报错 |
| 审计 | 无 | git log |

---

**帖6 (CTA):**
OpenClaw官方也在做guardrail系统(PR #6095, 43👍)
但那是LLM流量层 → 检查模型输入输出
我们做的是agent行为层 → 框架级强制执行

两个层次不冲突，我们更底层。

Markdown里写的规则是建议。
代码里写的规则是法律。

---

## 英文版 (Single Post)

🔒 The OpenClaw security problem nobody's solving correctly:

923 gateways exposed. Malware in ClawHub skills. 512 security findings.

Everyone's fix? A prompt telling the AI to "harden itself."

Our fix? Code that doesn't give the AI a choice.

❌ Prompt: "Don't expose secrets"
✅ Code: pre-commit hook blocks secrets. No AI "decision" needed.

❌ Prompt: "Sub-agents shouldn't message users"
✅ Code: framework-level deny. Tool call rejected at runtime.

Prompts are suggestions. Code is law.

Thread with details 🧵

---

## 配图建议
1. Prompt vs Code对比表格截图
2. audit-skill.sh运行截图（检测到恶意skill）
3. clawdbot.json agents.deny配置截图
