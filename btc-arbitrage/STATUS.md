# STATUS.md — BTC Arbitrage Bot
Last updated: 2026-02-02T23:13Z

## 当前状态: 进行中

## 最后做了什么
- ❌🔧 **v6 BUG FIX + 重启** (23:09-23:13)
  - **问题**: v6在20:09崩溃，运行仅31分钟（应该8小时）
  - **根本原因**: `asyncio.gather(*tasks)` 没有 `return_exceptions=True`
    - 任一WebSocket断开 → 整个bot崩溃
    - **这是v3的同一个bug** — 创建v6时未修复就复制了
    - 违反了 AGENTS.md Iron Law #3 (应该先检查v3失败原因，再创建v6)
  - **修复**:
    1. ✅ `asyncio.gather(*tasks, return_exceptions=True)`
    2. ✅ 所有4个WebSocket添加错误日志
    3. ✅ 重启 v6 (PID: 141721, 23:13 UTC)
  - **结果**: 之前运行31分钟，8笔交易，+$3.50 P&L
  - **教训**: 已知bug必须在新版本中修复，不能重复犯错
- ✅ **v4 Major Strategy Overhaul** (19:52-19:54)
  - Complete rewrite with 6 new features:
    1. BTC spot price direction filter (Binance REST + WebSocket feeds)
    2. Polymarket daily trend sentiment filter
    3. Volatility-adaptive stop-loss (20-30%, was 12% fixed)
    4. Time window filters (skip first 30s, last 60s, require >5min remaining)
    5. Fair value estimation (BTC vs window open, time remaining, volatility)
    6. Crash classification (liquidity vs informational vs delayed reaction)
  - 1-minute test: ✅ Runs cleanly, all feeds connected, proper logging
  - File: `src/realtime_paper_trader_v4.py`

- ✅ **v6创建完成** (19:36-19:38)
  - 实现RESEARCH-NOTES.md Priority 1-5改进
  - BTC momentum filter for crash detection
  - Volatility-adaptive stop-loss (15-40%)
  - Entry quality filters (time/spread/volume)
  - Mean reversion at extremes (<20¢, >80¢)
  - Market timing restrictions (exclude first/last 30s)
  - Dual market support (15min + hourly)
  
- ✅ **v4/v5测试** (19:30-19:35)
  - v4: 5分钟测试通过，0交易，稳定性验证
  - v5: 已创建，未启动（v6优先）

- ~~🚀 **v6 8小时测试启动** (19:38)~~ ❌ 已崩溃（20:09）
  - PID: 132581 (已停止)
  - 运行时长: 31分钟（应该480分钟）
  - 结果: 8笔交易，+$3.50 P&L
  - 崩溃原因: asyncio.gather bug (同v3)
  
- 🚀 **v6 重启** (23:13)
  - PID: 141721
  - 预计完成: 2026-02-03 07:13 UTC (8小时)
  - 修复: return_exceptions=True + 错误日志
  - 策略: Delay Arb + Mean Reversion (改进版)

## Blockers
- （无）

## 下一步
1. **监控v6运行** — 每小时自动汇报
2. **对比v2/v3/v6结果** — 验证改进效果
3. **根据v6结果进一步优化** — 可能调整参数

## 关键决策记录
- 2026-02-02 23:13: **v6 BUG重复 → 紧急修复** — 创建v6时未检查v3失败原因，直接复制了同一个asyncio.gather bug。违反 Iron Law #3。必须建立pre-create检查：新版本必须修复已知的旧版本bug。
- 2026-02-02 19:36: **直接创建v6** — Jason授权不再询问，直接实施改进
- 2026-02-02 19:30: **v3问题诊断** — Flash Crash失败因为没有BTC momentum filter
- 2026-02-02 18:42: **v3神秘停止原因** — asyncio.FIRST_COMPLETED导致任一任务崩溃就退出

## 📊 Key Metrics (Updated 19:38)

**v6 Improvements (based on RESEARCH-NOTES.md):**
- ✅ BTC momentum filter for crash detection
- ✅ Adaptive stop-loss: 15-40% (was 12% fixed)
- ✅ Entry quality filters: time/spread/volume/cooldown
- ✅ Mean reversion: only at extremes (<20¢ or >80¢)
- ✅ Market timing: exclude first/last 30s
- ✅ Dual market: 15min + hourly

**Historical Test Results:**
- **v2**: 29min, 9 trades, 89% win, +$2.40
- **v3**: 30min, 5 trades, 0% win, -$6.00 (Flash Crash failed)
- **v4**: 5min, 0 trades, N/A, $0.00 (stable, no signals)
- **v6**: 运行中... (PID: 132581)

## 📁 Files

**Src:**
- `src/realtime_paper_trader_v6.py` — RESEARCH-NOTES.md改进版（当前运行）
- `src/realtime_paper_trader_v5_dual.py` — Dual market (未启动)
- `src/realtime_paper_trader_v4.py` — Flash Crash disabled (已测试)
- `scripts/run_v6_with_watchdog.sh` — 进程守护脚本

**Logs:**
- `logs/rt_v6_live.log` — 实时日志
- `logs/rt_v6_YYYYMMDD_HHMMSS.log` — 带时间戳日志

**Data:**
- `data/rt_v6_state.json` — 实时checkpoint（每5分钟）
- `data/rt_v6_YYYYMMDD_HHMMSS.json` — 最终结果（8小时后）

## 🚀 Tech Stack

**Data Sources:**
- BTC price: WebSocket streams (4 exchanges)
- Kalshi markets: REST API (15min + hourly, 5s polling)

**v6 Strategies:**
1. **Delay Arbitrage** (improved): BTC momentum vs Kalshi lag
   - NEW: Only when abs(BTC momentum) > 0.15%
   - NEW: BTC momentum filter prevents false signals
   
2. **Mean Reversion** (new): At extreme prices
   - K < 20¢ + BTC stable → buy YES
   - K > 80¢ + BTC stable → buy NO

**Risk Management:**
- Adaptive stop-loss: 15-40% (based on volatility)
- Profit target: 8%
- Timeout: 6 minutes
- Entry filters: time/spread/volume/cooldown

**Infrastructure:**
- Python 3.12 + websockets + asyncio
- Dual market polling (15min + hourly)
- Volatility-adaptive risk management
- Periodic state checkpoints

## 📅 Timeline

- **19:30** — v4启动5分钟测试
- **19:35** — v4测试完成（稳定性验证通过）
- **19:36** — Jason授权直接实施改进
- **19:38** — v6启动8小时测试
- **03:38** — 预计完成（明天）

## 🔔 Monitoring

每小时汇报（通过heartbeat自动发送）：
- 进程状态
- 交易统计
- 策略breakdown
- 当前P&L

每小时:45分自动发送到group。
