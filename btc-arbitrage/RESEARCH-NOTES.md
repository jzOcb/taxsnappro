# BTC Arbitrage Research Notes — Kalshi Prediction Markets

**Date:** 2026-02-02  
**Focus:** Strategies for Kalshi KXBTC15M markets, stop-loss optimization, K-value dynamics  
**Context:** Our v3 paper trader detects "K crashes" (rapid Kalshi orderbook mid-price drops) and buys YES expecting recovery, but gets repeatedly stopped out in volatile markets.

---

## Table of Contents
1. [Open-Source Implementations & Bots](#1-open-source-implementations--bots)
2. [Cross-Platform Arbitrage Strategies](#2-cross-platform-arbitrage-strategies)
3. [Market Microstructure Insights](#3-market-microstructure-insights)
4. [Mean-Reversion vs Momentum in Prediction Markets](#4-mean-reversion-vs-momentum-in-prediction-markets)
5. [Stop-Loss & Whipsaw Mitigation](#5-stop-loss--whipsaw-mitigation)
6. [Academic Research](#6-academic-research)
7. [Strategy Improvements for v3](#7-strategy-improvements-for-v3)

---

## 1. Open-Source Implementations & Bots

### A. Polymarket-Kalshi BTC Arbitrage Bot
**Source:** https://github.com/CarlosIbCu/polymarket-kalshi-btc-arbitrage-bot  
**Type:** Cross-platform arbitrage  
**Key Insights:**
- Exploits price differences between Polymarket's CLOB and Kalshi's API for **Bitcoin 1-Hour Price markets**
- Buys opposing positions (e.g., YES on Kalshi + DOWN on Polymarket) when combined cost < $1.00
- Mathematical guarantee: minimum payout is always $1.00 regardless of outcome
- **"Middle zone" bonus**: When BTC lands between the two strike prices, BOTH legs win → $2.00 payout
- Uses FastAPI backend + Next.js dashboard, fetches live prices every second
- **Arbitrage thesis:** When Poly Strike > Kalshi Strike → buy Poly DOWN + Kalshi YES; vice versa

**Relevance to our strategy:**
- ⚠️ This is TRUE arbitrage (risk-free) vs our speculative approach
- Key lesson: They handle different strike prices across platforms — we could look for mispriced strikes WITHIN Kalshi's 15-min markets
- Settlement risk is real: "Prices might change between buying leg 1 and leg 2"

### B. Kalshi Market-Making Bot (jacksonm810)
**Source:** https://github.com/jacksonl0810/Kalshi-Trading-Bot  
**Type:** Market-making bot for BTC/ETH/XRP markets  
**Key Insights:**
- **Probability-based pricing**: Calculates bid prices from probability estimations with configurable spreads
- **Sticky pricing**: Implements time-boxed sticky pricing to reduce order churn — if proposed price is within 1¢ of last price AND within 1s window → keep last price
- **Safety features:**
  - Trading window restrictions: Excludes first/last 30 seconds of each hour
  - Data freshness: Cancels orders if market data >2 seconds stale
  - Price limits: Enforces MIN_BID (1.5¢) and MAX_BID (95¢)
  - Rate limiting with configurable throttling
  - Cooldowns: `RECREATE_COOLDOWN_SEC = 20.0`, `AMEND_COOLDOWN_SEC = 0.5`
- **Architecture**: Async with separate polling loops for orders, positions, and estimations
- Uses RSA-PSS API authentication

**Relevance to our strategy:**
- ✅ **Excludes first/last 30 seconds** — we should too (high uncertainty periods)
- ✅ **Data freshness checks** — cancel/avoid trading on stale data
- ✅ **Sticky pricing concept** — don't react to tiny K changes

### C. Kalshi AI Trading Bot (adrian-pan)
**Source:** https://github.com/adrian-pan/Kalshi-Bot  
**Type:** Multi-strategy AI bot with web dashboard  
**Key Insights:**
- **Multiple strategies implemented:**
  1. **Mean Reversion**: Identifies extreme prices (>85% or <15%) → expects reversion
  2. **Momentum**: Detects strong price movements, follows trends
  3. **Category-Based**: Different confidence levels for different market types
- **Risk management:**
  - `max_position_size`: 10 contracts max
  - `max_total_exposure`: $100 max
  - `min_edge`: 5% minimum edge required to trade
  - `stop_loss_pct`: 50% stop loss threshold
  - Position limits, exposure limits, stop losses
- **Fair value calculation**: Pluggable — can use ML models, technical indicators, etc.
- Demo environment for testing: `https://demo-api.kalshi.co`

**Relevance to our strategy:**
- ✅ **Mean reversion at extremes** — only trade when K hits extreme values (>85¢ or <15¢), not moderate drops
- ✅ **50% stop loss** — much wider than our 12%, which explains why we get whipsawed
- ✅ **5% minimum edge** — we should require a minimum expected edge before entering

### D. Prediction Market Arbitrage Bot (realfishsam)
**Source:** https://dev.to/realfishsam/how-i-built-a-risk-free-arbitrage-bot-for-polymarket-kalshi-4f  
**Code:** https://github.com/realfishsam/prediction-market-arbitrage-bot  
**Key Insights:**
- Found consistent 2-5% price spread between Polymarket and Kalshi
- Uses `pmxt` — a unified wrapper (like CCXT but for prediction markets)
- **Rotation Strategy**: Doesn't hold until maturity — enters when spread widens, exits when spread closes OR when a better opportunity appears
- Captured spreads of 1.5-4.5% on high-volume events
- **Execution risk**: "Prices can move between your first and second API call"
- **Fill risk**: "Might get filled on Polymarket but stuck on Kalshi if volume dries up"

**Relevance to our strategy:**
- ✅ **Rotation strategy concept** — exit positions not just on profit/loss, but when a BETTER opportunity appears
- ✅ **Don't hold to maturity** — active management

### E. kalshi-py SDK
**Source:** https://apty.github.io/kalshi-py/examples/  
**Type:** Python SDK for Kalshi API  
**Key Features:**
- Async support for concurrent API calls
- Batch order operations (create/cancel multiple orders)
- Real-time orderbook data via `get_market_orderbook`
- Portfolio management (positions, fills, balance)

**Relevance:** Could replace our manual REST polling with proper SDK

---

## 2. Cross-Platform Arbitrage Strategies

### Polymarket vs Kalshi BTC Markets
**Source:** https://newyorkcityservers.com/blog/prediction-market-arbitrage-guide  
**Key Data Points:**
- $40M+ in arbitrage profits extracted from Polymarket (Apr 2024 - Apr 2025)
- Top 3 wallets earned $4.2M combined from 10,200+ bets
- Average arbitrage margin: 2-3%
- **Typical opportunity window: SECONDS (not minutes)**
- Same-market arbitrage on Polymarket: 0.5-2% returns, closing within 200ms
- **One trader earned $764 in a single day on Dec 21, 2025 using BTC-15m markets with $200 deposit**

### Fee Considerations
| Platform | Fee |
|----------|-----|
| Polymarket (US) | 0.01% trading fee |
| Polymarket (Intl) | 2% on net winnings |
| Kalshi | ~0.7% taker fee (up to 3%) |
| Polygon gas | ~$0.007/tx |

**Critical Insight:** Spreads under 5-6% rarely generate profit after fees on cross-platform trades. For same-platform (Kalshi only) strategies like ours, the fee impact is lower but still matters.

### Settlement Risk Warning
Different platforms may interpret events differently. In 2024 government shutdown case: Polymarket resolved "Yes" while Kalshi resolved "No" for the SAME event due to different settlement definitions. Always verify resolution criteria.

---

## 3. Market Microstructure Insights

### Kalshi K-Value Dynamics (Orderbook Mid)
Based on our observations and community research:

1. **K-value is trader-driven, NOT oracle-driven**: Kalshi prices come from the orderbook, not an automatic feed. Market makers post bids/asks; the "mid" is the midpoint.

2. **Market maker behavior**: From the jacksonm810 bot, market makers:
   - Use probability estimations to calculate fair value
   - Apply a spread (default 1¢ each side)
   - Use "sticky pricing" to avoid churn on small moves
   - **Exclude first/last 30 seconds of each 15-min window**
   - Cancel orders if data becomes stale (>2 seconds)

3. **K-value crash causes** (what triggers rapid drops):
   - **BTC price drop** → Market makers pull bids → YES bids collapse
   - **Large market sell** → Someone dumps YES contracts
   - **Market transition** → New 15-min window opens with fresh pricing
   - **Liquidity withdrawal** → Market makers go offline or widen spreads
   - **"Fake" crashes** → Thin book means small trades cause big price swings

4. **BTC spot → K-value relationship**:
   - NOT direct; mediated by CF Benchmarks BRTI
   - BRTI aggregates multiple exchanges (Coinbase, Kraken, Bitstamp, etc.)
   - Kalshi makers update THEIR prices based on their own BRTI estimates
   - Lag is typically 20-60 seconds for market maker order updates
   - During high volatility, lag increases as makers become more conservative

### Why K Crashes Don't Always Recover
**This is our core problem.** K crashes don't always recover because:

1. **The crash is informationally correct**: BTC actually dropped, BRTI is lower, YES probability genuinely decreased
2. **New equilibrium**: Market makers recalculated fair value at a lower level — this isn't a "crash" to recover from
3. **Volatility regime change**: High-vol means wider spreads and lower bids, which looks like a crash but is really spread expansion
4. **Market window effect**: Near end of 15-min window, pricing converges to binary (near 0 or near 100), making "recovery" structurally impossible

---

## 4. Mean-Reversion vs Momentum in Prediction Markets

### Mean-Reversion Approach
**When it works in prediction markets:**
- Extreme mis-pricing events (YES < 15¢ or > 85¢) that are clearly wrong
- Liquidity shocks (large seller → price drops but fundamentals unchanged)
- Spread expansion events (makers widen, mid drops, but true value hasn't changed)

**When it FAILS (our current problem):**
- In **trending markets** where BTC is persistently moving one direction
- During **volatility spikes** where the wider spread is CORRECT, not a mismatch
- Near **market close** (<2 min) where binary convergence makes recovery impossible
- When the "crash" reflects **real information** (BTC genuinely dropped)

### Momentum Approach
**When it works:**
- Strong BTC momentum persists for 5-15 minute windows
- Kalshi market makers lag behind real-time BTC movement by 20-60 seconds
- Technical indicators (ROC, RSI, MACD) provide >50% directional accuracy

**When it FAILS:**
- Sharp reversals after momentum signals
- Low liquidity makes entry/exit expensive
- Signal abundance but low conviction per trade

### Hybrid Approach (Recommended)
The best prediction market strategies **combine both**:
1. **Use momentum to determine DIRECTION** (should I buy YES or NO?)
2. **Use mean-reversion for TIMING** (is the current K-value oversold relative to direction?)
3. **Use volatility regime detection** to adjust stop-loss and position sizing

---

## 5. Stop-Loss & Whipsaw Mitigation

### Our Current Problem
- **v3 stop-loss**: -12% → too tight for volatile markets
- **v3 profit target**: +8% → reasonable but rarely hit before stop
- **v3 timeout**: 360 seconds (6 min) → too long, ties up capital in stale trades
- **Result**: Repeated stop-outs during normal volatility, especially in trending markets

### Community Approaches

**A. Wider stops + smaller position size** (adrian-pan bot)
- 50% stop loss with max $100 exposure
- Rationale: Binary markets are inherently volatile; tight stops = guaranteed losses
- Trade-off: Each loss is bigger, but fewer false stop-outs

**B. Time-based exits only** (jacksonm810 bot)
- Market makers don't use stop-losses — they use trading window restrictions
- Exit at end of 15-min window, regardless of P&L
- Rationale: In binary markets, you either win 100% or lose 100% at settlement; intermediate P&L is noise

**C. Volatility-adjusted stops**
- Measure recent K-value volatility (std dev of last N readings)
- Set stop at 2-3x recent volatility
- During high-vol: wider stops (maybe 25-30%)
- During low-vol: tighter stops (maybe 8-10%)

**D. No stop-loss on mean-reversion trades**
- If you believe in the mean-reversion thesis, a further drop is a BETTER entry, not a reason to exit
- Instead: use max-loss limit per trade (e.g., risk at most $X on this position)
- Exit only at: profit target, timeout, or settlement

### Reducing False Crash Signals

**Key insight from research**: Most "K crashes" in volatile markets are NOT recoverable events — they're **information updates**. Our strategy needs to DISTINGUISH between:

1. **Liquidity crashes** (recoverable): Caused by one large seller, thin book; BTC hasn't moved much
   - Signal: K drops sharply BUT BTC price stable or rising
   - Action: BUY YES (mean-reversion play)

2. **Information crashes** (NOT recoverable): Caused by BTC actually dropping
   - Signal: K drops AND BTC price is also dropping
   - Action: DO NOT BUY (or buy NO for momentum play)

3. **Spread expansion** (sometimes recoverable): Makers widen spreads during uncertainty
   - Signal: K mid drops but spread widens significantly; BTC stable
   - Action: Wait for spread to narrow, then enter if still mis-priced

---

## 6. Academic Research

### "Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets"
**Source:** https://arxiv.org/abs/2508.03474  
**Published:** August 2025  
**Authors:** IMDEA Networks Institute  
**Key Findings:**
- Analyzed 86 million bets across 7,000+ markets on Polymarket
- Two forms of arbitrage:
  1. **Market Rebalancing**: Within single market (YES + NO < $1.00)
  2. **Combinatorial**: Across related markets (logical dependencies)
- $40M realized profit extracted
- Political markets: largest spreads; Sports: most frequent opportunities
- **Key quote**: "Prediction markets can deviate significantly from probabilistic consistency, even in markets with substantial trading activity"

### "How to Use Kalshi to Change Risk Profile of Bitcoin"
**Source:** https://ferraijv.github.io/posts/data/prediction%20markets/cryptocurrency/2024/05/17/changing-bitcoin-risk-profile.html  
**Key Insight:**
- Uses Kalshi NO contracts as hedges against BTC holdings
- Example: Buy $100 BTC + 100 "No" contracts at $0.43 each → positive expected value under most scenarios
- **Relevant concept**: Instead of pure speculation, we could use Kalshi contracts to create **structured payoffs** — e.g., buy YES + partial hedge with NO on a related strike

### Key Academic References
- Jegadeesh & Titman (1993). "Returns to Buying Winners and Selling Losers" — momentum trading foundation
- Wolfers & Zitzewitz (2004). "Prediction Markets" — theoretical basis for prediction market efficiency
- SSRN: "Price Discovery and Trading in Prediction Markets" — documents Polymarket→Kalshi price discovery lag during 2024 election

---

## 7. Strategy Improvements for v3

### Priority 1: Fix False Crash Detection (CRITICAL)

**Current logic (broken):**
```python
if kalshi_drop < -25%:  # K crashed
    buy YES  # expect recovery
```

**Improved logic:**
```python
# ONLY buy crash if BTC is STABLE or RISING
btc_momentum = feed.get_momentum(60)  # 1-min BTC momentum
kalshi_drop = (new_bid - old_bid) / old_bid * 100

if kalshi_drop < -25:
    if btc_momentum > -0.05:  # BTC stable or up
        # TRUE liquidity crash — RECOVERABLE
        buy YES
    elif btc_momentum < -0.15:  # BTC also crashing
        # Information crash — DO NOT BUY YES
        # Optionally: buy NO (momentum play)
        pass
    else:
        # Ambiguous — skip
        pass
```

### Priority 2: Volatility-Adaptive Stop-Loss

**Current:** Fixed -12% stop → gets whipsawed in volatile markets

**Improved:**
```python
# Calculate recent K-value volatility
k_readings = [h['yes_bid'] for h in poller.history[-20:]]
k_std = np.std(k_readings) if len(k_readings) > 5 else 0.03

# Adaptive stop-loss
vol_multiplier = 2.5
adaptive_stop = max(0.08, min(0.30, k_std * vol_multiplier / entry_price))

# During high vol: wider stop (up to 30%)
# During low vol: tighter stop (down to 8%)
```

### Priority 3: Entry Quality Filters

Add these filters BEFORE entering any trade:

1. **Minimum time remaining**: >5 minutes (avoid end-of-window binary convergence)
2. **Spread filter**: Spread < 5¢ (wide spreads = expensive to enter/exit)
3. **Volume filter**: Market volume > 50 contracts (avoid illiquid markets)
4. **Momentum alignment**: Don't buy YES against BTC downtrend
5. **Cooldown**: No entry within 60 seconds of last exit (avoid chasing)

```python
def should_enter(market, feed, last_exit_time):
    close_time = parse_close_time(market['close_time'])
    time_remaining = close_time - time.time()
    
    if time_remaining < 300:  # <5 min
        return False, "too close to settlement"
    
    spread = market['yes_ask'] - market['yes_bid']
    if spread > 0.05:
        return False, "spread too wide"
    
    if market['volume'] < 50:
        return False, "volume too low"
    
    if time.time() - last_exit_time < 60:
        return False, "cooldown period"
    
    return True, "passed filters"
```

### Priority 4: Dual-Signal Strategy (Momentum + Mean-Reversion)

Instead of pure mean-reversion (crash → buy), use a hybrid:

```python
# MOMENTUM mode: When BTC has clear direction
if abs(btc_momentum_5m) > 0.20:  # Strong 5-min momentum
    if btc_momentum_5m > 0.20 and k_value < fair_value - 0.05:
        # BTC going up, but K underpriced → BUY YES (momentum + value)
        enter('YES', confidence='high')
    elif btc_momentum_5m < -0.20 and k_value > fair_value + 0.05:
        # BTC going down, but K overpriced → BUY NO (momentum + value)
        enter('NO', confidence='high')

# MEAN-REVERSION mode: When BTC is stable but K mispriced
elif abs(btc_momentum_5m) < 0.05:  # BTC sideways
    if k_crash_detected and k_value < 0.35:
        # K crashed but BTC stable → liquidity crash → BUY YES
        enter('YES', confidence='medium')
```

### Priority 5: Better Fair Value Estimation

Instead of just looking at K drops, estimate what K SHOULD be:

```python
def estimate_fair_value(brti_price, open_price, time_remaining, volatility):
    """
    Estimate fair value of YES contract based on:
    - Current BRTI vs open BRTI (direction)
    - Time remaining (more time = more uncertainty = closer to 50%)
    - Volatility (higher vol = closer to 50%)
    """
    direction = (brti_price - open_price) / open_price
    
    # Simple model: probability of YES based on current direction + time
    if time_remaining > 600:  # >10 min remaining
        fair = 0.50 + direction * 100  # Slight tilt based on current direction
    else:
        # Closer to settlement, more binary
        fair = 0.50 + direction * 200 * (1 - time_remaining/900)
    
    # Clamp to [0.05, 0.95]
    fair = max(0.05, min(0.95, fair))
    
    return fair
```

### Priority 6: Position Sizing by Confidence

```python
# Instead of fixed $10 per trade:
def get_trade_size(confidence, balance, max_risk_pct=0.02):
    sizes = {'high': 1.0, 'medium': 0.5, 'low': 0.25}
    multiplier = sizes.get(confidence, 0.25)
    max_trade = balance * max_risk_pct
    return max_trade * multiplier
```

---

## Summary of Key Lessons

| Finding | Source | Implication |
|---------|--------|-------------|
| K crashes during BTC drops are NOT recoverable | Our own data + logic | Filter crash signals by BTC momentum |
| Market makers exclude first/last 30s of window | jacksonm810 bot | Don't trade in these periods |
| 50% stop loss is standard for binary markets | adrian-pan bot | Our 12% stop is WAY too tight |
| Mean-reversion only works at extremes (<15¢ or >85¢) | adrian-pan bot | Don't try to catch moderate drops |
| Arbitrage opportunities last seconds, not minutes | $40M study | Speed matters; REST polling may be too slow |
| Cross-platform arb has 2-5% margins | realfishsam | Same-platform speculative edge needs to be >5% |
| Sticky pricing reduces false signals | jacksonm810 bot | Implement minimum K change threshold |
| One trader made $764/day on BTC-15m with $200 | newyorkcityservers | This IS viable with the right approach |
| BRTI is the settlement source, not Binance | Our FINDINGS.md | Must track BRTI, not individual exchanges |

---

## Next Steps

1. **Immediate**: Implement BTC momentum filter for crash detection (Priority 1)
2. **Today**: Add volatility-adaptive stop-loss (Priority 2)
3. **This week**: Build fair value estimator and dual-signal strategy (Priority 4-5)
4. **Consider**: Cross-platform arbitrage with Polymarket as separate strategy
5. **Investigate**: Kalshi WebSocket API for faster K-value updates (vs 5s REST polling)
6. **Research**: CF Benchmarks BRTI real-time access (paid?) for better fair value

---

## Sources

| # | URL | Type |
|---|-----|------|
| 1 | https://github.com/CarlosIbCu/polymarket-kalshi-btc-arbitrage-bot | Cross-platform arb bot |
| 2 | https://github.com/jacksonl0810/Kalshi-Trading-Bot | Market-making bot |
| 3 | https://github.com/adrian-pan/Kalshi-Bot | AI trading bot |
| 4 | https://dev.to/realfishsam/how-i-built-a-risk-free-arbitrage-bot-for-polymarket-kalshi-4f | Arb bot tutorial |
| 5 | https://github.com/realfishsam/prediction-market-arbitrage-bot | Arb bot code |
| 6 | https://newyorkcityservers.com/blog/prediction-market-arbitrage-guide | $40M arb guide |
| 7 | https://www.polytrackhq.app/blog/polymarket-arbitrage-bot-guide | Bot building guide |
| 8 | https://arxiv.org/abs/2508.03474 | Academic: Polymarket arbitrage |
| 9 | https://ferraijv.github.io/posts/data/prediction%20markets/cryptocurrency/2024/05/17/changing-bitcoin-risk-profile.html | BTC risk hedging with Kalshi |
| 10 | https://polynoob.com/arbitrage-on-prediction-market/ | Prediction market arbitrage overview |
| 11 | https://apty.github.io/kalshi-py/examples/ | kalshi-py SDK examples |
| 12 | https://docs.kalshi.com/ | Official Kalshi API docs |
| 13 | https://raw.githubusercontent.com/CarlosIbCu/polymarket-kalshi-btc-arbitrage-bot/main/thesis.md | Arbitrage thesis |
