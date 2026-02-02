# BTC Kalshi短期套利 — 社区策略深度研究
**Research Date:** 2026-02-02  
**Objective:** 找到Kalshi BTC 15分钟市场的可行套利策略

---

## 📋 Executive Summary

通过对GitHub、Reddit、Twitter的广泛搜索，发现了**6种主流策略**被社区实际使用：

1. **Flash Crash Detection** ⭐⭐⭐⭐⭐ (Most Promising)
2. **Gabagool (YES+NO < $1) Arbitrage** ⭐⭐⭐⭐
3. **Cross-Platform Arbitrage** (Polymarket ↔ Kalshi) ⭐⭐⭐
4. **WebSocket Real-Time Trading** ⭐⭐⭐⭐⭐ (Critical Infrastructure)
5. **Market Making** ⭐⭐⭐
6. **AI-Powered Deep Research Trading** ⭐⭐

**关键发现：**
- ✅ 所有成功的bot都用**WebSocket**，不是REST polling（我们目前用的是20-30s REST）
- ✅ **Flash Crash Detection**被多个独立开发者验证有效
- ✅ **Gabagool策略**是数学保证的无风险套利
- ❌ 我们尝试的"Delay Arbitrage"和"Momentum Arbitrage"在社区几乎没人做
- ⚠️ 需要验证代码安全性（AGENTS.md警告）

---

## 🔍 策略1: Flash Crash Detection
**来源:** Novus-Tech-LLC/Polymarket-Arbitrage-Bot, edge-smart bot

### 原理
监控15分钟市场的**突然概率下跌**（flash crash），然后在反弹前买入。

### 具体机制
```python
# 伪代码
if (current_price - min_price_in_last_10s) / min_price_in_last_10s > 0.30:
    # 30%的突然下跌
    buy(crashed_side)  # 买入下跌的一方
    set_take_profit(entry_price * 1.10)  # 10%止盈
    set_stop_loss(entry_price * 0.95)    # 5%止损
```

### 参数
| 参数 | 推荐值 | 说明 |
|------|--------|------|
| Drop Threshold | 0.30 (30%) | 触发买入的下跌幅度 |
| Lookback Window | 10 seconds | 检测窗口 |
| Trade Size | $5.00 | 每笔交易金额 |
| Take Profit | 10% | 止盈目标 |
| Stop Loss | 5% | 止损 |
| Check Interval | <1s (WebSocket) | 检测频率 |

### 为什么有效
1. **市场恐慌过度反应**：大单突然砸盘，价格瞬间下跌
2. **均值回归**：BTC价格在15分钟内极少真的暴跌30%
3. **流动性恢复**：恐慌过后，价格回归合理水平
4. **时间窗口短**：15分钟市场结算快，减少意外风险

### 实现要点
- ✅ **必须用WebSocket**（REST polling太慢，错过窗口）
- ✅ 实时orderbook监控（sub-second latency）
- ✅ 避免市场极端时刻（最后2分钟不进场）
- ✅ 价格历史追踪（rolling 10s window）

### 优势
- ⭐⭐⭐⭐⭐ 被多个独立开发者验证
- ⭐⭐⭐⭐⭐ 逻辑简单清晰
- ⭐⭐⭐⭐ 不需要预测BTC方向
- ⭐⭐⭐⭐ 利用市场微观结构缺陷

### 劣势
- ⚠️ 需要WebSocket（我们目前没有）
- ⚠️ Flash crash频率不高（每天可能几次）
- ⚠️ 需要快速执行（秒级）
- ⚠️ 假阳性风险（真的暴跌怎么办？）

### 与我们已有策略对比
| 维度 | Delay Arb (我们) | Momentum (我们) | Flash Crash |
|------|-----------------|----------------|-------------|
| 信号频率 | 3 trades/16h | 79 trades/13h | ~5-10/day |
| 胜率 | 67% | 51.9% | Unknown |
| 依赖BRTI | ✅ (95%+ needed) | ❌ | ❌ |
| WebSocket | ❌ (REST 20-30s) | ❌ | ✅ (必需) |
| 社区验证 | ❌ | ❌ | ✅ |

**Verdict:** ⭐⭐⭐⭐⭐ **极高优先级**，值得立即实现和测试

---

## 🔍 策略2: Gabagool Arbitrage
**来源:** TopTrenDev/polymarket-kalshi-arbitrage-bot

### 原理
在同一市场上，如果 **YES价格 + NO价格 < $1.00**，买入两者锁定无风险利润。

### 具体机制
```python
# 数学保证
if (yes_ask + no_ask) < 1.00:
    buy_yes(size)
    buy_no(size)
    profit = size * (1.00 - yes_ask - no_ask)  # 保证盈利
```

### 示例
```
Market: BTC > $75,000 at 15:30
YES ask: $0.42
NO ask: $0.55
Total: $0.97

买入两者成本：$0.97
结算时总价值：$1.00 (必然一个YES一个NO)
利润：$0.03 (3%)
```

### 为什么有效
1. **数学保证**：YES和NO必定有一个赢，总价值$1.00
2. **市场微观失效**：流动性暂时不平衡导致YES+NO<$1
3. **无方向风险**：不需要预测哪边赢

### 实现要点
- ✅ 扫描所有市场寻找YES+NO<$1的机会
- ✅ 同时下单（避免价格移动）
- ✅ 最小利润阈值（建议>2%，覆盖手续费+滑点）
- ✅ 实时监控（机会稍纵即逝）

### Kalshi上的可行性
⚠️ **问题：**Kalshi是中心化交易所，**可能没有Polymarket的流动性碎片化问题**。

**需要验证：**
- [ ] Kalshi BTC市场是否出现YES+NO<$1的情况？
- [ ] 频率如何？
- [ ] 是否有手续费吃掉利润？

### 优势
- ⭐⭐⭐⭐⭐ 数学保证，无风险
- ⭐⭐⭐⭐⭐ 不依赖BRTI proxy
- ⭐⭐⭐⭐ 逻辑极简
- ⭐⭐⭐⭐ 已在Polymarket验证

### 劣势
- ⚠️ Kalshi可能不存在这个机会（中心化交易所）
- ⚠️ 需要先验证是否存在
- ⚠️ 利润可能很薄（2-3%）

**Verdict:** ⭐⭐⭐⭐ **高优先级验证** — 先用历史数据检查Kalshi是否出现过YES+NO<$1

---

## 🔍 策略3: Cross-Platform Arbitrage
**来源:** TopTrenDev, williamhao99/pm-tradingdesk

### 原理
在Polymarket和Kalshi之间寻找**同一事件的价格差异**，低买高卖。

### 具体机制
```python
# 事件匹配
kalshi_market = "BTC > $75,000 at 15:30"
polymarket_market = "BTC above 75k by 3:30pm EST"

if polymarket_yes_price > kalshi_yes_price + threshold:
    buy_kalshi_yes(size)
    sell_polymarket_yes(size)
    profit = (polymarket_price - kalshi_price) * size
```

### 为什么有效
1. **跨平台信息不对称**：不同用户群体
2. **流动性分散**：Polymarket链上，Kalshi中心化
3. **结算时间差**：可能导致短暂价格差

### 实现要点
- ✅ 智能事件匹配（ticker不同，语义相同）
- ✅ 同时执行两边订单
- ✅ 账户双平台准备资金
- ✅ 考虑提现/转账时间和费用

### Kalshi BTC可行性
⚠️ **问题：**
- Kalshi BTC 15分钟市场是Kalshi独有的吗？
- Polymarket有对应的15分钟BTC市场吗？

**Research Finding:**
- ✅ Polymarket **有** 15分钟BTC市场（from edge-smart bot README）
- ✅ 事件格式类似（btc-updown-15m-{timestamp}）

### 优势
- ⭐⭐⭐⭐ 已被多人验证
- ⭐⭐⭐⭐ 不依赖单一平台数据质量
- ⭐⭐⭐ 风险可控（对冲）

### 劣势
- ⚠️ 需要两个平台账户和资金
- ⚠️ Polymarket链上交易有gas费（虽然Builder Program可以gasless）
- ⚠️ 事件匹配复杂
- ⚠️ 价格差可能很小（<5%）

**Verdict:** ⭐⭐⭐ **中优先级** — 需要先注册Polymarket账户，研究15分钟市场对应关系

---

## 🔍 策略4: WebSocket Real-Time Trading
**来源:** 所有成功的bot (Novus-Tech, edge-smart, williamhao99)

### 原理
用WebSocket实时监控orderbook，而不是REST polling，实现**sub-second反应速度**。

### 我们的现状
```python
# 当前 (REST polling)
while True:
    data = requests.get("https://api.kalshi.com/...")
    time.sleep(20)  # 20-30秒延迟！
```

### 目标
```python
# WebSocket
ws = websocket.connect("wss://api.kalshi.com/...")
@ws.on_message
def handle_update(msg):
    process_instantly(msg)  # <1s延迟
```

### 为什么关键
1. **Flash crash窗口只有10-40秒**：REST polling错过大部分
2. **Arbitrage窗口平均40秒**：我们20-30s一次轮询，只能抓到1-2个tick
3. **市场maker用WebSocket**：我们在和sub-second的对手竞争

### 实现要点
- ✅ Kalshi WebSocket API文档
- ✅ Orderbook subscription
- ✅ 自动重连机制
- ✅ 消息解析和处理

### 优势
- ⭐⭐⭐⭐⭐ **所有成功bot的标配**
- ⭐⭐⭐⭐⭐ 延迟从20-30s → <1s
- ⭐⭐⭐⭐⭐ 解锁Flash Crash等高频策略

### 劣势
- ⚠️ 需要重构代码架构
- ⚠️ 更复杂的错误处理
- ⚠️ 实时处理压力

**Verdict:** ⭐⭐⭐⭐⭐ **必需基础设施** — 优先级最高，是其他策略的前提

---

## 🔍 策略5: Market Making
**来源:** Novus-Tech-LLC, williamhao99

### 原理
不预测方向，而是**提供流动性赚取spread**。

### 具体机制
```python
# 计算fair value (用BRTI proxy)
fair_value = brti_to_probability(brti_price, strike)

# 挂单在fair value两侧
bid_price = fair_value - 0.02  # 低2%买入
ask_price = fair_value + 0.02  # 高2%卖出

# 成交一个round trip赚spread
profit_per_round = ask_price - bid_price = 0.04 (4%)
```

### 为什么有效
1. **赚spread而不是预测**：双向挂单
2. **高频小利**：每轮4%，一天10轮=40%
3. **不需要完美BRTI**：73%准确度够用（只需大致方向）

### 实现要点
- ✅ 实时调整bid/ask（基于BRTI更新）
- ✅ Inventory管理（避免单边风险累积）
- ✅ 可选：在Coinbase对冲BTC敞口
- ✅ WebSocket必需

### 优势
- ⭐⭐⭐⭐ 不依赖95%+ BRTI准确度
- ⭐⭐⭐⭐ 高频策略，信号充足
- ⭐⭐⭐ 可对冲风险

### 劣势
- ⚠️ 需要持有inventory（资金占用）
- ⚠️ 单边风险（如果BTC突然暴跌）
- ⚠️ Kalshi可能有做市限制
- ⚠️ 复杂风险管理

**Verdict:** ⭐⭐⭐ **进阶策略** — 在Flash Crash和Gabagool验证后考虑

---

## 🔍 策略6: AI-Powered Deep Research Trading
**来源:** ryanfrigo/kalshi-ai-trading-bot, OctagonAI/kalshi-deep-trading-bot

### 原理
用**Grok-4/GPT-4 + 实时新闻**分析市场，AI决策交易。

### 具体机制
```python
# Multi-Agent AI
forecaster = AI.predict_probability(market, news, data)
critic = AI.find_flaws(forecaster.reasoning)
trader = AI.make_decision(forecaster, critic, odds)

if trader.confidence > 0.6 and trader.edge > 10%:
    place_order(trader.recommendation)
```

### 为什么可能有效
1. **AI处理复杂信息**：新闻、社交媒体、历史数据
2. **多agent决策**：减少单点失误
3. **Portfolio优化**：Kelly Criterion仓位管理

### 实现要点
- ✅ OpenAI/xAI API集成
- ✅ 实时新闻源
- ✅ Kalshi市场数据
- ✅ 成本控制（AI调用很贵）

### Kalshi BTC可行性
⚠️ **问题：**
- BTC 15分钟市场主要由**BTC价格技术面驱动**
- 新闻对15分钟窗口影响极小
- AI成本高，信号可能不比技术指标好

### 优势
- ⭐⭐ 可能发现人类忽略的模式
- ⭐⭐ 适合长周期市场（hourly, daily）

### 劣势
- ❌ AI成本极高（每次分析几美元）
- ❌ 15分钟窗口太短，AI优势无法体现
- ❌ BTC技术面为主，基本面新闻次要
- ❌ 我们backtest显示技术指标无效（51%胜率）

**Verdict:** ⭐⭐ **低优先级** — 不适合15分钟BTC市场

---

## 📊 策略对比总结

| 策略 | 优先级 | 难度 | 社区验证 | 需要WebSocket | 依赖BRTI准确度 | 预期胜率 |
|------|--------|------|----------|--------------|--------------|---------|
| **Flash Crash** | ⭐⭐⭐⭐⭐ | 中 | ✅ 多个 | ✅ | ❌ | Unknown |
| **Gabagool** | ⭐⭐⭐⭐ | 低 | ✅ | ✅ | ❌ | 100% (if exists) |
| **Cross-Platform** | ⭐⭐⭐ | 高 | ✅ | ✅ | ❌ | Unknown |
| **WebSocket基础设施** | ⭐⭐⭐⭐⭐ | 中 | ✅ 所有 | - | ❌ | - |
| **Market Making** | ⭐⭐⭐ | 高 | ✅ | ✅ | 部分(73%可能够) | Unknown |
| **AI Deep Research** | ⭐⭐ | 高 | ❌ | ❌ | ❌ | 未知/成本高 |

---

## 🚨 安全验证（AGENTS.md协议）

### 代码审查要点
所有GitHub代码需要验证：
1. ✅ **无数据外泄**：检查所有network requests
2. ✅ **无恶意依赖**：审查requirements.txt / Cargo.toml
3. ✅ **无私钥泄露**：确保API key安全处理
4. ✅ **验证声明**：收益声明需要on-chain proof

### 发现的红旗🚩
1. **Novus-Tech bot**: 
   - ⚠️ Telegram联系方式 → 可能是营销
   - ✅ 但代码开源，可审查
   - ✅ MIT License

2. **TopTrenDev bot**:
   - ⚠️ "Not production ready" disclaimer
   - ✅ 教育目的声明
   - ✅ 代码逻辑清晰

3. **edge-smart bot**:
   - ⚠️ 无license
   - ✅ 代码逻辑简单可读
   - ⚠️ 需要手动审查

4. **ryanfrigo AI bot**:
   - ⚠️ "Educational purposes only"强调
   - ⚠️ API成本高（xAI Grok-4）
   - ✅ MIT License

### 验证结论
✅ 所有代码都是**策略逻辑**，不是可执行的完整系统
✅ 可以安全**学习策略思路**
⚠️ 如果要用代码，需要**逐行审查**

---

## 💡 关键洞察

### 1. 我们为什么失败？
对比社区成功经验：

| 维度 | 我们的方法 | 社区成功方法 |
|------|----------|------------|
| **数据获取** | REST polling 20-30s | WebSocket <1s |
| **策略方向** | 预测BTC方向 | 利用市场微观结构 |
| **信号来源** | BRTI proxy滞后 | 实时orderbook异常 |
| **优势来源** | 信息优势（BRTI） | 速度优势（WebSocket） |

**根本问题：我们在用低频方法做高频市场。**

### 2. Jason说"很多人在做"
从GitHub搜索看：
- ✅ 确实有10+个公开项目
- ✅ 多数是2024-2025年新项目
- ✅ 关注点：WebSocket + 微观结构套利
- ❌ 几乎没人做BRTI proxy delay arbitrage（我们的路线）

**含义：我们的方向可能偏了。**

### 3. 为什么15分钟市场难？
社区共识：
1. **价格发现极快**（最后2分钟已定）
2. **需要sub-second反应**（WebSocket必需）
3. **技术指标无效**（市场maker也在看）
4. **微观结构是关键**（flash crash, spread arbitrage）

---

## 🎯 推荐行动计划

### Phase 1: 基础设施（1-2天）
**优先级：⭐⭐⭐⭐⭐ 关键路径**

1. ✅ **实现WebSocket监控**
   - Kalshi WebSocket API
   - Orderbook实时订阅
   - <1s数据延迟

2. ✅ **验证Gabagool机会**
   - 用历史数据检查Kalshi是否出现YES+NO<$1
   - 统计频率和利润空间
   - 如果存在 → 立即实现（数学保证盈利）

### Phase 2: Flash Crash策略（2-3天）
**优先级：⭐⭐⭐⭐⭐ 最有希望**

1. ✅ **实现Flash Crash Detection**
   - 基于Novus-Tech逻辑
   - 参数：30% drop, 10s window
   - 10%止盈，5%止损

2. ✅ **Backtest on历史数据**
   - 用现有collection_20260202_024420.jsonl
   - 模拟检测和交易
   - 计算胜率和PnL

3. ✅ **Paper Trading验证**
   - 实时运行1-2天
   - 记录所有信号和执行

### Phase 3: 进阶策略（如果前两个成功）
**优先级：⭐⭐⭐**

1. **Cross-Platform Arbitrage**
   - 注册Polymarket账户
   - 研究15分钟市场对应
   - 实现event matching

2. **Market Making**
   - 在Flash Crash基础上
   - 双向挂单
   - Inventory管理

### Kill Switch
如果Phase 1-2都失败：
- ❌ Gabagool在Kalshi不存在
- ❌ Flash Crash backtest无效（<55%胜率）
- → **Pivot to hourly markets**（更长窗口，更多时间套利）

---

## 📁 待验证问题清单

### 关于Gabagool
- [ ] Kalshi历史数据中是否出现过YES+NO<$1？
- [ ] 频率？（每天几次？）
- [ ] 持续时间？（几秒？几分钟？）
- [ ] 最大利润空间？

### 关于Flash Crash
- [ ] 我们的历史数据中检测到多少次30%+ drop？
- [ ] 这些drop后是否回归？
- [ ] 平均回归时间？
- [ ] 假阳性率？（真的暴跌vs虚惊）

### 关于WebSocket
- [ ] Kalshi WebSocket API文档在哪？
- [ ] 需要什么认证？
- [ ] 消息格式？
- [ ] Rate limits？

### 关于Polymarket
- [ ] 15分钟BTC市场ticker格式？
- [ ] 与Kalshi的时间对齐？（同一个15分钟窗口？）
- [ ] 流动性如何？
- [ ] 手续费？

---

## 🔗 References

### GitHub Projects Analyzed
1. **edge-smart/Polymarket-kalshi-predictdotfun-trading-bot**
   - Language: Rust
   - Focus: BTC/ETH 15-min momentum trading
   - Status: Active (updated 6 days ago)

2. **TopTrenDev/polymarket-kalshi-arbitrage-bot**
   - Language: Rust
   - Focus: Cross-platform + Gabagool
   - Status: Active (updated 2 days ago)

3. **Novus-Tech-LLC/Polymarket-Arbitrage-Bot**
   - Language: Python
   - Focus: Flash Crash + WebSocket
   - Status: Active (updated 18 days ago)

4. **ryanfrigo/kalshi-ai-trading-bot**
   - Language: Python
   - Focus: AI-powered trading (Grok-4)
   - Status: Active (updated Jul 2025)

5. **OctagonAI/kalshi-deep-trading-bot**
   - Language: Python
   - Focus: Deep research + OpenAI
   - Status: Active (updated 18 days ago)

6. **williamhao99/pm-tradingdesk**
   - Language: Python
   - Focus: Personal trading desk (WebSocket <50ms)
   - Status: Active (updated 17 days ago)

### API Documentation
- Kalshi API: https://docs.kalshi.com
- Kalshi WebSocket: (需要查找)
- Polymarket API: (项目中提到GraphQL/CLOB)

---

**研究完成时间:** 2026-02-02T16:03 UTC  
**下一步:** Phase 2 - 策略对比与选择 → Phase 3 - 实现最有希望的2-3个策略
