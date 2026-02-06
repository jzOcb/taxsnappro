# Deep Research Report: Prediction Market Trading Strategies
## Date: 2026-02-05
## Sources: Twitter, GitHub, Medium, Polymarket Analytics

---

## 1. 已确认赚钱的策略类型

### 1A. 做市 (Market Making) — 最成熟的赚钱方式

**@gabagool22 — $705k profit, 2,268 predictions**
- Source: @hanakoxbt analysis (224 likes, 16 RT)
- 策略：在1day BTC up/down market做双边做市
- **Maker**: 在YES/NO两边挂限价单，比mid略好，收spread
- **Taker**: 当PM价格滞后于Binance时，吃掉流动性获取instant profit  
- **Dip Arbitrage**: whale大单导致价格偏移时快速买入等回归
- 每天约10次精确交易，不频繁
- 关键洞察：**"precision market making beats random scalping"**

**@defiance_cr — poly-maker开源作者 (840 stars)**
- Top 5 Polymarket做市奖励接收者
- **核心方法：用波动率来选市场**
  1. 计算每个市场的实时波动率
  2. 选低波动率+高奖励的市场（因为大多数人在高波动率市场提供相同的流动性）
  3. YES/NO两边挂单，比最近200-share level高一tick
  4. 止损、交易流监控、orderbook imbalance检测
- **关键发现：orderbook动态和累积交易量的信号出现在价格变动之前**
- 参数分类：4种市场类型，每种共享相同参数（波动率阈值、止损）
- **警告**: "In today's market, this bot is not profitable and will lose money" — 竞争已加剧

### 1B. 非对称套利 (Asymmetric Hedging) — gabagool的具体方法

Source: Medium深度分析 by Michal Stefanow

**核心公式：**
```
avg_YES = Total_Cost(YES) / Total_Shares(YES)
avg_NO = Total_Cost(NO) / Total_Shares(NO)
Pair_Cost = avg_YES + avg_NO
当 Pair_Cost < 1.00 时，锁定利润
```

**具体执行：**
- 不同时买YES+NO（不是简单套利）
- 在不同时间点分别买——当YES变便宜时买YES，当NO变便宜时买NO
- 保持数量平衡：Qty_YES ≈ Qty_NO
- 真实案例：1266.72 YES@0.517 + 1294.98 NO@0.449 = Pair Cost 0.966 → 单窗口赚$58.52

**为什么可行：**
- 二元市场理论上 YES + NO = 1.00
- 但散户情绪波动导致频繁错位：YES 0.20, NO 0.85 → 几分钟后 YES 0.82, NO 0.18
- 短时窗口（15min）情绪波动更剧烈

---

## 2. 操纵相关研究

### 2A. @predict_anon 的操纵成本模型
- 最小BTC操作成本 = $2,000 (1M volume × 0.2%)
- 正常操作成本 = $30,000 (10M volume × 0.3%)
- 50k+ poly shares可在低流动性时完全操纵
- 10k+ shares可在尾盘微操

### 2B. @zzd_la 报道
- 20 BTC就能操控15min市场价格
- Polymarket正在推出5min BTC market（更短窗口）

### 2C. 反操纵策略（predict_anon提出）
- 理论上反操纵更容易获利：可从现货+up/down双向赚
- 计算盈亏平衡点：
  - 现货潜在收益 = sell_wall × (open_price - close_price) × 2/3 - 手续费
  - updown收益/亏损 = PM上比公允价格高的订单买入收益/成本
  - 当两者接近时，这是一笔可进行的交易

---

## 3. 开源工具和基础设施

### 3A. GitHub Top Repos

| Repo | Stars | Description | 对我们的价值 |
|------|-------|-------------|-------------|
| **warproxxx/poly-maker** | 840 | Polymarket做市bot，WebSocket+Google Sheets配置 | 高 — 做市策略参考 |
| **ryanfrigo/kalshi-ai-trading-bot** | 112 | Kalshi AI交易，Grok-4集成 | 中 — 架构参考 |
| **OctagonAI/kalshi-deep-trading-bot** | 96 | Kalshi深度研究+OpenAI决策 | 中 — AI决策参考 |
| **Novus-Tech-LLC/Polymarket-Arbitrage-Bot** | 63 | PM/Kalshi跨平台套利 | 低 — 简单套利 |
| **Drakkar-Software/OctoBot-Prediction-Market** | 33 | PM copy trading + 套利 | 中 — copy trading思路 |
| **pietrobogani/Polymarket-live-odds-trading** | 1 | 足球Poisson模型 | 高 — 概率建模参考 |

### 3B. 概率建模方法

**Poisson/Skellam模型 (足球应用，可迁移)**
- 用Poisson过程建模事件发生（进球/价格突破）
- Skellam分布 = 两个Poisson的差
- 给出 P(win), P(draw), P(lose)
- 当预测概率与市场价格有显著差异时买入

**波动率建模 (defiance_cr方法)**
- 实时计算每个市场的波动率
- 低波动率 = 更安全的做市环境
- 参数按市场流动性类型分为4类

### 3C. 链上追踪工具

- **polymarketanalytics.com/traders** — 每5分钟更新的trader排行榜
  - 可以追踪top账号的PnL、持仓、win rate
  - 点击看详细交易历史
  - "Sharp traders" vs "dumb money" 分析
- Polymarket所有交易在Polygon链上公开
- 可以用Polygon RPC或Dune Analytics追踪

---

## 4. AI/LLM辅助决策

### 4A. Multi-Agent方法 (ryanfrigo的Kalshi bot)
- **Forecaster Agent**: 估算真实概率
- **Critic Agent**: 找潜在问题和遗漏
- **Trader Agent**: 最终决策 + position sizing
- 用Kelly Criterion做仓位管理
- 成本：需要LLM API调用，每笔交易有推理成本

### 4B. 我的评估
- 对于15min市场，LLM调用太慢（每次3-10秒）
- 更适合长周期市场（政治、天气等）
- 但概念可用：在Research阶段用AI分析，在Trade阶段用纯数学

---

## 5. 关键教训和警告

### 来自实战者的警告
1. **defiance_cr**: "In today's market, this bot is not profitable" — 竞争已加剧
2. **predict_anon**: "不建议用15m作为切入点——竞争最激烈，职业化最高"
3. **@zostaff**: "很多bot存在只是为了提供流动性"——有些表面赚钱的bot可能有亏损的对冲账号
4. **@sanek_1sd**: "This isn't prediction skill — it's pure market structure extraction. Edge disappears when liquidity thickens"

### 时间窗口
- @crpykenny预估8-10个月窗口（不可靠来源）
- 更现实的评估：15min BTC市场已经高度垄断（JaneStreet + predict_anon等）
- 新的5min市场可能有短期机会
- 其他市场（天气、体育、政治）竞争相对较低

---

## 6. 对我们的具体建议

### 立即可用
1. **非对称套利 (gabagool方法)** — 不需要预测方向，只需要在价格错位时分别买入
2. **波动率筛选** — 只在低波动率环境做市/交易
3. **polymarketanalytics.com** — 开始追踪top accounts的行为
4. **orderbook信号** — defiance_cr确认orderbook动态领先于价格

### 需要开发
1. **概率模型** — 参考Poisson方法，为BTC 15min建立概率估计
2. **链上追踪器** — 监控top accounts在Polygon上的实时交易
3. **操纵检测** — 基于predict_anon的成本模型

### 可参考的开源代码
1. `warproxxx/poly-maker` — 做市策略的完整参考实现
2. `pietrobogani/Polymarket-live-odds-trading` — Poisson概率模型
3. `ryanfrigo/kalshi-ai-trading-bot` — Multi-agent AI决策架构

---

*研究持续进行中。下次更新重点：5min market的机会分析、Kalshi specific做市策略、链上追踪工具搭建*
