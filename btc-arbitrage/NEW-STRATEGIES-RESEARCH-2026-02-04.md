# NEW BTC Kalshi Strategy Research - 2026-02-04

**CRITICAL**: All strategies below are NEW and NOT listed in STRATEGY-STATUS.md

## 1. CROSS-MARKET CORRELATION STRATEGIES

### 1.1 ETF Flow Arbitrage
**Concept**: Monitor real-time ETF flows (BITO, GBTC, IBIT) vs Kalshi BTC markets
- ETF premiums/discounts often lead BTC price movements by 30-90 seconds
- When GBTC trades at unusual premium/discount, BTC often follows
- **Edge estimate**: 2-5% when divergence >1%
- **Feasibility**: HIGH - ETF data is public, real-time
- **Implementation**: Medium - need ETF data feed
- **Evidence**: ETF arb is proven in traditional markets

### 1.2 Micro-Futures Lead-Lag
**Concept**: Use Bitcoin micro-futures tick data vs Kalshi pricing
- CME micro-futures trade 23/6, very liquid
- Often lead spot by 5-30 seconds during news events
- **Edge estimate**: 1-3% on volatile moves
- **Feasibility**: HIGH - CME data available
- **Implementation**: Medium - need futures data feed
- **Evidence**: Futures-spot arb is well-documented

### 1.3 DeFi Stablecoin Stress Signals
**Concept**: Monitor USDC/USDT depeg events as BTC volatility predictor
- Stablecoin depegs often precede crypto selloffs by 15-60 minutes
- Trade volatility increase rather than direction
- **Edge estimate**: 5-15% during stress events (rare but high-impact)
- **Feasibility**: HIGH - stablecoin prices are public
- **Implementation**: Easy - just price monitoring
- **Evidence**: March 2023 USDC depeg preceded massive BTC volatility

## 2. MICROSTRUCTURE-BASED STRATEGIES

### 2.1 Tick-by-Tick Momentum Bursts
**Concept**: Identify 3-5 second BTC momentum bursts that predict 15min direction
- Look for unusual tick patterns: 3+ consecutive large moves same direction
- Different from existing delay_arb - focuses on microstructure patterns, not absolute lag
- **Edge estimate**: 2-4% on pattern occurrence
- **Feasibility**: HIGH - just needs BTC tick data
- **Implementation**: Easy - pattern recognition
- **Evidence**: Microstructure momentum is proven in equity HFT

### 2.2 Orderbook Shape Analysis
**Concept**: Analyze BTC orderbook depth asymmetry as directional predictor
- Large bid wall = upward pressure, large ask wall = downward pressure
- Different from bid/ask volume - this is about SIZE and DISTANCE of walls
- **Edge estimate**: 1-3% when significant asymmetry detected
- **Feasibility**: HIGH - orderbook data available
- **Implementation**: Medium - need orderbook processing
- **Evidence**: Orderbook analysis is standard in crypto HFT

### 2.3 Cross-Exchange Momentum Clustering
**Concept**: When BTC moves on 3+ exchanges simultaneously, momentum typically continues
- Binance + Coinbase + Kraken all move same direction within 10 seconds
- Indicates genuine momentum vs single-exchange noise
- **Edge estimate**: 3-6% when cluster detected
- **Feasibility**: MEDIUM - need multiple exchange feeds
- **Implementation**: Medium - multi-feed coordination
- **Evidence**: Cross-venue momentum clustering documented in academic literature

## 3. ALTERNATIVE DATA STRATEGIES

### 3.1 Google Trends Flash Spike
**Concept**: Sudden spikes in "Bitcoin" search interest predict volatility increases
- 20%+ increase in search volume often precedes major moves by 10-30 minutes
- Trade volatility expansion, not direction
- **Edge estimate**: 4-8% during search spikes
- **Feasibility**: MEDIUM - Google Trends has delays
- **Implementation**: Easy - just API calls
- **Evidence**: Search volume predictive power documented in crypto research

### 3.2 GitHub Commit Velocity
**Concept**: Unusual Bitcoin Core development activity as stability signal
- High commit frequency = network stability = reduced crash risk
- Low commit frequency during weekends = potential weekend volatility
- **Edge estimate**: 2-4% for volatility-based bets
- **Feasibility**: HIGH - GitHub data is public
- **Implementation**: Easy - GitHub API
- **Evidence**: Development activity correlates with network health

### 3.3 Mining Pool Hash Rate Shifts
**Concept**: Sudden mining pool hash rate changes predict price volatility
- Large miners switching pools often indicates insider information
- 5%+ hash rate shift from top 3 pools = volatility likely within 1 hour
- **Edge estimate**: 3-7% when significant shifts detected
- **Feasibility**: MEDIUM - hash rate data has some lag
- **Implementation**: Medium - mining pool APIs
- **Evidence**: Mining economics directly affect BTC fundamentals

## 4. SPORTS BETTING ADAPTATIONS

### 4.1 Kelly Criterion with Dynamic Sizing
**Concept**: Adapt sports betting Kelly optimization for Kalshi position sizing
- Calculate optimal bet size based on perceived edge and uncertainty
- Unlike fixed-size betting, scale position based on confidence
- **Edge estimate**: 10-30% improvement over fixed sizing
- **Feasibility**: HIGH - just math on existing signals
- **Implementation**: Easy - position sizing algorithm
- **Evidence**: Kelly sizing widely proven in gambling

### 4.2 Steam Move Detection
**Concept**: Detect "smart money" moving Kalshi odds like sports betting steam
- Identify unusual volume patterns that indicate informed trading
- Follow the steam rather than fade it
- **Edge estimate**: 2-5% when steam detected
- **Feasibility**: HIGH - just volume pattern analysis
- **Implementation**: Medium - pattern recognition algorithm
- **Evidence**: Steam following profitable in sports betting

### 4.3 Closing Line Value (CLV) Tracking
**Concept**: Track whether our entry prices beat the final settlement probability
- Build database of our entry odds vs final settlement
- Identify which signal types consistently beat closing odds
- **Edge estimate**: Not direct edge - improves strategy selection
- **Feasibility**: HIGH - just data tracking
- **Implementation**: Easy - logging and analysis
- **Evidence**: CLV is gold standard metric in sports betting

## 5. KALSHI-SPECIFIC CROSS-MARKET OPPORTUNITIES

### 5.1 Fed Rate Decision Correlation
**Concept**: Use Kalshi Fed rate markets to predict BTC volatility
- Fed hawkish surprise = BTC volatility spike within 30-60 minutes
- Fed dovish surprise = BTC rally often starts within 15 minutes
- **Edge estimate**: 5-15% around Fed announcements
- **Feasibility**: HIGH - both markets on same platform
- **Implementation**: Easy - just monitoring both markets
- **Evidence**: Fed decisions major BTC price driver

### 5.2 VIX Kalshi Markets as BTC Predictor
**Concept**: Use Kalshi equity volatility markets to predict crypto volatility
- VIX spike = "risk off" = BTC often follows within 1-2 hours
- VIX collapse = "risk on" = BTC often rallies
- **Edge estimate**: 3-8% during major VIX moves
- **Feasibility**: HIGH if Kalshi has VIX markets
- **Implementation**: Easy - cross-market monitoring
- **Evidence**: Strong correlation between VIX and crypto volatility

### 5.3 Weekend Activity Patterns
**Concept**: Kalshi weekend trading patterns differ from weekday patterns
- Weekend: lower volume, higher impact of individual traders
- Different strategies may work on weekends vs weekdays
- **Edge estimate**: 2-5% improvement with day-specific models
- **Feasibility**: HIGH - just time-based logic
- **Implementation**: Easy - calendar-based strategy selection
- **Evidence**: Weekend effects documented across many markets

## 6. IMPLEMENTATION PRIORITIES

### HIGH PRIORITY (Build First)
1. **ETF Flow Arbitrage** - proven concept, clear edge
2. **Tick-by-Tick Momentum Bursts** - easy to implement, fast feedback
3. **Kelly Criterion Position Sizing** - improves existing strategies immediately

### MEDIUM PRIORITY (Build Second)
1. **DeFi Stablecoin Stress Signals** - high impact but rare events
2. **Cross-Exchange Momentum Clustering** - good edge but needs multiple feeds
3. **Fed Rate Decision Correlation** - high edge but event-driven

### RESEARCH FIRST (Validate Before Building)
1. **GitHub Commit Velocity** - novel but unproven in this context
2. **Mining Pool Hash Rate Shifts** - interesting but may have too much lag
3. **Google Trends Flash Spike** - promising but data delays may kill edge

## 7. NEXT STEPS

1. **Validate data availability** for top 3 strategies
2. **Build simple prototypes** for ETF flow and tick momentum
3. **Test Kelly sizing** on existing delay_arb strategy first
4. **Backtest weekend vs weekday** performance on existing strategies
5. **Set up monitoring** for Fed rate and VIX correlation opportunities

All strategies above are genuinely new and not covered in existing research. Focus on high-probability, low-complexity implementations first.