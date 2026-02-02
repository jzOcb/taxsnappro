# BTC Arbitrage Bot - Implementation Roadmap

## Phase 1: Data Collection & Validation ✅ (IN PROGRESS)

**Goal:** Understand the market and validate our BRTI proxy

### Completed ✅
- [x] Switch to Binance.US API
- [x] Build BRTI proxy (3-exchange aggregation)
- [x] Test API accessibility
- [x] Initial delay measurement (30s test)
- [x] Continuous monitoring script
- [x] Settlement tracker script
- [x] Backtest framework

### In Progress 🔄
- [🔄] 6-hour continuous monitoring (running now)
- [ ] Collect 24-48h of BRTI proxy vs Kalshi data
- [ ] Track at least 5-10 market settlements
- [ ] Validate BRTI proxy accuracy (target: >95%)

### Deliverables
- `data/continuous_*.json` - Monitoring data
- `data/settlements.json` - Settlement tracking
- Proxy accuracy report

**Timeline:** 2-3 days

---

## Phase 2: Strategy Validation (NEXT)

**Goal:** Determine if delay arbitrage is viable OR pivot to logic arbitrage

### Tasks
- [ ] Analyze monitoring data for arbitrage windows
- [ ] Calculate window frequency (how often do they appear?)
- [ ] Measure window duration (how long do they last?)
- [ ] Backtest both strategies:
  - Delay Arbitrage
  - Momentum/Logic Arbitrage
- [ ] Calculate expected profitability after fees
- [ ] **GO/NO-GO Decision**

### Decision Criteria

**Proceed with Delay Arbitrage if:**
- ✅ BRTI proxy accuracy >95%
- ✅ Arbitrage windows appear >5 times per day
- ✅ Windows last >10 seconds
- ✅ Backtest shows >60% win rate
- ✅ Expected profit >$100/day after fees

**Pivot to Logic Arbitrage if:**
- ❌ BRTI proxy inaccurate
- ❌ Delay windows too rare/brief
- ✅ BTC momentum signals show predictive power

**Timeline:** 2-3 days

---

## Phase 3A: Delay Arbitrage Implementation (IF VIABLE)

### Tasks
- [ ] Implement WebSocket connections
  - Binance.US trades WebSocket
  - Kalshi order book WebSocket
- [ ] Build real-time BRTI calculator
- [ ] Implement order execution
  - Kalshi API authentication
  - Order placement
  - Position management
- [ ] Add risk management
  - Max position size
  - Stop-loss logic
  - Daily loss limits
- [ ] Paper trading mode
  - Simulate orders
  - Track hypothetical P&L

### Deliverables
- WebSocket monitoring system
- Order execution engine
- Risk management module
- Paper trading results

**Timeline:** 1 week

---

## Phase 3B: Logic Arbitrage Implementation (IF PIVOT)

### Tasks
- [ ] Feature engineering
  - BTC momentum indicators
  - Volatility measures
  - Volume patterns
  - Funding rate signals
- [ ] Model development
  - Train prediction model
  - Backtest on historical data
  - Optimize hyperparameters
- [ ] Integrate with Kalshi
  - API authentication
  - Order execution
  - Position sizing
- [ ] Risk management
  - Kelly criterion for sizing
  - Max drawdown limits
  - Portfolio constraints

### Deliverables
- Prediction model
- Feature pipeline
- Backtesting results
- Paper trading system

**Timeline:** 2 weeks

---

## Phase 4: Paper Trading

**Goal:** Validate strategy with real-time execution (no real money)

### Tasks
- [ ] Run paper trading for 7 days minimum
- [ ] Track all trades and P&L
- [ ] Monitor for edge cases
- [ ] Optimize parameters
- [ ] Stress test with different market conditions

### Success Criteria
- Win rate >60%
- Sharpe ratio >1.5
- Max drawdown <10%
- No critical bugs

**Timeline:** 1-2 weeks

---

## Phase 5: Live Trading (Small Scale)

**Goal:** Deploy with real money, start small

### Tasks
- [ ] Set up Kalshi account with real funds
- [ ] Start with $100-500 capital
- [ ] Max trade size: $10-20
- [ ] Monitor closely for first week
- [ ] Daily performance review
- [ ] Gradually scale if profitable

### Risk Controls
- Hard daily loss limit: -$50
- Max position size: $20
- Kill switch if 5 consecutive losses
- Manual review required for scaling

**Timeline:** 1 week initial, ongoing

---

## Phase 6: Scale & Optimize (IF PROFITABLE)

### Tasks
- [ ] Increase capital allocation
- [ ] Add more sophisticated features
- [ ] Optimize execution
- [ ] Reduce latency
- [ ] Consider VPS/co-location

### Scaling Milestones
- $500 → $1,000 (if 2 weeks profitable)
- $1,000 → $5,000 (if 1 month profitable)
- $5,000+ (if 3 months profitable + Sharpe >2)

**Timeline:** Months (conditional on profitability)

---

## Current Status: Phase 1 (Data Collection)

**Active:**
- 6-hour continuous monitor running (started 2026-02-02 02:00 UTC)
- BRTI proxy tested and working
- Settlement tracker ready to deploy

**Next Immediate Actions:**
1. Wait for 6-hour monitor to complete
2. Analyze collected data
3. Start settlement tracking
4. Run initial backtests
5. Make GO/NO-GO decision

**Estimated Time to Live Trading:** 3-6 weeks (if viable)

---

## Risk Mitigation

### Technical Risks
- **API failures** → Multiple fallback data sources
- **Latency issues** → WebSocket instead of REST, consider co-location
- **Data quality** → BRTI proxy validation, cross-check sources

### Market Risks
- **Competition** → Other bots may eliminate edge
- **Liquidity** → Start small, scale gradually
- **Market structure changes** → Monitor Kalshi for policy updates

### Execution Risks
- **Bugs** → Extensive testing, paper trading mandatory
- **Fat finger** → Hard limits on order sizes
- **Account issues** → Keep backup funds, separate accounts

**Kill Criteria (Stop Trading Immediately If):**
- 10 consecutive losses
- Daily drawdown >20%
- Sharpe ratio drops <0.5
- API access revoked
- Market structure fundamentally changes

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-02T02:00Z  
**Status:** Phase 1 Active - Data Collection
