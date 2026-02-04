# STATUS.md — 美股市场报告系统
Last updated: 2026-02-03T17:42Z

## 当前状态: 进行中

## 已完成
- ✅ market_report.py — 核心报告生成器（指数、板块、宏观、个股、警报）
- ✅ send_report.sh — flag 文件机制（备用）
- ✅ alert_monitor.sh — 异动监控脚本（备用）
- ✅ Cron jobs 已配置（4个）
- ✅ 首次测试成功 — 触发了6个警报

## Cron 计划
| Job | 时间 (UTC) | 说明 |
|-----|-----------|------|
| market-report-premarket | 14:25 Mon-Fri | 盘前报告（开盘前5分钟）|
| market-report-midday | 17:00 Mon-Fri | 午间报告 |
| market-report-close | 21:05 Mon-Fri | 收盘报告 |
| market-alert-monitor | */15 14-21 Mon-Fri | 异动监控（每15分钟，仅有警报时发送）|

## 监控的标的
- **指数**: S&P 500, Nasdaq, Dow, Russell 2000
- **板块**: 11个 SPDR 行业 ETF
- **宏观**: VIX, 黄金, 原油, 10Y国债, 美元指数, BTC
- **个股**: Mag7 + 软件/AI + 银行 + 零售 + 医药 + Crypto（23只）

## 警报阈值
- 指数 > ±1.5%
- VIX > 25 或日变 > ±15%
- 板块 > ±3%
- 个股 > ±8%

## 下一步
- [ ] 添加盘前期货数据
- [ ] 添加财报日历提醒
- [ ] 添加 Jason 自选股 watchlist 配置
- [ ] 报告中加入 AI 分析（原因总结）
- [ ] 历史数据对比（vs 昨天、vs 上周）

## Blockers
无

## 关键决策
- 用 yfinance 而非付费 API（免费、够用）
- 异动监控每15分钟（平衡成本和及时性）
- 用 Sonnet 跑监控（省钱），Opus 跑定时报告
