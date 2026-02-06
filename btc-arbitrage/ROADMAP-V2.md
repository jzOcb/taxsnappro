# Trading System Roadmap V2
**Created: 2026-02-05**
**Based on: Community research + platform data scan**

## Architecture Vision

```
                    ┌─────────────────────┐
                    │   Fair Value Engine  │
                    │ (spot/options/model) │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼──────┐  ┌─────▼──────┐  ┌──────▼──────┐
     │  Crypto Module │  │ Sports Mod │  │ Mention Mod │
     │  BTC/ETH/SOL  │  │  NBA/NFL   │  │ Trump/Events│
     └────────┬──────┘  └─────┬──────┘  └──────┬──────┘
              │                │                │
     ┌────────▼────────────────▼────────────────▼──────┐
     │            Cross-Platform Arb Scanner            │
     │         (Kalshi ↔ Polymarket ↔ Sportsbooks)     │
     └────────────────────────┬────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Execution Engine  │
                    │  (MAKER ORDERS ONLY)│
                    └───────────────────┘
```

## Phase 1: Foundation (Feb 5-7) — Fair Value + Maker Simulation

### 1A. Fair Value Pricing Engine
**Goal**: Calculate theoretical Kalshi bracket price from spot + volatility
**Why**: Stop guessing direction → only trade when market price ≠ fair value
**Implementation**:
- Input: spot price, historical vol (ATR), time to settlement
- Model: Black-Scholes-like for binary options P(S > K at T)
- Output: fair_value_yes, edge = market_price - fair_value
- Entry rule: |edge| > threshold (e.g., 5¢) → trade the mispriced side

### 1B. Maker Order Simulation
**Goal**: Paper trading must simulate maker fills, not instant taker fills
**Why**: Research shows maker fee (0.3%) vs taker (1.2%) is life/death
**Implementation**:
- Limit order placed at best bid/ask
- Fill only when price crosses your limit (not instant)
- Track queue position, fill rate, time-to-fill
- Calculate actual P&L with maker fees (0.3%)

### 1C. Upgrade V14
**Goal**: Integrate fair value engine + maker simulation into V14
**V14 already has**: probability scoring, EV gating
**Add**: fair value model, maker-only execution, edge-based entry

**Deliverable**: V15 = V14 + fair_value + maker_sim

---

## Phase 2: Cross-Platform Scanner (Feb 7-10)

### 2A. Contract Matcher
**Goal**: Auto-match Kalshi ↔ Polymarket events
**Implementation**:
- Scan both APIs for overlapping events (BTC daily, politics, sports)
- Normalize strike prices, resolution times, settlement rules
- Flag when same-event prices diverge > fees
- Handle resolution time differences (PM noon vs Kalshi 5pm for crypto)

### 2B. Cross-Platform Arb Bot
**Goal**: When matched events have price gap > fees → signal both legs
**Targets** (by overlap + volume):
- ✅ BTC/ETH daily (already have data feeds!)
- ✅ Fed rate decisions (Kalshi KXFED + PM Fed events)
- ✅ CPI/GDP (Kalshi KXCPI/KXGDP + PM equivalents)
- 🔜 NBA games (Kalshi KXNBA 3.8M vol + PM NBA events)

### 2C. PM → Kalshi Lead Signal (V13 Evolution)
**Goal**: Extend V13's pm_lead to ALL matching markets, not just crypto
**PM has higher volume** → prices move first → trade Kalshi lag

**Deliverable**: cross_platform_scanner.py + arb signals

---

## Phase 3: Sports Module (Feb 10-14)

### 3A. NBA In-Game Bot
**Goal**: Trade Kalshi NBA markets using live game data
**Why**: 3.8M volume on Kalshi, massive PM overlap, proven strategies exist
**Strategies** (from @HesomParhizkar's research):
- homeUnderdog: Home teams at 30-35¢ (46.2% WR, breakeven 35%)
- favoriteFade: Favorites >75% with spread -10 to -14
- lateGameLeader: Buy team with big lead in 4th quarter
**Data source**: ESPN API (free, real-time scores)
**Cross-platform**: Kalshi vs PM live odds arb

### 3B. Super Bowl Mention Markets (Feb 9 — URGENT if SB is this week)
**Goal**: Monitor Super Bowl related mention markets
**Note**: Mention markets appear when event is scheduled on Kalshi

**Deliverable**: sports_trader.py + espn_feed.py

---

## Phase 4: Mention Market Monitor (Feb 14+)

### 4A. Live Event Monitor
**Goal**: Track scheduled political events, parse context for mention prediction
**Implementation**:
- Monitor C-SPAN/WhiteHouse.gov schedule
- When event starts → activate mention market scanner
- Context anticipation (not word detection — bots win that race)

### 4B. Trump Speech Tracker
**Goal**: Polymarket "What will Trump say" markets are $2M+/week
**Implementation**: PM prices as sentiment → trade Kalshi mentions

**Deliverable**: mention_monitor.py

---

## Phase 5: Advanced (Feb 20+)

### 5A. Sportsbook Integration
- OddsJam API for sportsbook ↔ Kalshi price comparison
- Focus on markets where Kalshi has better odds than FanDuel/DraftKings

### 5B. Weather Markets (Seasonal)
- Build NWS data integration NOW, deploy when summer temp markets open
- NOAA API (free), multiple forecast model blending

### 5C. ML Signal Model
- Train on all our paper trading data
- Feature engineering from all data sources
- 4-6 week project

---

## Critical Rules (All Phases)

1. **MAKER ORDERS ONLY** — Never taker (0.3% vs 1.2% fee)
2. **FAIR VALUE FIRST** — Calculate what the contract should be worth before trading
3. **EV > 0 REQUIRED** — From V14's probability scorer
4. **CROSS-PLATFORM VALIDATION** — If PM and Kalshi disagree, figure out who's right
5. **A/B TEST EVERYTHING** — @predict_anon's iron rule, also ours

---

## Current State (Feb 5)

| Version | Status | Purpose |
|---------|--------|---------|
| V10 | ❌ Killed | Baseline (outperformed by V11) |
| V11 | ✅ Running (PID 268308) | Trend filter — best performer so far |
| V12 | ❌ Killed | Quant enhanced (ATR stops too tight) |
| V13 | ❌ Killed | PM lead signal (concept proven, merging into V15) |
| V14 | ✅ Running (PID 278970) | Probability + EV gating |
| V15 | 🔜 Next | V14 + fair value + maker sim |

## Key Metrics to Track

- **Edge per trade**: fair_value - market_price (should be >5¢ average)
- **Maker fill rate**: % of limit orders that actually fill
- **Cross-platform spread**: Average price gap on matched events
- **Win rate by strategy**: Track separately for each strategy+market combo
- **Fee-adjusted P&L**: The ONLY P&L that matters
