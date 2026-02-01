# Kalshi Tools Research — 2026-02-01

## 发现的开源项目

### 1. pmxt (⭐440) — 统一预测市场 API
- https://pmxt.dev
- 统一 API 接口，支持 Polymarket + Kalshi + 其他平台
- **这就是我们跨平台对比需要的！**

### 2. prediction-market-arbitrage-bot (⭐78)
- https://github.com/realfishsam/prediction-market-arbitrage-bot
- **Polymarket ↔ Kalshi 跨平台套利 bot**
- 使用 fuzzy matching（Jaccard + Levenshtein）自动配对两个平台的市场
- 实现了合成套利：一个平台买 YES，另一个买 NO
- 用 Market Orders 同时执行
- **这解决了我们之前"市场不匹配"的问题！**

### 3. dr-manhattan (⭐129) — CCXT for prediction markets
- https://github.com/guzus/dr-manhattan
- 支持 Polymarket, Kalshi, Opinion, Limitless, Predict.fun
- 统一的 exchange interface
- WebSocket 实时数据
- Strategy base class

### 4. Kal-trix-prediction-bot (⭐8)
- AI-powered Kalshi 交易系统
- 值得看看他们的策略实现

### 5. polymarket-kalshi-btc-arbitrage-bot (⭐131)
- BTC 价格预测市场的跨平台套利
- 实时监控价差

## 关键洞见

1. **跨平台套利已经有成熟工具** — 不需要自己写 fuzzy matching
2. **pmxt 提供统一 API** — 可以同时访问多个平台
3. **Market matching 用 Jaccard + Levenshtein** — 比我们之前用的简单关键词匹配好很多
4. **关键问题不是工具，是速度** — 套利机会可能很短暂

## 下一步
- [ ] 安装 pmxt 或 dr-manhattan 试试
- [ ] 用 arbitrage bot 的 matching 逻辑改进我们的 crosscheck.py
- [ ] 研究这些 bot 的策略实现
- [ ] 评估是否值得接入 Kalshi API（需要 API key）
