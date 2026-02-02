# BTC Price Arbitrage Bot

Binance ↔ Polymarket/Kalshi price delay arbitrage bot

## 📋 Current Status: **Phase 1 - Research**

### What We Know

**Strategy Source:**
- Twitter: [@xmayeth](https://x.com/xmayeth/status/2011460579500659030)
- Reference trader: 0x8dxd (97% win rate, $614k profit/month)
- Method: Monitor Binance BTC 5min candles → trade on Polymarket before price updates

**Core Arbitrage Loop:**
1. Binance BTC moves up/down
2. Polymarket price updates with delay
3. Bot trades in the delay window
4. Exit when prices sync

### What We Need to Find Out

#### 🔍 Priority 1: Does this market exist?
- [ ] **Kalshi**: Do they have BTC price prediction markets?
- [ ] **Polymarket**: What BTC markets are currently active?
- [ ] Market structure: Binary (YES/NO) or range-based?

#### 📊 Priority 2: Is it profitable?
- [ ] Measure actual delay: Binance → Polymarket price update
- [ ] Check liquidity: Can we enter/exit without slippage?
- [ ] Calculate fees: Trading costs + gas (if on-chain)
- [ ] Estimate win rate: How often does delay window appear?

#### ⚙️ Priority 3: Can we build it?
- [ ] Binance WebSocket API documentation
- [ ] Polymarket CLOB API speed test
- [ ] Server latency requirements
- [ ] Backtest with historical data

## 🛠️ Tech Stack (Planned)

```
┌─────────────────┐
│  Binance WS API │  ← Real-time BTC price feed
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Arbitrage Bot  │  ← Monitor delay, execute trades
│   (Python)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Polymarket CLOB │  ← Place orders in delay window
│       API       │
└─────────────────┘
```

**Languages:** Python (asyncio for concurrent monitoring)  
**APIs:** Binance WebSocket, Polymarket CLOB  
**Infrastructure:** Low-latency VPS (TBD)

## 📚 Research Tasks

### Today (Phase 1)
```bash
# Search for active BTC markets
- [ ] Run: python3 scripts/search_polymarket_btc.py
- [ ] Check Kalshi series for crypto markets
- [ ] Study 0x8dxd's public trade history

# Understand the delay mechanism
- [ ] How often does Polymarket update prices?
- [ ] What triggers price updates?
- [ ] Average delay window size?
```

### This Week (Phase 2)
```bash
# Technical feasibility
- [ ] Setup Binance WebSocket listener
- [ ] Test Polymarket API response time
- [ ] Backtest delay windows (last 30 days data)
- [ ] Calculate minimum profitable delay

# Risk assessment
- [ ] Competition analysis (other bots?)
- [ ] Slippage simulation
- [ ] Max drawdown scenarios
```

## 🚨 Known Risks

1. **No market exists** - If Kalshi/Polymarket don't have BTC price markets, strategy is DOA
2. **Delay too small** - If window is <1 second, execution becomes impractical  
3. **High competition** - Other bots may have already captured this alpha
4. **Low liquidity** - Can't enter/exit at expected prices
5. **Technical failure** - API downtime, network lag kills the edge

## 📁 Project Structure

```
btc-arbitrage/
├── README.md           # This file
├── RESEARCH.md         # Detailed research findings
├── scripts/
│   ├── search_markets.py     # Find BTC markets
│   ├── measure_delay.py      # Test delay windows
│   └── backtest.py           # Historical simulation
├── src/
│   ├── binance_monitor.py    # WebSocket listener
│   ├── polymarket_trader.py  # Order execution
│   └── arbitrage_engine.py   # Core logic
└── data/
    ├── delays.csv            # Measured delays
    └── backtest_results.json # Simulation output
```

## 🎯 Success Criteria

**Minimum Viable Strategy:**
- ✅ BTC market exists with >$10k daily volume
- ✅ Average delay >3 seconds
- ✅ Backtest shows >60% win rate
- ✅ Expected profit >10% after fees

**Go/No-Go Decision:** End of Phase 2 (1 week)

## 🔗 Resources

- [@xmayeth's thread](https://x.com/xmayeth/status/2011460579500659030)
- [0x8dxd Polymarket profile](https://polymarket.com/@0x8dxd?via=maycrypto)
- [Polymarket CLOB docs](https://docs.polymarket.com)
- [Binance WebSocket docs](https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams)

---

**Last updated:** 2026-02-02  
**Status:** Research phase, no code yet
