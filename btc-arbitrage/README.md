# BTC Arbitrage Bot

**Real-time arbitrage trading system for Kalshi KXBTC15M prediction markets**

## 🔩 [IRON RULES](IRON_RULES.md) — READ FIRST

Before writing any code, read `IRON_RULES.md`. Non-negotiable principles for this project.
Core mandate: **Research → Data → Trade 正循环。永远不要跳过。**

## 📊 Project Overview

This project explores arbitrage opportunities in Kalshi's 15-minute Bitcoin price prediction markets (KXBTC15M) by monitoring the delay between real-time BTC price movements and market price updates.

### Market Structure

Kalshi KXBTC15M markets ask: **"Will BTC price go UP in the next 15 minutes?"**
- New market every 15 minutes
- Binary outcome: YES or NO
- Settlement: Based on CF Benchmarks BRTI (Bitcoin Real-Time Index)
- BRTI aggregates prices from: Coinbase, Kraken, Bitstamp, and others

### The Opportunity

**Hypothesis:** Market prices may lag behind real-time BTC movements, creating brief arbitrage windows.

**Two potential mechanisms:**
1. **CF Benchmarks Delay** - BRTI might update slower than individual exchanges
2. **Market Maker Lag** - Human traders may be slow to update orders after BTC moves

## 🎯 Current Status: Phase 1 - Data Collection

**What's Running:**
- ✅ BRTI Proxy (aggregates Binance.US + Coinbase + Kraken)
- 🔄 6-hour continuous monitor (started 2026-02-02 02:00 UTC)
- 📊 Data collection for strategy validation

**Completed:**
- Binance.US API integration
- CF Benchmarks BRTI research
- BRTI proxy implementation (3-exchange aggregation)
- Monitoring infrastructure
- Backtesting framework

**Next:**
- Analyze collected monitoring data
- Validate BRTI proxy accuracy vs actual settlements
- Backtest potential strategies
- **GO/NO-GO decision** on pursuing this opportunity

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Sources                            │
├─────────────────────────────────────────────────────────────┤
│  Binance.US    Coinbase    Kraken    │    Kalshi API      │
│     REST         REST        REST     │       REST         │
└─────┬──────────┬──────────┬──────────┴────────┬────────────┘
      │          │          │                    │
      └──────────┴──────────┴───────┐            │
                                    ▼            ▼
                            ┌─────────────────────────┐
                            │   BRTI Proxy Engine     │
                            │  (Weighted Average)     │
                            └───────────┬─────────────┘
                                        │
                                        ▼
                            ┌─────────────────────────┐
                            │  Arbitrage Detection    │
                            │  - Delay monitoring     │
                            │  - Signal generation    │
                            └───────────┬─────────────┘
                                        │
                                        ▼
                            ┌─────────────────────────┐
                            │  Strategy Engine        │
                            │  - Delay arbitrage      │
                            │  - Momentum trading     │
                            └───────────┬─────────────┘
                                        │
                                        ▼
                            ┌─────────────────────────┐
                            │   Kalshi Trading API    │
                            │  (Order Execution)      │
                            └─────────────────────────┘
```

## 📁 Project Structure

```
btc-arbitrage/
├── README.md                   # This file
├── STATUS.md                   # Current project status
├── ROADMAP.md                  # Implementation phases
├── FINDINGS.md                 # Research notes
├── COMMUNITY_RESEARCH.md       # Strategy analysis
├── PIVOT_ANALYSIS.md           # Strategy comparison
│
├── scripts/
│   ├── brti_proxy.py           # BRTI price calculator
│   ├── continuous_monitor.py   # Long-running data collector
│   ├── settlement_tracker.py   # Settlement validation
│   ├── backtest_framework.py   # Strategy testing
│   ├── measure_delay_binance_us.py
│   ├── test_binance_us.py      # API verification
│   └── (other utilities)
│
├── src/
│   └── binance_monitor.py      # Binance.US price monitor
│
└── data/
    ├── continuous_*.json       # Monitoring data
    ├── settlements.json        # Settlement tracking
    └── delay_measurement_*.json
```

## 🔧 Setup

### Prerequisites
- Python 3.11+
- Internet connection
- No API keys required for data collection phase

### Quick Start

1. **Clone & Navigate:**
```bash
cd btc-arbitrage
```

2. **Test BRTI Proxy:**
```bash
python3 scripts/brti_proxy.py
```

3. **Start Monitoring (1 hour):**
```bash
python3 scripts/continuous_monitor.py 60 15
```

4. **Track Settlements:**
```bash
python3 scripts/settlement_tracker.py
```

## 📊 Data Collection

### BRTI Proxy

Our proxy aggregates 3 major exchanges:
- **Binance.US** (33.3% weight)
- **Coinbase** (33.3% weight)
- **Kraken** (33.4% weight)

**Accuracy:** Exchange spread typically <0.1%, suggesting tight pricing.

### Monitoring Metrics

- BRTI Proxy price
- Kalshi YES bid/ask
- Price change percentages
- Arbitrage window detection
- Settlement outcomes

## 🎯 Strategy Options

### Option A: Delay Arbitrage
- **Concept:** Trade when BRTI moves but Kalshi lags
- **Requirement:** BRTI proxy must accurately predict settlements (>95%)
- **Risk:** Competition, execution speed

### Option B: Logic/Momentum Arbitrage
- **Concept:** Use BTC momentum to predict direction
- **Advantage:** Doesn't require perfect BRTI proxy
- **Requirement:** Strong predictive model

## 📈 Decision Criteria

**Proceed with Delay Arbitrage if:**
- ✅ BRTI proxy accuracy >95%
- ✅ Windows appear >5 times/day
- ✅ Windows last >10 seconds
- ✅ Backtest win rate >60%

**Pivot to Logic Arbitrage if:**
- ❌ BRTI proxy insufficient
- ❌ Delay windows too rare
- ✅ Momentum signals show edge

## ⚠️ Risk Management

### Pre-Live Trading
- Extensive backtesting required
- Paper trading mandatory (7+ days)
- Success criteria: Win rate >60%, Sharpe >1.5

### Live Trading Limits
- Start capital: $100-500
- Max trade size: $10-20
- Daily loss limit: $50
- Kill switch: 5 consecutive losses

## 📚 Key Resources

- [Kalshi API Docs](https://trading-api.readme.io/reference/getting-started)
- [CF Benchmarks BRTI](https://www.cfbenchmarks.com/data/indices/BRTI)
- [Binance.US API](https://docs.binance.us/)
- [Project Roadmap](ROADMAP.md)
- [Research Findings](FINDINGS.md)

## 🔬 Research Background

This project originated from Twitter research into Kalshi arbitrage strategies:
- [@xmayeth](https://x.com/xmayeth/status/2011460579500659030) - BTC delay arbitrage
- [@w1nklerr](https://x.com/w1nklerr) - Logic arbitrage approach

**Key Discovery:** Kalshi settles to CF Benchmarks BRTI, NOT raw exchange prices. This adds complexity but also opportunity if our proxy is accurate.

## 📊 Performance Tracking

*Will be updated once data collection completes*

**Metrics to track:**
- BRTI proxy accuracy vs settlements
- Arbitrage window frequency
- Average window duration
- Backtest results
- Paper trading P&L
- Live trading performance

## 🚀 Future Enhancements

**Phase 1+:**
- WebSocket integration for lower latency
- Multi-asset support (ETH, SOL, etc.)
- Advanced ML models for prediction
- Co-location for execution speed

## 📝 License & Disclaimer

**Educational purposes only.** Trading carries risk. No guarantees of profitability. Always start small and test thoroughly.

---

**Status:** Active Development - Phase 1  
**Last Updated:** 2026-02-02  
**Maintainer:** JZ + AI Co-founder
