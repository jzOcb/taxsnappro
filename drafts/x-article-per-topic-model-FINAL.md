# FINAL — Ready to Post

**X Handle:** @xxx111god
**Language:** 中文
**Type:** Article (quote repost @Tz_2022)
**Image:** Jason's Topics screenshot ✅

---

## Quote Repost 短推文（附Article链接）:

@Tz_2022 的 Topics 并发指南很赞👆但有个杀手级功能很多人漏了：

每个 Topic 可以用不同的模型。

我的群：8个Topic，3种模型混用。
🧠 Opus 做决策
⚡ Sonnet 干活
💰 Haiku 监控

Token 成本降 60-70%，关键任务质量不降。

详见👇

---

## Article 正文:

# 同一个群，不同 Topic 用不同模型 — Clawdbot 省钱秘籍

@Tz_2022 这篇 Topics 并发指南写得很好（推荐没看过的先看原帖）。

但有一个杀手级功能很多人不知道：

> 每个 Topic/Session 可以单独设置不同的 AI 模型。

这意味着什么？你可以在一个群里同时跑 Opus、Sonnet、Haiku，按需分配。

[插入 Jason 的 Topics 截图]

## 为什么这很重要？

Opus 很强，但也很贵。如果所有 Topic 都跑 Opus，你的 token 预算会像火箭一样燃烧 🚀

聪明的做法：按任务复杂度分配模型。

## 我的实际设置

我的群有 8 个 Topic，跑 3 种模型：

💡 新项目 idea → Opus
用来做深度研究、分析竞品、策略讨论。这种需要"动脑子"的活，必须用最强的。

👮 Market Monitor → Opus
交易信号、市场分析。钱相关的决策不能省。

💬 Chat → Sonnet
日常聊天、快速问答。Sonnet 性价比最高，质量完全够用。

📁 Kanban → Sonnet
项目管理、进度更新。不需要 Opus 级别的推理。

📺 X Post → Sonnet
内容创作、社交媒体。Sonnet 写东西已经很好了。

🔴 Rednote → Sonnet
小红书相关任务。

📊 Usage Monitor → Haiku
纯数字监控——查 token 用量、系统状态。最便宜的就够。

# TODO → Haiku
简单的任务管理、提醒。

## 效果

同一个群，8 个 Topic 并行，3 种模型混用。

• 需要深度思考的 → Opus（贵但值）
• 日常工作 → Sonnet（性价比之王）  
• 纯监控 → Haiku（几乎不花钱）

整体 token 成本降低约 60-70%，但关键任务的质量完全没降。

## 怎么设置？

三种方法，从简单到高级：

### 方法 1：直接在 Topic 里用命令

在任意 Topic 里输入：

/model claude-3-5-haiku-latest

用 /status 可以查看当前 Topic 用的是什么模型。

最简单，适合大多数人。

### 方法 2：跟 Clawdbot 说

直接跟它说："把这个 Topic 的模型改成 Haiku"。

它会自己改配置，不需要你碰任何文件。

### 方法 3：改配置文件

在 clawdbot.json 里按 Topic 设置默认模型：

```json
{
  "channels": {
    "telegram": {
      "groups": {
        "-100xxxxxxxxxx": {
          "topics": {
            "49": { "model": "claude-3-5-haiku-latest" },
            "3": { "model": "claude-opus-4-5" }
          }
        }
      }
    }
  }
}
```

适合想精确控制每个 Topic 的人。

## 我的模型选择原则

• 深度分析、策略制定 → Opus（推理能力最强）
• 代码、内容创作、日常工作 → Sonnet（性价比最高）
• 监控、通知、简单查询 → Haiku（速度快、成本低）
• 不确定的新任务 → 先用 Sonnet，需要时升级

## 进阶玩法

1. Cron 任务也可以指定模型 — 定时扫描、监控报告这种用 Haiku 就够，不要浪费 Opus
2. Sub-agent 用不同模型 — 主 session 用 Opus 思考，spawn 出来的 sub-agent 用 Sonnet 干活，成本直接砍半
3. 同一个 Topic 可以随时切换 — /model 命令即时生效，不需要重启

## 总结

Topics 不只是"并发多任务"，更是"分级用模型"。

一个群 = 多条车道 = 每条车道不同引擎。

这才是 Clawdbot Topics 的完全体 💪

---

## Checklist:
- [x] Article 正文定稿
- [x] Quote repost 短推文定稿
- [x] Topics 截图 ✅
- [x] X handle: @xxx111god
- [x] 语言: 中文
- [ ] Jason 发布
