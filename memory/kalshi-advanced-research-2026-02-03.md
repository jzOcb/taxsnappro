# Kalshi 预测市场高级交易策略研究报告

**日期**: 2026-02-03
**作者**: Clawdbot Research
**状态**: 基于现有代码分析 + 互联网研究 + 跨平台数据

---

## 目录
1. [跟单策略分析](#1-跟单策略分析)
2. [套利机会：Kalshi vs Polymarket](#2-套利机会kalshi-vs-polymarket)
3. [API 高级用法与自动化](#3-api-高级用法与自动化)
4. [高确定性事件策略（Endgame/Junk Bonding）](#4-高确定性事件策略)
5. [事件类型分析](#5-事件类型分析)
6. [当前热门市场与机会](#6-当前热门市场与机会)
7. [风险分析](#7-风险分析)
8. [Kalshi vs Polymarket 全面对比](#8-kalshi-vs-polymarket-全面对比)
9. [可执行策略建议](#9-可执行策略建议)
10. [下一步行动](#10-下一步行动)

---

## 1. 跟单策略分析

### Kalshi 有公开交易员 Profile 吗？

**结论：没有。** Kalshi 不提供类似 Polymarket 的公开交易员钱包/Profile 功能。

| 特性 | Kalshi | Polymarket |
|------|--------|------------|
| 公开交易者 Profile | ❌ 无 | ✅ 有（链上钱包透明） |
| 交易历史可查 | ❌ 仅自己的 | ✅ 所有链上交易公开 |
| 跟单工具 | ❌ 无 | ✅ 有第三方工具（PolyTrack, Polysights等） |
| 鲸鱼追踪 | ❌ 仅看到 volume | ✅ 可追踪大钱包 |
| 评论区分析 | ✅ 有价值 | ✅ Discord/评论区 |

### 可行替代方案

**A) Kalshi 评论区挖掘（已验证有效）**
- Jason 的 SCOTUS 案例就是从评论区获得的程序性知识
- 评论区有法律、金融、政策专家分享内行分析
- **行动**：对每个关注的市场，系统性阅读评论区

**B) Polymarket 鲸鱼追踪 → 反向映射到 Kalshi**
- 使用 Polysights、HashDive 等工具追踪 Polymarket 大户
- 找到大户重仓的事件 → 在 Kalshi 找对应市场
- 如果 Kalshi 价格尚未反映 → 跟单机会
- **工具**: `kalshi/crossplatform.py` 已有自动匹配基础

**C) 新闻/评论员信号**
- 追踪 Nate Silver、538 等专业预测者
- 追踪 Kalshi 官方博客分析（news.kalshi.com 有深度市场分析）
- 中文社区（微博/推特）的预测市场讨论

### 跟单策略评估

| 策略 | 可行性 | 预期 Alpha | 实施难度 |
|------|--------|-----------|---------|
| Kalshi 评论区 | ✅ 高 | 中等 | 低 |
| Polymarket 鲸鱼→Kalshi | ⚠️ 中 | 高 | 中 |
| 专业预测者 | ✅ 高 | 低-中 | 低 |

---

## 2. 套利机会：Kalshi vs Polymarket

### 当前实际套利数据（2026-02-03 扫描结果）

我们的 `crossplatform.py` 已经发现了真实的价差：

#### 政府关门市场（最大套利机会！）

| Kalshi Market | Kalshi Price | Poly Price | Spread | 方向 |
|---------------|-------------|-----------|--------|------|
| 关门 >4 天 | YES 15¢ | YES 100¢ | **85¢** | ⚠️ 需验证定义差异 |
| 关门 >5 天 | YES 8¢ | YES 17.5¢ | 9.5¢ | Buy Kalshi |
| 关门 >7 天 | YES 6¢ | YES 4.4¢ | 1.6¢ | Buy Poly |
| 关门 >10 天 | YES 4¢ | YES 1.8¢ | 2.2¢ | Buy Poly |

**⚠️ 关键警告：85¢ 价差极有可能是定义差异，不是真正套利**
- Kalshi 的 "4 days" 定义可能和 Polymarket 不同
- 时间窗口不同（Kalshi 到 Feb 28 vs Polymarket 到 Jan 31）
- **教训：V2 策略已强调——跨平台必须精读合约 PDF**

### 套利的现实挑战

1. **定义不匹配**：两平台对"同一事件"的定义经常不同（结算时间、判定标准、数据源）
2. **费用摩擦**：Kalshi ~0.7% per side，Polymarket 0.01-2%
3. **流动性问题**：低流动性市场无法同时在两端大量成交
4. **资金摩擦**：Kalshi USD，Polymarket USDC（链上），资金转移成本和时间
5. **结算时间差**：两个平台可能不在同一时间结算

### 真正可行的套利类型

**A) 信息速度套利（最高 Alpha）**
```
事件发生 → Polymarket 先反映（更活跃） → Kalshi 滞后
→ 在 Kalshi 快速交易
```
- 这是 Putin 通话案例的核心逻辑
- 我们的 `news_scanner.py` + `crossplatform.py` 可以捕捉
- 窗口极短（分钟到小时级别）

**B) 结构性价差套利**
```
两个平台的 bracket 设计不同
→ 可能出现覆盖同一结果但总成本 <$1 的情况
→ 无风险套利
```
- `parity_scanner.py` 已实现单平台内 parity 扫描
- 需要扩展为跨平台 parity

**C) 做市价差收割**
```
在流动性差的一侧做 market maker
→ 在流动性好的一侧对冲
→ 赚取 bid-ask spread
```
- 需要 API 自动化
- 资金量要求较高

---

## 3. API 高级用法与自动化

### Kalshi API 能力（基于文档分析）

```
REST API: https://api.elections.kalshi.com/trade-api/v2
WebSocket: wss://api.elections.kalshi.com/trade-api/ws/v2

认证: RSA-PSS 签名（我们已在 websocket/auth.py 实现）
```

### 已实现的工具矩阵

| 工具 | 文件 | 功能 | 状态 |
|------|------|------|------|
| 市场扫描 | `report_v2.py` | 全市场扫描 + Decision Engine 评分 | ✅ 生产 |
| 跨平台对比 | `crossplatform.py` | Kalshi vs Poly 价差发现 | ✅ 可用 |
| Endgame 扫描 | `endgame_scanner.py` | 近结算高概率机会 | ✅ 可用 |
| Parity 扫描 | `parity_scanner.py` | 同事件 bracket 套利 | ✅ 可用 |
| 新闻驱动 | `news_scanner.py` | 新闻→市场匹配 | ✅ 可用 |
| 到期窗口 | `expired_window.py` | 过期未结算市场 | ✅ 可用 |
| 动态管理 | `dynamic_trader.py` | 仓位管理 + 新闻验证 | ✅ 可用 |
| WebSocket | `websocket/` | 实时数据流 | 🔧 基础完成 |
| Paper Trading | `paper_trading.py` | 模拟交易记录 | ✅ 可用 |

### 缺失但需要的高级功能

**A) 限价单策略引擎（做市）**
```python
# 概念代码
class MarketMaker:
    def __init__(self, ticker, capital):
        self.spread_target = 2  # 2¢ target spread
        self.max_position = capital * 0.1  # 10% max exposure
    
    def quote(self, orderbook):
        mid = (orderbook.best_bid + orderbook.best_ask) / 2
        my_bid = mid - self.spread_target / 2
        my_ask = mid + self.spread_target / 2
        
        # 检查仓位限制
        if self.position > self.max_position:
            # 偏斜报价以减仓
            my_bid -= 1
        elif self.position < -self.max_position:
            my_ask += 1
        
        return my_bid, my_ask
```
- **风险**：需要处理 adverse selection（知情交易者把你吃掉）
- **适合**：高流动性、稳定的市场（经济指标接近结算时）
- **不适合**：突发事件市场（政治、战争类）

**B) 自动跟单/信号执行**
```python
# 新闻信号 → 自动下单流程
class SignalExecutor:
    def on_news_signal(self, signal):
        # 1. 验证信号
        if not self.verify_signal(signal): return
        
        # 2. 找到受影响的市场
        markets = self.find_affected_markets(signal.entities)
        
        # 3. 检查价格是否已反映
        for market in markets:
            if self.price_not_reflected(market, signal):
                # 4. 下限价单（避免 slippage）
                self.place_limit_order(
                    market, 
                    side=signal.direction,
                    price=market.mid - 1,  # 略低于中间价
                    quantity=self.position_size(market)
                )
```

**C) 实时监控仪表板**
- WebSocket 接收 ticker 更新
- 监控所有 paper trade 仓位实时 P&L
- 价格异动告警（>5¢ 变动）
- 需要：完成 WebSocket 集成 + 前端展示

### API 关键限制

- **Rate limit**: 约 10 req/s
- **WebSocket**: 最多 100 个订阅
- **交易**: 需要 KYC 验证 + 资金到位
- **最小单**: 1 contract
- **Maker/Taker 费**: Maker 通常更低，具体费率 market-dependent

---

## 4. 高确定性事件策略

### 策略核心："Junk Bonding" / "Endgame Harvesting"

这是我们已验证的核心策略，也是社区中 "poorsob" 等大户使用的策略。

### 策略数学

```
买入 YES @ 95¢ → 结算 YES → 收益 5¢ (5.26% return)
假设 9 天周期 → 年化 213%
假设 3 天周期 → 年化 639%
胜率需要 > 95% 才能整体盈利
```

### 我们的实战数据

| 案例 | 入场 | 退出/结算 | 收益 | 天数 | 年化 |
|------|------|----------|------|------|------|
| SCOTUS 关税 NO | 93¢ | 100¢ | 7.5% | 9 | ~304% |
| Trump-Putin YES | 62¢ | 100¢ | 61% | ~3 | ~7400% |
| Trump 签署法案 NO | 68¢ | 91¢ (exit) | 33% | ~7 | ~1720% |

### Paper Trading 当前状态（6笔）

所有 6 笔经济指标 paper trade 仍在 PENDING：
- CPI trades: 入场 95-96¢，等 Feb 11 结算
- GDP trades: 入场 87-94¢，等 Feb 20 结算
- 未实现亏损仅 -$10 (-1.0%)，正常波动范围

### Endgame 策略优化

**当前 endgame_scanner.py 的问题**：
1. 最近一次扫描找到 0 个机会 — 可能是市场接近结算时已效率定价
2. 仅用价格+时间估计概率，缺少事实验证层
3. 没有整合新闻验证（应该和 news_scanner 联动）

**改进建议**：
```
优化后流程：
1. 扫描 1-7 天内结算的市场
2. 对每个高概率市场，运行新闻验证
3. 检查官方数据源（BLS/BEA/Fed 日程）
4. 如果事实已可确认 + 价格仍有空间 → 标记为 ENDGAME 机会
5. 输出包含：预期收益、实际概率证据、风险因子
```

### 资金效率对比

| 策略 | 单次收益 | 周期 | 年化 | 胜率 | 适合资金 |
|------|---------|------|------|------|---------|
| Junk Bond 95¢+ | 2-7% | 3-14天 | 100-500% | 95%+ | $5K+ |
| 信息套利 50-70¢ | 30-100% | 1-5天 | 极高 | 60-80% | $500+ |
| Parity 套利 | 0.5-3% | 即时 | N/A | ~100% | $10K+ |
| 做市 | 1-3¢/trade | 连续 | 50-200% | N/A | $5K+ |

---

## 5. 事件类型分析

### 各类别市场的可预测性

基于我们的交易经验和策略分析：

#### 🟢 最容易预测（信息优势最大）

**A) 经济指标（CPI、GDP、就业）**
- **为什么好**：有官方数据源（BLS、BEA）、有专家预测（Cleveland Fed CPI Nowcast、GDPNow）
- **Alpha 来源**：散户不看 Nowcast 数据，Kalshi 定价经常滞后于专业预测
- **我们的优势**：`report_v2.py` 已整合 BLS/BEA 数据源评分
- **风险**：数据突然偏离预期（如 tariff 对 CPI 的冲击）
- **推荐度**: ⭐⭐⭐⭐⭐

**B) 程序性事件（法院日程、国会议程）**
- **为什么好**：日程公开、规则明确、散户不了解流程
- **Alpha 来源**：规则理解差（Rules Edge）— Putin=meeting 案例
- **风险**：规则被突然修改、极端政治事件
- **推荐度**: ⭐⭐⭐⭐⭐

#### 🟡 中等可预测性

**C) 天气市场**
- **为什么好**：NWS 预报数据公开、短期预报准确率高
- **Alpha 来源**：3-7 天预报准确率 ~80%，散户可能不追踪
- **风险**：天气本质不确定，极端事件难预测
- **Kalshi 特色**：大量城市温度/降雪市场，这是 Kalshi 的独有品类
- **推荐度**: ⭐⭐⭐⭐

**D) 政治事件（总统行动、法案签署）**
- **为什么好**：信息密度高，新闻驱动明显
- **Alpha 来源**：新闻速度差 + 规则理解差
- **风险**：Trump 不可预测性高、政策反转
- **推荐度**: ⭐⭐⭐

#### 🔴 难以预测

**E) 提及市场（Mention Markets）**
- "Trump 会提到 X 吗？" — 高度随机
- 但有时候有规律（如节日前的特定话题）
- **推荐度**: ⭐⭐

**F) 体育**
- 高效定价，庄家/专业赔率人已覆盖
- 除非有内幕信息，否则几乎无 alpha
- **推荐度**: ⭐

### 历史胜率数据（基于我们的经验）

| 类别 | 交易次数 | 胜率 | 平均收益 | 最大亏损 |
|------|---------|------|---------|---------|
| 经济指标 | 6 (paper) | TBD (Feb 11/20) | TBD | -3¢ unrealized |
| 程序性事件 | 3 (real) | 100% | ~34% | 0 |
| 政治事件 | 1 (real) | 100% | 61% | 0 |

样本太小无法统计显著，但方向正确。

---

## 6. 当前热门市场与机会

### 基于 2026-02-03 数据的机会分析

#### A) 即刻机会

**1. 政府关门市场（活跃！）**
- Kalshi: KXGOVSHUTLENGTH 系列 — 关门持续多少天
- Polymarket: $149M volume，目前 100% 确认会关门
- **机会**：关门已发生但持续时间 uncertain
  - >4天 YES 15¢ — 如果 shutdown 周末不结束就 settle YES
  - >5天 YES 8¢ — 下周一还没解决就 YES
  - **关键信息**：Congress 是否有解决方案？CR 延期？
  - **风险**：周末可能突然达成协议

**2. CPI 数据（Feb 11 结算）**
- 我们已有 paper trades：YES@95¢ (CPI>0%), YES@96¢ (CPI>-0.1%)
- 新机会：KXCPI-26JAN-T0.4 NO@95c (Score 100) — CPI 不会涨>0.4%
- **Cleveland Fed CPI Nowcast** 应该已有 1月预测
- **行动**：查看 Nowcast 确认方向

**3. GDP 数据（Feb 20 结算）**
- 我们已有 4 个 paper trades
- GDPNow 追踪中
- Q4 GDP 初值 Jan 30 已发布 — **需要确认发布的数值**
  - 如果 GDP 已发布，这些 trades 的概率应该已接近确定

#### B) 中期机会（1-4周）

**4. Fed 利率决议（March）**
- Polymarket: 91% No change
- Kalshi 也应有对应市场
- Fed 已经基本暗示 hold — 几乎确定性事件
- **Junk Bond 机会**：如果 Kalshi YES "Fed holds" 在 95¢+

**5. Trump Fed Chair 提名**
- Polymarket: 98% Kevin Warsh
- 如果 Kalshi 有对应市场且价格更低 → 套利

**6. US 对伊朗军事行动**
- Polymarket: 45% by June 30, 78% No strike by Feb 28
- 高度不确定，不适合 Junk Bonding
- 可能适合小仓位投机

#### C) 天气市场

**7. 冬季风暴市场**
- Kalshi 博客特别推荐了暴风雪相关市场
- 城市降雪量、温度极端值
- **可用 NWS 数据对照定价**
- 适合短期（1-3天）交易

### 不推荐的市场

- 提及市场（Mention Markets）— 太随机
- 长期政治（2028 选举）— 锁定资金太久
- 体育 — 无 alpha

---

## 7. 风险分析

### 系统性风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Kalshi 平台风险（倒闭/监管） | 低 | 高 | CFTC 监管，资金隔离 |
| 市场定价变得更高效 | 中 | 中 | AI/bot 竞争加剧，持续优化策略 |
| 黑天鹅事件 | 低 | 高 | 分散仓位，避免单一事件重仓 |
| 流动性枯竭 | 中 | 中 | 仅交易高 volume 市场 |
| 规则变更（合约 PDF 更新） | 低 | 中 | 监控合约更新通知 |

### 策略特定风险

**Junk Bonding 风险**：
- 95% 胜率下，20 笔交易中会有 1 笔亏损
- 1 笔亏损（-95¢）需要 ~19 笔成功（各赚5¢）才能弥补
- **Kelly Criterion 建议**：即使 95% 概率，最大仓位不超过资金的 20%
- **我们的设置**：MAX_POSITION_PER_TICKER = $500 ✅ 合理

**跨平台套利风险**：
- 定义不匹配是最大风险（上面 85¢ 价差很可能是这个原因）
- 资金无法同时在两平台，存在执行时间差
- **建议**：仅在完全确认定义一致后才执行套利

**新闻驱动风险**：
- 假新闻/误导性新闻
- 新闻速度竞争（专业做市商更快）
- **我们的优势**：散户市场信息反应慢，有分钟级窗口

---

## 8. Kalshi vs Polymarket 全面对比

| 维度 | Kalshi | Polymarket |
|------|--------|------------|
| **监管** | CFTC 监管 ✅ | 正在获取 CFTC 牌照（via QCX） |
| **用户基础** | 美国散户为主 | 全球 crypto 用户 |
| **结算** | USD 银行转账 | USDC (链上) |
| **流动性** | 低-中（小市场 spread 大） | 高（热门市场极深） |
| **透明度** | 低（无法看到其他交易者） | 高（链上可审计） |
| **费用** | ~0.7%/side | 0.01-2% |
| **市场种类** | 政治+经济+天气+提及+体育 | 政治+经济+体育+crypto |
| **独有优势** | 天气市场、规则专家可利用 | 透明度、跟单工具 |
| **API** | REST + WebSocket | REST + CLOB (链上) |
| **做市** | 可以，需要 API | 可以，有 rewards 程序 |
| **全球扩张** | $300M 融资，扩展 140 国 | 即将美国重新上线 |
| **竞争格局** | CME、Robinhood 进入 | Coinbase 等新玩家 |

### 各平台最佳用途

- **Kalshi**：经济指标 Junk Bonding + 天气 + 规则套利
- **Polymarket**：高流动性事件交易 + 跟单 + 信息速度套利
- **两者结合**：跨平台信息速度差套利

---

## 9. 可执行策略建议

### 策略 1：增强版 Junk Bonding（立即可执行）⭐⭐⭐⭐⭐

**改进点**：整合 Nowcast 数据 + 新闻验证 + endgame 时间窗口

```
具体操作：
1. 每天运行 report_v2.py + endgame_scanner.py
2. 对 Score ≥ 70 的机会：
   a. 检查官方数据源 Nowcast（CPI: Cleveland Fed, GDP: Atlanta GDPNow）
   b. 读 Kalshi 评论区
   c. 检查合约 PDF 边界条件
3. 如果三重验证通过 → 下单（限价单，maker）
4. 每 2 小时 dynamic_trader.py 监控

资金分配：
- 单笔 $50-100（paper trading 阶段）
- 真金阶段：$200-500/笔，总上限 $3000
```

### 策略 2：新闻→市场信息速度差（高 Alpha）⭐⭐⭐⭐

**改进点**：自动化新闻匹配 + 快速验证 + 告警

```
具体操作：
1. news_scanner.py 每小时运行
2. 检测到重大新闻 → 匹配 Kalshi 市场
3. 如果市场价格未反映 → Telegram 告警
4. Jason 人工确认后快速执行

重点关注新闻类型：
- 官方声明、行政命令、数据发布
- 法院裁决、国会投票
- 外交事件（会面、电话、协议）
```

### 策略 3：天气市场专项（新方向）⭐⭐⭐⭐

**理由**：Kalshi 独有品类，竞争较少，NWS 数据公开

```
具体操作：
1. 新建 weather_scanner.py
2. 整合 NWS API 预报数据
3. 找 NWS 预报 vs Kalshi 价格的偏差
4. 重点：极端天气事件（暴风雪、极寒）时散户恐慌定价

市场类型：
- 城市降雪量 (KXSNOWSTORM)
- 城市最低温度 (KXLOWT)
- 月度降雪总量 (KXBOSSNOWM 等)
```

### 策略 4：跨平台信号（增量改进）⭐⭐⭐

```
具体操作：
1. crossplatform.py 每 4 小时运行
2. 严格匹配（相同事件、相同结算条件、相同时间窗口）
3. 仅在价差 > 5¢ 且定义完全一致时告警
4. 优先用 Polymarket 作为"信号源"（更活跃），Kalshi 执行
```

### 策略 5：到期窗口扫描（低风险）⭐⭐⭐⭐

```
具体操作：
1. expired_window.py 每天运行
2. 找时间窗口已过的市场（标题含月份/日期）
3. 自动搜索事件是否已发生
4. 价格 vs 事实不符 → 告警

经典案例：
- "January" 市场在 2月还没结算
- "Before Feb 1" 市场已过期
- Putin 通话就是这类机会
```

---

## 10. 下一步行动

### 立即（今天-明天）

- [ ] **确认 GDP Q4 初值**：Jan 30 BEA 已发布 GDP 数据，确认我们 4 笔 GDP paper trade 的结果预期
- [ ] **查看 CPI Nowcast**：Cleveland Fed 对 Jan CPI 的预测，确认 2 笔 CPI paper trade 方向
- [ ] **政府关门评估**：当前 shutdown 是否可能本周结束？评估 KXGOVSHUTLENGTH 系列
- [ ] **运行 endgame_scanner.py 最新扫描**：更新机会列表

### 本周

- [ ] **实现 weather_scanner.py**：整合 NWS API，扫描天气市场机会
- [ ] **完善 crossplatform.py 定义匹配**：增加合约 PDF 比对，避免假套利
- [ ] **WebSocket 实时监控上线**：完成依赖安装，测试实时价格流
- [ ] **Paper trade 到 20 笔**：Feb 11 CPI 结算后复盘，调整策略

### 本月

- [ ] **Paper trading 验证**：目标 20+ 笔，胜率 >70%
- [ ] **真金转换评估**：如果 paper trade 胜率达标，首笔真金 $50 测试
- [ ] **自动化告警系统**：news_scanner + endgame + cross-platform → Telegram bot 推送
- [ ] **天气策略回测**：用 NWS 历史数据 vs Kalshi 历史价格验证

### Q1 2026 目标

- [ ] 真金交易系统上线，首月目标 +20%
- [ ] 全自动扫描管道（每小时运行，自动告警）
- [ ] 至少 3 种策略同时运行（Junk Bond + 新闻 + 天气）
- [ ] 评估做市策略可行性（需要更多资金）

---

## 附录 A：社区策略总结（Medium/Twitter 研究）

### 已被验证无效的策略

1. **"Liquidity bot draining"** — 在薄市场下单诱骗奖励 bot，然后 trade against it
   - Medium 上多篇文章揭露这是伪策略
   - 条件太苛刻：需要 bot 行为可预测 + 市场足够薄 + 无 adverse selection
   - **结论**：不值得尝试

2. **"Free money" parity arbitrage** — 在同一平台买 YES + NO 总成本 <$1
   - 理论可行但实际上 spread 和费用吃掉利润
   - 我们的 parity_scanner.py 最近扫描：0 opportunities
   - **结论**：持续监控但不依赖

### 新兴趋势

1. **AI Agent 做市** — 用 LLM 分析合约规则 + 新闻，自动做市
   - 这正是我们在构建的方向
   - 竞争加剧：多篇文章预测 2026 AI agents 将大量进入
   - **结论**：先发优势重要，加快自动化

2. **预测市场期权化** — 将 binary 合约当作 binary options 使用
   - "Will BTC close above $150k on June 30?" ≈ binary option
   - 可以用来对冲 crypto 仓位
   - **结论**：有趣但不是我们的核心方向

3. **Insurance/Hedging 用途** — 用天气市场对冲真实经济风险
   - Kalshi 博客多次推广这个角度
   - **结论**：教育性内容，对我们交易策略无直接帮助

---

## 附录 B：竞争格局变化（2026）

- **CME Group** 计划上线体育市场 — 机构级别竞争
- **Coinbase** 进入预测市场 — crypto 用户导入
- **Robinhood** 收购 MIAXdx — 零售经纪商进入
- **Kalshi** $300M 融资，扩展到 140 国 + 链上整合（Jupiter, Phantom）
- **Polymarket** 通过 QCX 获取 CFTC 牌照，即将美国重新上线

**影响评估**：
- 更多参与者 → 市场更高效 → 简单 alpha 消失
- 但也意味着更多流动性 + 更多市场种类
- 我们的优势（规则理解 + 新闻速度 + 自动化）仍然有效
- 需要持续提升速度和准确性

---

*报告完成于 2026-02-03T15:55Z*
*数据来源：Kalshi API、Polymarket API、Medium、Kalshi Blog、项目代码分析*
