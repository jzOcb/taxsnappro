# BTC价格延迟套利Bot

## 状态
💡 规划中

## 描述
基于Binance和Kalshi/Polymarket之间的价格延迟套利机会。

**核心策略：**
1. 实时监控Binance BTC 5分钟K线
2. 检测Polymarket/Kalshi价格更新延迟
3. BTC涨 → 买YES（在市场调整前）
4. BTC跌 → 买NO（在市场调整前）
5. 价格同步后退出

**灵感来源：**
- Twitter: @xmayeth的推文
- Trader: 0x8dxd (97%胜率, $614k/月)
- 策略链接: https://x.com/xmayeth/status/2011460579500659030

## 平台
- Kalshi (主要目标)
- Polymarket (备选)

## 技术栈
- Binance WebSocket API (实时价格)
- Kalshi API (市场数据 + 交易)
- Python asyncio (并发监控)

## 关键挑战
1. **延迟窗口很短** - 可能只有几秒到几十秒
2. **需要快速执行** - API响应时间至关重要
3. **滑点控制** - 市场流动性可能不足
4. **交易成本** - 频繁进出需要考虑手续费

## 研究任务
- [ ] 分析Kalshi BTC相关市场（有哪些？流动性如何？）
- [ ] 测试Binance WebSocket延迟
- [ ] 测试Kalshi API下单速度
- [ ] 计算实际套利窗口大小
- [ ] 研究0x8dxd的交易记录（如果公开）
- [ ] 回测历史数据（Binance + Kalshi价格）

## 前置条件
- [ ] Kalshi API access（可能需要KYC + 资金）
- [ ] Binance API key
- [ ] 快速的服务器（低延迟）
- [ ] 足够的启动资金

## 风险
- **竞争者** - 其他bot可能也在做同样的事
- **市场适应** - Kalshi可能会加快价格更新
- **滑点** - 流动性不足时无法成交
- **资金被套** - 价格反向移动时损失

## 参考资料
- @xmayeth推文: https://x.com/xmayeth/status/2011460579500659030
- 0x8dxd profile: https://polymarket.com/@0x8dxd?via=maycrypto
- Kalshi BTC markets: 需要研究

## Tags
#套利 #BTC #高频 #规划中

## 优先级
中等 - 在当前Kalshi Trading System验证成功后考虑
