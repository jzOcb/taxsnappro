# BTC Arbitrage Bot - Research Findings Report

**Date**: 2026-02-02  
**Phase**: 1 - Market Research  
**Time spent**: ~15 minutes  
**Status**: ⚠️ MIXED RESULTS

---

## Executive Summary

✅ **Good news**: Kalshi has 15-minute BTC price prediction markets (KXBTC15M)  
⚠️ **Concerns**: Low liquidity ($687/market), large spread (3¢), API access issues  
🔬 **Next**: Need US-based server or API access to continue testing  

---

## Key Findings

### 1. Market Discovery ✅

**Kalshi KXBTC15M Series**:
- **Question**: "Will BTC price go up in the next 15 minutes?"
- **Frequency**: New market every 15 minutes
- **Current market**: KXBTC15M-26FEB012030-30
- **Pricing**: YES at 36¢ bid / 39¢ ask
- **Volume**: $687 (very low)
- **Closes**: 2026-02-02T01:30:00Z

**Alternative markets found**:
- KXETH15M: ETH 15-minute predictions (even lower volume: $235)
- BTCD: Daily BTC above/below (no active markets currently)
- KXBTC100: BTC hitting $100k (custom frequency, no active markets)

### 2. Polymarket Comparison

**Crypto markets on Polymarket**:
- MicroStrategy Bitcoin sales: $19.7M volume
- Trump crypto tax elimination: $89k volume
- MegaETH launch markets: $8.8M volume

**Problem**: These are long-term event markets, not suitable for short-term price arbitrage strategy.

**Conclusion**: Kalshi KXBTC15M is better suited for this strategy despite lower volume.

### 3. Liquidity Analysis ⚠️

| Platform | Market | Volume | Spread |
|----------|--------|--------|--------|
| Kalshi BTC | 15min price | $687 | 3¢ |
| Kalshi ETH | 15min price | $235 | 3¢ |
| Polymarket | MicroStrategy | $19.7M | ? |

**Concerns**:
1. $687 volume is very low for profitable trading
2. 3¢ spread eats into profit margins
3. Large orders would cause significant slippage

**Comparison**:
- Polymarket BTC events have 28x more volume
- But those are long-term events (weeks/months), not 15-minute windows

### 4. Strategy Viability

**Original plan** (from @xmayeth):
```
Binance BTC moves → Polymarket slow to update → Trade in delay window
```

**Adapted plan** (our finding):
```
Binance BTC moves → Kalshi KXBTC15M slow to update? → Trade in delay window
```

**Critical unknowns**:
1. ❓ Does Kalshi actually have a price update delay?
2. ❓ How correlated is KXBTC15M pricing with real BTC moves?
3. ❓ Can we execute fast enough given liquidity constraints?

### 5. Technical Blockers 🚨

**API Access Issue**:
- Kalshi API returns HTTP 451 (Unavailable For Legal Reasons)
- Likely geographic restriction
- Blocks our ability to:
  - Measure real delay
  - Test trading API
  - Build automated system

**Current workarounds**:
1. Need US-based server or VPN
2. Manual observation via Kalshi website
3. Use public/archived data if available

**What we CAN test now**:
- ✅ Binance price monitoring (no restrictions)
- ✅ Price movement detection logic
- ❌ Kalshi API integration (blocked)
- ❌ End-to-end arbitrage testing (blocked)

---

## Profit Calculation (Theoretical)

**Assumptions**:
- Delay window: 5 seconds (unknown, need to measure)
- Position size: $100
- Spread cost: 3¢ ($3 on $100 position)
- Win rate: 60% (typical for arbitrage)

**Best case scenario**:
```
Entry: YES @ 39¢
Correct prediction: Market settles YES
Profit: $100 * (1 - 0.39) = $61
Minus spread: $61 - $3 = $58
ROI: 58%
```

**Average case** (60% win rate):
```
Wins (60%): $58 * 0.6 = $34.80
Losses (40%): -$39 * 0.4 = -$15.60
Net: $19.20 per trade
ROI: 19.2%
```

**Problem**: With only $687 liquidity, we can only do 6-7 trades per 15-min window before moving the market.

---

## Go / No-Go Decision Factors

### ✅ GO Signals
1. Market exists and is specific to our strategy
2. Clear binary outcome (price up/down)
3. High frequency (every 15 minutes = 96 opportunities/day)
4. Binance monitoring is straightforward

### ⚠️ YELLOW Flags
1. Low liquidity limits position size
2. Large spread reduces profit margin
3. Need to verify delay actually exists
4. API access restrictions

### 🛑 NO-GO Signals
1. If no measurable delay exists (Kalshi already tracks Binance real-time)
2. If API access can't be resolved
3. If liquidity doesn't improve
4. If correlation is weak

---

## Recommended Next Steps

### Immediate (Can do now)
1. ✅ Build Binance WebSocket monitor (in progress)
2. ✅ Document findings for decision
3. ⏳ Test from US-based server or with VPN

### Short-term (This week)
1. Get US server access or resolve API blocks
2. Measure actual delay (Binance → Kalshi)
3. Backtest correlation (BTC moves vs KXBTC15M outcomes)
4. Test Kalshi trading API

### Medium-term (If GO)
1. Build automated monitoring system
2. Implement risk management
3. Paper trade for 1 week
4. Evaluate profitability

---

## Alternative Strategies to Consider

If KXBTC15M doesn't work out:

1. **Higher liquidity Polymarket events**
   - Focus on high-volume crypto events
   - Longer timeframes but better execution

2. **Different assets**
   - ETH, SOL if they have better Kalshi markets
   - Stock index futures during market hours

3. **Different arbitrage angles**
   - Cross-exchange arbitrage (Kalshi vs Polymarket on same events)
   - Statistical arbitrage (market inefficiencies)

4. **Back to original Kalshi Trading System**
   - Focus on official data-driven trades
   - Lower frequency but higher conviction

---

## Files Created

```
btc-arbitrage/
├── README.md - Project overview
├── RESEARCH.md - Detailed research plan
├── STATUS.md - Live status tracking
├── FINDINGS.md - This report
├── scripts/
│   ├── search_markets.py - Market discovery
│   ├── analyze_kalshi_crypto.py - Deep dive on crypto markets
│   ├── get_btc_markets.py - KXBTC15M details
│   └── measure_delay.py - Delay measurement (blocked by API)
├── src/
│   └── binance_monitor.py - Price monitoring framework
└── data/
    └── delay_measurement.json (empty due to API block)
```

---

## Conclusion

**TL;DR**: Kalshi KXBTC15M markets exist and match our strategy, BUT we hit API access issues and liquidity concerns. Need to resolve API access first before making final Go/No-Go decision.

**Recommendation**: 
1. Resolve API access (US server or Kalshi support)
2. Measure real delay in production environment
3. If delay >3 seconds: GO (build prototype)
4. If delay <1 second or no delay: NO-GO (pivot to other strategies)

**Risk level**: 🟡 MEDIUM - Viable but needs validation

**Next review**: After API access is resolved
