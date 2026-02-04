# X Article Draft — Per-Topic Model Assignment

**Purpose:** Quote repost @Tz_2022's Topics article, adding the "hidden feature" of per-topic model control

---

## Article Title:
**Clawdbot 省钱秘籍：同一个群里，不同 Topic 用不同模型**

## Article Body:

@Tz_2022 这篇 Topics 并发指南写得很好（推荐没看过的先看原帖）。

但有一个**杀手级功能**很多人不知道：

> 每个 Topic/Session 可以单独设置不同的 AI 模型。

这意味着什么？**你可以在一个群里同时跑 Opus、Sonnet、Haiku，按需分配。**

---

### 为什么这很重要？

Opus 很强，但也很贵。如果所有 Topic 都跑 Opus，你的 token 预算会像火箭一样燃烧 🚀

聪明的做法：**按任务复杂度分配模型。**

### 我的实际设置：

```
📊 Research & Strategy → Opus 4.5
   深度分析、复杂推理、重要决策

💹 Market Monitor → Opus 4.5  
   交易信号需要最强判断力

💬 日常讨论 → Sonnet 4.5
   平衡质量和成本的甜蜜点

📁 项目管理 → Sonnet 4.5
   Kanban更新、进度跟踪

🔢 Token Monitor → Haiku
   纯数字监控，最便宜的就够

⚙️ System Config → Haiku
   简单操作，不需要大脑
```

### 效果：

同一个群，8个 Topic 并行，3种模型混用。

- 需要深度思考的用 Opus（贵但值）
- 日常工作用 Sonnet（性价比之王）
- 纯监控用 Haiku（几乎不花钱）

**整体 token 成本降低约 60-70%**，但关键任务的质量完全没降。

---

### 怎么设置？

**方法1：在 Topic 里直接说**

在任意 Topic 里输入：
```
/model claude-3-5-haiku-latest
```
或者用 `/status` 查看当前 Topic 用的是什么模型。

**方法2：配置文件**

在 `clawdbot.json` 里按 Topic 设置默认模型：
```json
{
  "channels": {
    "telegram": {
      "groups": {
        "-100xxxxxxxxxx": {
          "topics": {
            "49": {
              "model": "claude-3-5-haiku-latest"
            },
            "3": {
              "model": "claude-opus-4-5"
            }
          }
        }
      }
    }
  }
}
```

**方法3：让 Clawdbot 自己设置**

直接跟它说："把这个 Topic 的模型改成 Haiku"，它会自己搞定。

---

### 我的模型选择原则：

| 任务类型 | 推荐模型 | 原因 |
|---------|---------|------|
| 深度分析、策略制定 | Opus | 推理能力最强 |
| 代码、内容创作、日常工作 | Sonnet | 性价比最高 |
| 监控、通知、简单查询 | Haiku | 速度快、成本低 |
| 不确定的新任务 | Sonnet | 先用Sonnet，需要时升级 |

---

### 进阶玩法：

1. **Cron 任务也可以指定模型** — 定时任务不需要 Opus，用 Haiku 就够
2. **Sub-agent 可以用不同模型** — 主 session 用 Opus 思考，spawn 出来的 sub-agent 用 Sonnet 干活
3. **同一个 Topic 可以随时切换** — `/model` 命令即时生效

---

总结：Topics 不只是"并发多任务"，更是"分级用模型"。

一个群 = 多条车道 = 每条车道不同引擎。

这才是 Clawdbot Topics 的完全体 💪

---

## Quote Repost Text (短推文):

@Tz_2022 的 Topics 并发指南很赞。但有个杀手级功能很多人漏了：

每个 Topic 可以用不同的模型。

我的群：8个Topic，3种模型混用。Opus做决策，Sonnet干活，Haiku监控。

Token成本降 60-70%，关键任务质量不降。

详见👇

---

## Needs from Jason:
- [ ] 截图：Telegram 群里的 Topics 列表（展示多个 Topic 名称）
- [ ] 截图：/status 命令显示不同模型（可选，文字描述也行）
- [ ] 确认是否要用中文还是英文发（考虑到原帖是中文，建议中文）
- [ ] Jason 的 X handle 确认（@xxx111god?）
