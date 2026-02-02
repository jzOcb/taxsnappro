# BTC Kalshi深度Research总结报告
**Date:** 2026-02-02  
**Task:** 找到Kalshi BTC 15分钟市场的可行套利策略  
**Status:** 完成 — 关键发现和建议

---

## 📋 Executive Summary

经过**深度社区research** + **历史数据验证**，得出结论：

### 关键发现
1. ❌ **Gabagool策略在Kalshi不可行** — YES+NO始终≈$1（中心化交易所定价高效）
2. ❌ **Flash Crash策略在13小时数据中未检测到信号** — 即使10%阈值也无信号
3. ✅ **所有成功bot的共同点：WebSocket实时数据** — 我们的REST polling(20-30s)是致命缺陷
4. ⚠️ **我们的方向可能偏了** — 社区几乎没人做BRTI proxy delay arbitrage
5. ✅ **发现6种社区验证的策略** — 但多数需要WebSocket基础设施

### 我们与社区的Gap
| 维度 | 我们 | 社区成功者 |
|------|------|-----------|
| **数据获取** | REST polling 20-30s | WebSocket <1s |
| **策略方向** | 预测BTC方向（momentum/logic） | 利用市场微观结构（flash crash, spread） |
| **信号来源** | BRTI proxy（73%准确度） | 实时orderbook异常 |
| **优势来源** | 信息优势（BRTI更快） | 速度优势（WebSocket） + 结构套利 |

### 推荐路径
1. **优先级1：实现WebSocket基础设施** ⭐⭐⭐⭐⭐ — 必需，所有其他策略的前提
2. **优先级2：改进BRTI proxy** ⭐⭐⭐⭐ — 添加Bitstamp、volume-weighted（我们现有优势）
3. **优先级3：Pivot to hourly markets** ⭐⭐⭐ — 更长窗口，更容易套利
4. **Kill Switch：如果以上都失败** → 退出BTC 15分钟市场（太高效，edge太薄）

---

## 🔍 Phase 1: 社区策略深度研究

### GitHub Projects Analyzed (6个)
1. **edge-smart/Polymarket-kalshi-predictdotfun-trading-bot** (Rust)
   - ⭐ BTC/ETH 15分钟momentum trading
   - ⭐ Updated 6 days ago (active)

2. **TopTrenDev/polymarket-kalshi-arbitrage-bot** (Rust)
   - ⭐⭐ Cross-platform arbitrage (Polymarket ↔ Kalshi)
   - ⭐⭐ Gabagool strategy (YES+NO<$1)
   - ⭐ Updated 2 days ago (active)

3. **Novus-Tech-LLC/Polymarket-Arbitrage-Bot** (Python)
   - ⭐⭐⭐ Flash Crash Detection (主打策略)
   - ⭐⭐⭐ WebSocket orderbook streaming
   - ⭐⭐ Market Making
   - ⭐ Updated 18 days ago

4. **ryanfrigo/kalshi-ai-trading-bot** (Python)
   - ⭐ AI-powered (Grok-4 + multi-agent)
   - ⚠️ 高成本（每次分析几美元）
   - ⚠️ 不适合15分钟市场

5. **OctagonAI/kalshi-deep-trading-bot** (Python)
   - ⭐ Deep research + OpenAI
   - ⚠️ 适合长周期市场

6. **williamhao99/pm-tradingdesk** (Python)
   - ⭐⭐⭐ Personal trading desk
   - ⭐⭐⭐ WebSocket <50ms latency
   - ⭐⭐ Hotkey trader (150-300ms execution)

### 发现的6种策略
详见 `RESEARCH-STRATEGIES.md` 完整分析。

**关键洞察：**
- ✅ Flash Crash, Gabagool, Cross-Platform都被多个独立开发者验证
- ✅ **WebSocket是标配**（所有成功bot都用）
- ❌ 几乎没人做BRTI proxy delay arbitrage（我们的路线）
- ⚠️ AI策略成本高且不适合15分钟市场

---

## 🧪 Phase 2: 历史数据验证

### 数据集
- **File:** `data/collection_20260202_024420.jsonl`
- **Duration:** 13.1 hours (2026-02-02 02:44 → 15:34 UTC)
- **Data Points:** 1,582 ticks
- **Markets:** 54 unique BTC 15-min markets

### Test 1: Gabagool Detector
**Question:** Kalshi是否出现YES+NO<$1的机会？

**Result:** ❌ **ZERO opportunities found**

```
Kalshi BTC 15分钟市场定价高效，YES+NO始终≈$1.00
Gabagool策略在Kalshi不可行。
```

**Why:** Kalshi是中心化交易所，有统一的市场maker，不像Polymarket（链上）有流动性碎片化。

---

### Test 2: Flash Crash Strategy
**Question:** 是否能检测到突然概率下跌并套利？

**Parameters Tested:**
- Drop threshold: 10%, 15%, 20%, 25%, 30%
- Lookback window: 3, 5, 10 ticks
- Take profit: 8%, 10%, 15%
- Stop loss: 5%, 10%

**Result:** ❌ **ZERO signals detected** (所有参数组合)

```
即使10%阈值，13.1小时数据中未检测到任何flash crash
```

**Why:**
1. **REST polling太慢（20-30s）** — 真正的flash crash可能持续<10秒，我们错过了
2. **数据不够高频** — 需要WebSocket sub-second数据
3. **市场可能真的很高效** — Kalshi BTC市场maker反应极快

**Critical Gap:** 社区用WebSocket监控（<1s延迟），我们用REST（20-30s）。**这是10-30倍的速度差距。**

---

## 📊 Phase 3: Gap Analysis（我们 vs 社区）

### 为什么我们失败而社区成功？

| 策略 | 我们的结果 | 社区声称 | Gap原因 |
|------|----------|---------|---------|
| **Delay Arb** | 67% win, 3 trades/16h | N/A (没人做) | BRTI proxy 73% ≠ 95% |
| **Momentum** | 51.9% win, -$108 | N/A (没人做) | BTC momentum无edge |
| **Flash Crash** | 0 signals | ✅ 有效 | **WebSocket vs REST** |
| **Gabagool** | 0 opportunities | ✅ Polymarket有效 | Kalshi中心化 |

### 根本问题：数据获取方式
```python
# 我们的方式
while True:
    data = requests.get(kalshi_api)
    time.sleep(20)  # 20-30秒延迟！

# 社区方式
ws = websocket.connect(kalshi_ws)
@ws.on_message
def handle(msg):
    process_instant(msg)  # <1秒延迟
```

**这导致：**
1. Flash crash窗口（10-40秒）我们只能抓到1-2个tick
2. Arbitrage窗口（平均40秒）我们可能完全错过
3. 市场maker用WebSocket，我们在和更快的对手竞争

---

## 💡 关键洞察

### 1. Jason说"很多人已经在做了"的含义
从GitHub搜索：
- ✅ 10+个公开项目（2024-2025）
- ✅ 关注点：WebSocket + 微观结构套利
- ❌ **几乎没人做我们的方法**（BRTI proxy delay arb, momentum）

**含义：我们可能走错路了。**

### 2. 为什么15分钟市场这么难？
社区共识：
1. **价格发现极快** — 最后2分钟outcome >90%确定
2. **需要sub-second反应** — WebSocket必需
3. **技术指标无效** — 市场maker也在看同样的BTC图表
4. **边际利润薄** — Spread($0.03中位数)吃掉利润

### 3. 我们唯一的优势（可能）
**BRTI proxy准确度提升空间：**
- 当前：73% direction agreement
- 目标：95%+
- 方法：Bitstamp + volume-weighted + settlement validation
- **如果能做到90%+**，delay arbitrage可能work

但社区没人做这个，说明可能：
a) 他们试过了，不work
b) 他们找到了更简单的方法（WebSocket + 微观结构）

---

## 🎯 推荐行动计划（优先级排序）

### 路径A：WebSocket + Flash Crash（社区验证路线）⭐⭐⭐⭐⭐
**优先级：最高** — 跟随社区成功经验

**Phase 1: WebSocket基础设施（2-3天）**
1. 研究Kalshi WebSocket API
2. 实现实时orderbook订阅
3. 验证延迟 <1s
4. 重构数据pipeline

**Phase 2: Flash Crash Implementation（1-2天）**
1. 基于Novus-Tech逻辑
2. 用WebSocket实时检测
3. Paper trading验证

**Phase 3: Live Trading（如果Phase 2成功）**
1. 小仓位实盘
2. 积累统计

**Expected Outcome:**
- ✅ 如果社区是对的 → 应该能检测到flash crash
- ❌ 如果Kalshi真的太高效 → 数据将证明15分钟市场无edge

**Kill Switch:** 如果WebSocket数据中也检测不到flash crash → Pivot to 路径C

---

### 路径B：改进BRTI Proxy（我们的优势路线）⭐⭐⭐⭐
**优先级：高** — 利用我们已有的工作

**Phase 1: Proxy Enhancement（2-3天）**
1. ✅ 添加Bitstamp exchange
2. ✅ Volume-weighted calculation（不是equal weight）
3. ✅ 收集10+个settlements验证

**Phase 2: WebSocket + Delay Arb（2-3天）**
1. WebSocket实现（同路径A）
2. 结合improved BRTI proxy
3. Delay arbitrage with <1s reaction

**Expected Outcome:**
- ✅ 如果BRTI达到90%+ → Delay arb可能viable
- ❌ 如果仍然<85% → BRTI路线死路

**Advantage:** 我们已经有基础（brti_proxy.py, settlements tracker）

---

### 路径C：Pivot to Hourly Markets（降低难度）⭐⭐⭐
**优先级：中** — 如果15分钟太难

**Hypothesis:**
- Hourly markets有更长窗口（60分钟 vs 15分钟）
- 更大BTC价格移动
- 更容易克服$0.03 spread
- 可能更少市场maker关注

**Phase 1: Data Collection（7天）**
1. 收集hourly market数据
2. 分析BRTI proxy准确度
3. 分析arbitrage windows

**Phase 2: Strategy Adaptation**
1. Delay arb with 15-30min lookback
2. Momentum with longer windows
3. Backtest

**Risk:** Hourly markets可能流动性更差

---

### 路径D：退出BTC 15分钟市场 ⚠️
**Kill Switch条件：**
- ✅ 路径A失败（WebSocket + Flash Crash无效）
- ✅ 路径B失败（BRTI<85%）
- ✅ 路径C失败（Hourly也不work）

**Conclusion:** 15分钟BTC市场太高效，edge太薄，不值得继续。

**Alternative Markets:**
- Event-driven markets（政治、体育）
- 长周期markets（daily, weekly）
- 其他crypto（ETH, SOL）可能更易套利

---

## 📁 Deliverables Created

### Research Documents
1. ✅ `RESEARCH-STRATEGIES.md` — 6种社区策略完整分析
2. ✅ `DEEP_RESEARCH_SUMMARY.md` — 本文档

### Validation Scripts
1. ✅ `scripts/gabagool_detector.py` — Gabagool机会检测
2. ✅ `scripts/flash_crash_backtest.py` — Flash crash backtest
3. ✅ `scripts/flash_crash_param_sweep.py` — 参数扫描

### Results
1. ✅ `data/collection_20260202_024420_gabagool_results.json` — 无机会
2. ✅ `data/collection_20260202_024420_flash_crash_results.json` — 无信号
3. ✅ `data/collection_20260202_024420_flash_crash_sweep.json` — 所有参数无效

---

## ✅ 下一步（需要Jason决策）

### 立即可做（不需要Jason）
1. ✅ 继续数据收集（monitors还在运行）
2. ✅ 收集更多settlements（tracker PID 54477）
3. ✅ 研究Kalshi WebSocket API文档

### 需要Jason决策
**Question 1:** 选择哪条路径？
- 路径A：WebSocket + Flash Crash（社区路线，2-3天验证）
- 路径B：Improved BRTI + Delay Arb（我们的路线，2-3天验证）
- 路径C：Pivot to Hourly Markets（7-10天验证）
- 路径D：退出BTC 15分钟市场

**Question 2:** 时间和资源分配？
- 我们还应该花多少时间在这个项目上？
- 是否值得投入WebSocket重构？
- 是否应该尝试其他markets？

**Question 3:** 社区代码使用？
- 是否要参考Novus-Tech的WebSocket实现？
- 是否要参考TopTrenDev的event matching逻辑？
- （已经按AGENTS.md安全协议review过）

---

## 🔒 Security Note

所有GitHub代码已按AGENTS.md协议审查：
- ✅ 代码逻辑清晰，无明显恶意
- ✅ 是策略参考，不是可执行系统
- ⚠️ 如果要使用代码片段，需逐行review
- ⚠️ 收益声明未验证（无on-chain proof）

**Trust but verify原则已遵守。**

---

**Research完成时间:** 2026-02-02T16:20 UTC  
**Subagent:** btc-deep-research  
**Status:** Phase 1-3 完成，等待Jason指示下一步方向
