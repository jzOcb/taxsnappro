# STATUS.md — BTC Arbitrage Bot
Last updated: 2026-02-02T17:20Z

## 当前状态: 进行中 — WebSocket实时数据pipeline完成，v2 paper trader运行中

## 最后做了什么 (过去2小时)
- ✅ **实现WebSocket实时数据feed** (无需API key)
  - Coinbase, Kraken, Bitstamp, Binance US 公开WebSocket
  - Volume-weighted BRTI proxy (35%/25%/20%/20%)
  - Kalshi REST 5秒轮询
  - 延迟: 20-30秒 → <1秒 ⚡
  
- ✅ **实时Paper Trader v1**
  - 检测到2次Flash Crash信号（市场结算切换造成的假信号）
  - 10分钟后进程死亡（无错误信息）
  
- ✅ **实时Paper Trader v2** (17:18 启动，运行中)
  - 避免市场切换时刻交易
  - 改进flash crash检测逻辑
  - 增强错误处理和日志
  - 运行480分钟 → 明天01:18 UTC

## Blockers
- ❌ Subagent spawn机制不工作（session创建但不执行）
- ⚠️  v1 flash crash策略在市场结算时产生假信号

## 下一步
1. **监控v2运行** — 明天早上查看完整8小时结果
2. **BRTI proxy准确度验证** — 积累更多settlement数据
3. **策略优化** — 根据v2结果调整参数
4. **考虑hourly markets** — 如果15分钟市场仍然不够profitable

## 关键决策记录
- 2026-02-02 16:42: **不需要Kalshi API key** — 公开WebSocket可获取BTC实时价格
- 2026-02-02 16:56: **WebSocket基础设施完成** — 4交易所实时feed
- 2026-02-02 17:05: **v1 paper trader启动** — 检测到flash crash但是假信号
- 2026-02-02 17:18: **v2 paper trader启动** — 改进逻辑避免市场切换

## 📊 Key Metrics (Updated 17:20)

**WebSocket Infrastructure:**
- Exchanges: 4 (Coinbase, Kraken, Bitstamp, Binance US) ✅
- Latency: <1s (was 20-30s) ✅
- BRTI weighting: Volume-weighted (was equal) ✅
- Kalshi polling: 5s (was 60s) ✅

**Paper Trading v2 (running):**
- Start: 17:18 UTC
- Duration: 8 hours (480 min)
- Expected finish: 2026-02-03 01:18 UTC
- PID: $(cat /tmp/rt_v2_pid.txt 2>/dev/null || echo 'unknown')

**Historical Results:**
- Delay Arb (REST, 16h): 3 trades, 67% win, +$0.10
- Momentum (REST, 13h): 79 trades, 51% win, -$108
- v1 Real-time (10min): 2 trades, 0% win, -$4.20 (假信号)

## 📁 Files

**Src:**
- `src/realtime_feed.py` — WebSocket BTC feed (4 exchanges) + Kalshi poller
- `src/realtime_paper_trader.py` — v1 (已失败)
- `src/realtime_paper_trader_v2.py` — v2 (运行中)

**Logs:**
- `logs/rt_v2_live.log` — v2实时日志
- `logs/rt_v2_YYYYMMDD_HHMMSS.log` — v2详细日志（带时间戳）

**Data:**
- `data/rt_v2_YYYYMMDD_HHMMSS.json` — v2运行结果（8小时后）

## 🚀 Tech Stack

**Data Sources:**
- BTC price: WebSocket streams (public, no auth)
- Kalshi markets: REST API (public, no auth)

**Strategy:**
- Delay Arbitrage: BRTI momentum vs Kalshi lag
- Flash Crash Detection: Sudden Kalshi price drops (避免市场切换)

**Infrastructure:**
- Python 3.12 + websockets 14.2
- Asyncio concurrent feeds
- Volume-weighted BRTI proxy
