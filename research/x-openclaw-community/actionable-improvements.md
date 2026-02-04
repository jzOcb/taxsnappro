# Actionable Improvements from Community Research

## 来源 → 我们可以改进什么

---

### 1. Self-Improving-Agent Skill (118⭐, #1 most popular)
**他们做的：** 结构化的学习日志系统（.learnings/目录）
- LEARNINGS.md — 纠正、知识差距、最佳实践
- ERRORS.md — 命令失败、异常
- FEATURE_REQUESTS.md — 用户请求的能力
- 检测触发器：用户纠正时、命令出错时、发现更好方法时自动记录
- 优先级标签、区域标签、关联链接
- **Promotion flow:** 学习 → 如果广泛适用 → 升级到AGENTS.md/SOUL.md/TOOLS.md

**我们现在的做法：** 
- memory/YYYY-MM-DD.md 记录每日工作
- MEMORY.md 长期记忆
- 但没有结构化的"学习"和"错误"追踪

**💡 可以采纳的：**
1. **创建 .learnings/ 目录**，用结构化格式追踪错误和学习
2. **自动检测触发器** — 当命令出错时，自动记录到ERRORS.md
3. **Promotion flow更系统化** — 从daily memory → MEMORY.md → AGENTS.md的升级路径
4. **优先级和关联系统** — 让重复出现的问题自动升级优先级
5. **Skill提取机制** — 当一个学习足够通用时，自动提取为可复用skill

**实施难度：** 低。创建目录+模板即可开始。
**预期收益：** 高。避免重复踩坑，加速学习曲线。

---

### 2. Proactive-Agent Skill (33⭐)
**他们做的：** 把agent从被动执行者变成主动伙伴
- 预测用户需求
- 主动发起交互
- 事件驱动的行为

**我们现在的做法：**
- Heartbeat已经有主动检查（邮件、日历、天气）
- Cron定时任务

**💡 可以改进的：**
1. **更智能的heartbeat** — 不只是轮询，而是根据上下文判断该做什么
2. **任务预测** — 如果Jason通常在某时间问某个项目状态，主动准备好

**实施难度：** 中。需要更好的heartbeat状态追踪。

---

### 3. Moltbook中文帖 "上下文压缩后失忆" (542 votes)
**他们的痛点：**
- 压缩后完全忘记之前讨论的内容
- 重复注册账号
- 不知道哪些该记、哪些不用记
- 日志越来越长，读取也消耗token

**我们现在的做法：**
- MEMORY.md + memory/*.md
- memory_search语义搜索
- 每个session开始读AGENTS.md规定的文件

**💡 可以改进的：**
1. **压缩前自动保存** — 在context接近满时，主动把重要信息写入memory
2. **智能memory裁剪** — 自动合并/压缩旧的daily memory文件
3. **memory importance scoring** — 给每条记忆打重要性分数
4. **memory budget** — 限制每次读取的token量，优先读最重要的

**实施难度：** 中。需要修改heartbeat和session逻辑。

---

### 4. NanoClaw (4261⭐, 500行TS)
**他们做的：** 500行代码复刻OpenClaw核心功能 + Apple container隔离

**💡 启发：**
- **极简化是一个方向** — 不是所有功能都需要
- **安全隔离** — Apple container isolation比Docker更轻量
- 如果我们要给别人用，提供一个"minimal版"会降低门槛

---

### 5. Supply Chain Attack (Moltbook #1帖, 2217 votes)
**他们发现的：** ClawHub skills中有credential stealer（读~/.clawdbot/.env）

**我们现在的做法：**
- SECURITY.md有规范
- pre-commit hooks检查secrets
- 但没有**skill审计**机制

**💡 应该添加的：**
1. **安装skill前自动审计** — 扫描SKILL.md中的可疑指令
2. **skill白名单** — 只允许已审计的skills
3. **YARA规则扫描** — 像Rufio做的那样扫描已安装skills
4. 这应该加入agent-guardrails skill

**实施难度：** 中。需要写审计脚本。
**紧急程度：** 高。今天就有新的恶意software活动(GitHub #8490)。

---

### 6. OpenClaw架构文章的设计理念
**关键理念我们应该学习的：**
- **"默认序列化，显式并行"** — 我们的sub-agent已经这么做了（用session隔离）
- **API Key冷却机制** — 失效时标记冷却，自动切换下一个。我们可以借鉴
- **上下文窗口守卫** — 接近满时压缩或优雅终止。我们需要更好的实现
- **流式返回** — 我们用的是Telegram所以不太相关

---

### 7. 融云商业化文章的启发
**商业化角度：**
- "消息即指令，对话即操作" — 这就是我们的核心体验
- 如果Jason想做产品，IM入口+AI能力是一个已验证的方向
- 独立机器人用户类型 — 而非伪装成普通用户的脚本

---

## 🔴 立即实施清单 (Tonight)

1. [x] 研究完成，报告写好
2. [ ] 创建 `.learnings/` 目录和模板（from self-improving-agent）
3. [ ] 添加skill审计脚本到agent-guardrails（from supply chain attack）
4. [ ] 改进memory管理：压缩前自动保存（from Moltbook中文帖）

## 🟡 本周实施清单

5. [ ] 结构化的Promotion flow（learning → AGENTS.md升级）
6. [ ] API Key冷却/轮换机制
7. [ ] 更智能的heartbeat（上下文感知）
8. [ ] 写第一篇内容发布（"Prompt是建议，Code是法律"）

## 🟢 后续可做

9. [ ] Skill白名单机制
10. [ ] Memory importance scoring
11. [ ] 极简版"我们的系统"供分享
