# LEARNINGS.md — 持续改进日志

记录纠正、知识差距、最佳实践。当某个学习广泛适用时，升级到 AGENTS.md / SOUL.md / TOOLS.md。

---

## [LRN-20260204-001] best_practice

**Logged**: 2026-02-04T06:30:00Z
**Priority**: high
**Status**: pending
**Area**: research

### Summary
社区研究不只是素材收集，更重要的是学习和应用改进

### Details
Jason指出研究的目标不只是写文章，而是理解社区在做什么、学习他们的好做法、改进我们自己的系统。之前研究模式偏向"记录+报告"，应该转向"学习+应用"。

### Suggested Action
每次研究后都创建actionable-improvements.md，列出具体可实施的改进项。

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
Self-improving-agent的结构化学习系统（.learnings/）是全ClawHub最受欢迎的skill(118⭐)

### Details
它的核心理念：
1. 错误和学习不应该散落在daily memory里，应该有专门的结构化追踪
2. 检测触发器自动化（命令出错→记录，用户纠正→记录）
3. Promotion flow：学习 → 如果重复/广泛适用 → 升级到永久文件
4. 关联链接：相似问题互相引用，重复出现自动升优先级

### Suggested Action
采纳这个系统，创建.learnings/目录。但不完全照搬，保留我们的简洁性。

### Metadata
- Source: community_research
- Related Files: /tmp/skill-study/self-improving-agent/SKILL.md
- Tags: self-improvement, memory, community

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

---
