# BTC Price Arbitrage Bot - Research

## 策略来源
**Twitter**: [@xmayeth的推文](https://x.com/xmayeth/status/2011460579500659030)  
**Trader**: 0x8dxd  
**Performance**: $614,965 profit, 97%+ win rate in one month  
**Profile**: https://polymarket.com/@0x8dxd?via=maycrypto

## 核心策略

### 套利循环
1. **读取实时BTC走势**
   - 监控Binance 5分钟K线
   - 检测波动性出现的瞬间

2. **检查Polymarket延迟定价**
   - 对比Binance最新价格和Polymarket慢速更新的赔率
   - 寻找短暂的不同步窗口

3. **在延迟窗口进场**
   - BTC涨 → 在Polymarket调整前买YES
   - BTC跌 → 在Polymarket调整前买NO

4. **价格同步后退出**
   - Polymarket价格追上Binance后平仓

## 关键问题需要研究

### 1. Kalshi是否有BTC价格市场？
**初步搜索结果：**
- 在Kalshi series中未找到BTC相关市场
- Polymarket有1个BTC事件（MicroStrategy相关）
- **需要确认：** Kalshi是否有"BTC价格在X时间达到Y"类型的市场

**如果Kalshi没有：**
- 专注Polymarket
- 或者等Kalshi推出相关市场
- 或者pivot到其他资产（股票、指数）

### 2. Polymarket的BTC市场结构
**需要研究：**
- 市场类型（二元结果 vs 范围区间）
- 流动性如何
- 订单簿深度
- 手续费结构

### 3. 延迟窗口大小
**需要测量：**
- Binance价格变动 → Polymarket价格更新的平均延迟
- 是几秒？几十秒？还是分钟级？
- 延迟是否稳定？

### 4. 执行速度要求
**技术栈评估：**
- Binance WebSocket（实时推送）
- Polymarket CLOB API（下单速度？）
- 服务器位置（延迟优化）
- 并发处理（asyncio vs multiprocessing）

### 5. 利润空间计算
**成本因素：**
- Polymarket手续费
- 滑点（订单簿深度不足）
- Gas费（如果是链上交易）
- 资金占用成本

**最小套利空间：**
- 需要覆盖所有成本
- 考虑失败率（价格反向移动）

## 下一步研究任务

### Phase 1: 市场调研（今天）
- [ ] 深入搜索Polymarket所有BTC相关市场
- [ ] 研究0x8dxd的公开交易记录
- [ ] 找到类似策略的其他案例
- [ ] 确认Kalshi是否有价格预测市场

### Phase 2: 技术可行性（1-2天）
- [ ] 搭建Binance WebSocket监控
- [ ] 测试Polymarket API响应时间
- [ ] 回测历史数据（Binance vs Polymarket价格）
- [ ] 计算实际延迟窗口

### Phase 3: 原型开发（3-5天）
- [ ] 构建实时监控系统
- [ ] 实现自动下单逻辑
- [ ] 风险控制（止损、仓位管理）
- [ ] Paper trading测试

### Phase 4: 实盘测试（1-2周）
- [ ] 小资金测试
- [ ] 监控胜率和盈亏
- [ ] 优化参数
- [ ] 评估可扩展性

## 风险清单

1. **竞争激烈** - 其他bot可能也在做
2. **延迟缩小** - 市场可能会加快更新
3. **流动性不足** - 无法按预期价格成交
4. **技术故障** - API断线、网络延迟
5. **监管风险** - Polymarket可能限制高频交易
6. **资金风险** - 价格反向移动时的损失

## 参考资料
- @xmayeth推文: https://x.com/xmayeth/status/2011460579500659030
- Polymarket CLOB API: https://docs.polymarket.com
- Binance WebSocket API: https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams
- 0x8dxd profile: https://polymarket.com/@0x8dxd?via=maycrypto
