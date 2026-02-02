# BTC Arbitrage Bot - Project Status

Last updated: 2026-02-02T01:16Z

## 当前状态: 🔬 Phase 1 - Research (Active)

## 重大发现 ✅

### 1. Kalshi有15分钟BTC价格市场！
**Series**: KXBTC15M - "Bitcoin price up down"  
**Frequency**: Every 15 minutes  
**Current market**: KXBTC15M-26FEB012030-30

**Market details:**
- Question: "BTC price up in next 15 mins?"
- YES bid/ask: 36¢ / 39¢ (3¢ spread)
- Volume: $687 (⚠️ LOW)
- Closes: 2026-02-02T01:30:00Z

**Similar markets:**
- KXETH15M: ETH 15-minute predictions
- BTCD: Daily BTC above/below (currently no active markets)

### 2. Polymarket有crypto事件
- MicroStrategy Bitcoin sales: $19.7M volume
- Trump crypto tax: $89k volume
- MegaETH markets: $8.8M volume

**问题**: Polymarket的crypto事件大多是长期事件，不适合短期价格套利。

## 策略调整 🎯

**原计划**: Binance → Polymarket 价格延迟套利  
**新发现**: Kalshi KXBTC15M 更适合这个策略

**为什么Kalshi更好:**
1. ✅ 专门的15分钟价格预测市场
2. ✅ 每15分钟新市场（高频机会）
3. ✅ 问题清晰（价格上涨 vs 下跌）
4. ⚠️ 但流动性低（$687 vs Polymarket百万级）

## 当前测试

### 测量Binance → Kalshi延迟
**脚本**: `scripts/measure_delay.py` (运行中)

**测试方法:**
- 每5秒采样Binance BTC价格
- 同时获取Kalshi KXBTC15M价格
- 记录价格变化和时间戳
- 共60秒观察

**限制**: REST API有5秒间隔，无法精确测量秒级延迟  
**下一步**: 需要WebSocket实时监控

## 关键问题

### ✅ 已解答
1. **市场是否存在?** YES - Kalshi KXBTC15M
2. **平台选择?** Kalshi > Polymarket (对短期价格套利)

### ⚠️ 待解答
1. **延迟有多大?** 测试中...
2. **流动性是否足够?** 仅$687/市场，可能不足
3. **Spread成本?** 3¢ (很大，吃掉利润空间)
4. **Binance价格变动是否影响Kalshi赔率?** 需要验证相关性

### 🚨 新发现的风险
1. **低流动性** - $687成交量太小，大单会滑点
2. **大Spread** - 3¢ bid-ask差价是成本
3. **市场频率** - 每15分钟才有新市场，不是连续的
4. **不确定是否有延迟** - 可能Kalshi已经实时跟踪Binance

## 下一步 (Today)

### 正在进行
- [x] 搜索Kalshi crypto市场
- [x] 发现KXBTC15M系列
- [x] 获取市场详情
- [ ] 延迟测量 (60s测试运行中)

### 待办 (接下来1小时)
- [ ] 分析延迟测试结果
- [ ] 搭建Binance WebSocket监控
- [ ] 测试Kalshi API下单速度
- [ ] 回测：BTC价格变化 vs Kalshi赔率变化
- [ ] 计算盈利空间（考虑spread + 手续费）

### 待办 (今天完成)
- [ ] Go/No-Go决策
- [ ] 如果GO: 搭建原型监控系统
- [ ] 如果NO: pivot到其他策略

## 技术栈

**已确认:**
- Binance WebSocket API (实时BTC价格)
- Kalshi REST API (市场数据 + 下单)
- Python asyncio (并发监控)

**待评估:**
- 服务器位置（需要低延迟?）
- 风险控制逻辑
- 仓位管理策略

## 参考资料

- Kalshi KXBTC15M: https://kalshi.com/markets/kxbtc15m
- Binance WebSocket: https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams
- 原始灵感: @xmayeth推文

## Files Created

```
btc-arbitrage/
├── STATUS.md (this file)
├── README.md
├── RESEARCH.md
├── scripts/
│   ├── search_markets.py (✅ completed)
│   ├── analyze_kalshi_crypto.py (✅ completed)
│   ├── get_btc_markets.py (✅ completed)
│   └── measure_delay.py (⏳ running)
└── data/
    └── delay_measurement.json (⏳ generating)
```

## 🚨 API Access Issue

**Problem**: Kalshi API返回 HTTP 451 (Unavailable For Legal Reasons)  
**Likely cause**: Geographic restriction or rate limiting

**Impact**:
- 无法通过当前服务器访问Kalshi API
- delay measurement脚本失败

**Solutions to explore**:
1. 使用代理/VPN
2. 部署到US服务器
3. 联系Kalshi获取API access
4. 先用公开数据手动分析

**Workaround for now**:
- 手动观察Kalshi网页版市场
- 使用public archived data (if available)
- Focus on Binance WebSocket setup first

---

**Updated**: 2026-02-02T01:17Z

## 🚨 Critical Blocker Update

**NEW ISSUE**: Binance API also returns HTTP 451  
**Impact**: Cannot monitor BTC price from current server

**Both APIs blocked:**
- ❌ Kalshi API: HTTP 451
- ❌ Binance API: HTTP 451

**Root cause**: Server IP (45.55.78.247) appears to be geographically restricted

**This blocks ALL development**:
- Cannot monitor Binance prices
- Cannot access Kalshi markets
- Cannot test arbitrage strategy

**Required actions**:
1. Deploy to US-based server
2. Or use VPN/proxy service
3. Or contact both platforms for API access

**Status**: 🛑 **BLOCKED** - Cannot proceed without API access

---

**Updated**: 2026-02-02T01:18Z
