# LEARNINGS.md — 持续改进日志

记录纠正、知识差距、最佳实践。当某个学习广泛适用时，升级到 AGENTS.md / SOUL.md / TOOLS.md。

---

## [LRN-20260204-001] best_practice

**Logged**: 2026-02-04T06:30:00Z
**Priority**: high
**Status**: promoted
**Area**: research

### Summary
社区研究不只是素材收集，更重要的是学习和应用改进

### Details
Jason指出研究的目标不只是写文章，而是理解社区在做什么、学习他们的好做法、改进我们自己的系统。之前研究模式偏向"记录+报告"，应该转向"学习+应用"。

### Suggested Action
每次研究后都创建actionable-improvements.md，列出具体可实施的改进项。

### Resolution
- **Resolved**: 2026-02-04T06:45:00Z
- **Promoted**: SOUL.md补充 — 研究是为了学习改进，不是为了记录

### Metadata
- Source: user_feedback
- Tags: research, workflow, mindset

---

## [LRN-20260204-002] best_practice

**Logged**: 2026-02-04T06:35:00Z
**Priority**: high
**Status**: implementing
**Area**: infra

### Summary
Self-improving-agent的结构化学习系统是全ClawHub最受欢迎的skill(118⭐)

### Details
核心理念：
1. 错误和学习不应该散落在daily memory里，应该有专门的结构化追踪
2. 检测触发器自动化（命令出错→记录，用户纠正→记录）
3. Promotion flow：学习 → 如果重复/广泛适用 → 升级到永久文件
4. 关联链接：相似问题互相引用，重复出现自动升优先级

### Suggested Action
采纳这个系统，创建.learnings/目录。已实施。

### Metadata
- Source: community_research
- Tags: self-improvement, memory, community
- See Also: LRN-20260204-004

---

## [LRN-20260204-003] knowledge_gap

**Logged**: 2026-02-04T06:35:00Z
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary
X搜索需要登录cookie，所有nitter实例已关闭/被封

### Details
尝试了nitter.cz、nitter.privacydev.net、nitter.poast.org、nitter.1d4.us，全部不可用。
Google的site:x.com搜索也被反爬。fxtwitter API返回429。
结论：不配bird CLI的cookie就无法做X内容研究。

### Suggested Action
配置bird CLI的X cookie，或者在浏览器中登录X账号。

### Metadata
- Source: error
- Tags: x-twitter, research, tooling
- See Also: ERR-20260204-001

---

## [LRN-20260204-004] best_practice

**Logged**: 2026-02-04T06:42:00Z
**Priority**: critical
**Status**: implementing
**Area**: infra

### Summary
Proactive-Agent v3.0的WAL Protocol是解决上下文丢失的最佳方案

### Details
三个关键机制：
1. **WAL (Write-Ahead Logging)**: 发现用户纠正/偏好/决策时，先写文件再回复
2. **Working Buffer**: 上下文60%时开始记录每条交互到文件
3. **Compaction Recovery**: 压缩后按固定顺序恢复（buffer→state→daily→search）

这完美解决了Moltbook中文帖(542 votes)描述的所有问题：
- 压缩后失忆 → Working Buffer保留
- 不知道该记什么 → WAL自动检测触发器
- 日志太长 → SESSION-STATE.md只保留当前任务

### Suggested Action
1. 创建SESSION-STATE.md机制
2. 实现Working Buffer（60%阈值）
3. 在AGENTS.md中添加WAL规则

### Metadata
- Source: community_research (proactive-agent v3.0, 33⭐)
- Tags: memory, context, compaction, wal
- See Also: LRN-20260204-002

---

## [LRN-20260204-005] best_practice

**Logged**: 2026-02-04T06:50:00Z
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
Reflect skill的"Correct once, never again"理念和信号检测系统

### Details
Reflect v2.0的核心贡献：
1. **信号置信度**: HIGH(explicit correction) / MEDIUM(approved) / LOW(observation)
2. **分类映射**: 每种学习自动映射到应该更新的文件
3. **Skill-Worthy检测**: 5个质量门控判断是否值得提取为skill
4. **指标追踪**: acceptance rate, confidence breakdown等

与self-improving-agent的区别：
- self-improving是"记录一切"，reflect是"分析后提炼"
- reflect更适合session结束时回顾，self-improving更适合实时捕获

### Suggested Action
在session结束前增加"reflect"步骤，回顾本次对话的学习。

### Metadata
- Source: community_research (reflect-learn v2.0)
- Tags: self-improvement, reflection

---

## [LRN-20260204-006] best_practice

**Logged**: 2026-02-04T06:55:00Z
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary
Stock-analysis skill的多维度评分系统和rumor检测值得借鉴

### Details
stock-analysis v6.2 的设计：
- 8维度股票评分（技术面、基本面、动量、情绪等）
- Rumor Scanner：检测早期信号（M&A传闻、内部交易、分析师评级）
- Watchlist + Alerts：价格目标、止损、信号变化
- 快速模式（--fast跳过慢分析）

对我们Kalshi项目的启发：
- 多维度评分可以用于预测市场事件概率
- Rumor检测可以整合到我们的market scanner
- Watchlist模式可以用于持仓监控

### Suggested Action
研究如何将rumor检测整合到Kalshi扫描器中。

### Metadata
- Source: community_research (stock-analysis v6.2, 12⭐)
- Tags: trading, kalshi, market-analysis

---

## [LRN-20260204-007] best_practice

**Logged**: 2026-02-04T07:00:00Z
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
Capability-evolver的GEP Protocol（Gene Evolution Protocol）提供了一个结构化的自我进化框架

### Details
GEP Protocol核心组件：
- genes.json: 可重用的"基因"定义（进化方向）
- capsules.json: 成功案例胶囊（避免重复推理）
- events.jsonl: 追加式进化事件日志（树状结构）

核心流程：
1. 读取session日志 → 提取信号
2. 选择适用的gene和capsule
3. 构建进化prompt
4. 提取能力候选
5. 应用或review

关键安全设计：
- Mad Dog Mode（连续进化）需要显式启用
- Review Mode（人工确认）是推荐默认
- Git Sync作为安全网

### Suggested Action
考虑在我们的系统中实现类似的"capsule"机制——成功案例的结构化复用。

### Metadata
- Source: community_research (capability-evolver, 31K downloads)
- Tags: self-improvement, evolution, automation

---

---

## [LRN-20260204-008] best_practice

**Logged**: 2026-02-04T06:50:00Z
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary
memU (7.4K⭐) treats "memory as filesystem" — structured, hierarchical, instantly accessible

### Details
memU的核心设计：
- 文件夹=分类，文件=记忆项，符号链接=交叉引用
- 结构化：preferences/, relationships/, knowledge/, context/
- 主动预测用户意图（不等指令就行动）
- 减少token成本（缓存insights，避免重复LLM调用）

与我们的区别：
- 我们用flat daily files (memory/YYYY-MM-DD.md)
- memU用层级目录结构
- 我们可以从中学习：把memory按主题组织，而不只是按日期

### Suggested Action
考虑在memory/下增加主题子目录（如memory/projects/, memory/decisions/, memory/people/）

### Metadata
- Source: community_research (memU, 7419⭐)
- Tags: memory, architecture, filesystem

---

## [LRN-20260204-009] knowledge_gap

**Logged**: 2026-02-04T07:00:00Z
**Priority**: low
**Status**: pending
**Area**: infra

### Summary
ClawHub security-checker skill只有SKILL.md（prompt-based），没有实际代码

### Details
openclaw-skills-security-checker虽然描述了pattern detection和whitelist管理，
但实际安装后只有一个SKILL.md文件——完全依赖AI按照指令行事。
我们的audit-skill.sh是真正的可执行代码。
这证实了"Prompt是建议，Code是法律"的论点。

### Metadata
- Source: community_research
- Tags: security, code-vs-prompt


---

## [LRN-20260204-010] best_practice

**Logged**: 2026-02-04T06:55:00Z
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
OpenCloudOS文章展示了企业微信+QQ完整接入流程，关键是plugin生态

### Details
从SegmentFault文章学到：
1. 企业微信接入通过 `clawdbot plugins install @william.qian/simple-wecom`
2. QQ接入通过 `sliverp/qqbot` GitHub项目
3. 配置流程：安装plugin → config set channels → gateway restart
4. 运维场景（PHP-FPM假死检测+自动重启）是超强卖点
5. OpenCloudOS作为服务器OS推荐使用

对我们的价值：
- 说明plugin生态是扩展中国平台支持的关键路径
- 运维自动化是一个我们没探索的方向
- 企业微信+QQ接入教程已有，我们可以直接参考

### Metadata
- Source: community_research (SF article "AI运维同事")
- Tags: wechat, qq, enterprise, devops, plugin


---

## [LRN-20260204-011] knowledge_gap

**Logged**: 2026-02-04T06:55:00Z
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
OpenClaw进入Stabilisation Mode — 不再接受新feature PR，Skills是唯一扩展路径

### Details
Issue #5799 (21👍) 宣布：
- PR每两分钟一个，团队无法review
- 新feature requests会被自动关闭
- 只接受bug reports
- 推荐路径：Skills > CLIs/tooling > Fork
- "Build around OpenClaw, not into it"

对我们的影响：
1. 我们的agent-guardrails作为skill更有价值了（不需要改core）
2. 发布到ClawHub是正确策略
3. 任何需要core改动的想法都不现实
4. 稳定性是当前最大关注点

### Suggested Action
- 确认我们所有改进都是skill/config层面，不依赖core
- 尽快发布agent-guardrails到ClawHub
- 考虑把audit-skill.sh也包装成ClawHub skill

### Metadata
- Source: github_issue #5799
- Tags: openclaw, strategy, skills, stabilisation


---

## [LRN-20260204-012] knowledge_gap

**Logged**: 2026-02-04T07:00:00Z
**Priority**: high
**Status**: pending
**Area**: config

### Summary
OpenClaw v2026.2.2 (released TODAY) 加入了 agents.defaults.subagents.thinking 配置

### Details
新版本关键更新：
1. 飞书官方plugin支持（PR #7313，by openclaw-cn）
2. Web UI Agents dashboard（管理agent文件、工具、skills）
3. QMD backend for memory（新的可选memory系统）
4. **agents.defaults.subagents.thinking** — 可以设置默认sub-agent思考级别

对我们的影响：
- 应该检查并配置 subagents.thinking 以优化sub-agent表现
- 飞书官方支持说明中国市场已被官方重视
- QMD memory backend可能比我们当前的memory系统更好

### Suggested Action
1. 检查当前版本是否是最新
2. 配置 agents.defaults.subagents.thinking
3. 研究QMD memory backend是否值得采用

### Metadata
- Source: github_release v2026.2.2
- Tags: openclaw, release, config, memory

