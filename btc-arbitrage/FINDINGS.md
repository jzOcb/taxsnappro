# BTC Arbitrage Research Findings

Last updated: 2026-02-02T01:48Z

## Market Structure Discovery ✅

### Kalshi KXBTC15M Markets

**Format**: `KXBTC15M-[DATE][TIME]-[SEQUENCE]`
- Example: `KXBTC15M-26FEB012100-00`
- Means: "Will BTC price go UP in the 15 mins ending at 2026-02-02 01:21:00 (9:00 PM EST Feb 1)?"

**Key Characteristics:**
1. **Binary market**: YES (price up) or NO (price down/flat)
2. **15-minute cycles**: New market opens every 15 minutes
3. **Resolution source**: CF Benchmarks BRTI (NOT Binance!)
4. **Settlement logic**:
   - Take average of 60 BRTI prices in last minute before close
   - Compare to average of 60 BRTI prices in last minute before open
   - If close_avg >= open_avg → YES wins
   - Otherwise → NO wins
5. **Fast settlement**: 60 seconds after close time

**Current Active Market (as of 01:48 UTC):**
```json
{
  "ticker": "KXBTC15M-26FEB012100-00",
  "title": "BTC price up in next 15 mins?",
  "open_time": "2026-02-02T01:45:00Z",
  "close_time": "2026-02-02T02:00:00Z",
  "yes_bid": 0.40,
  "yes_ask": 0.42,
  "no_bid": 0.58,
  "no_ask": 0.60,
  "volume": 987,
  "liquidity": "$10,759.28"
}
```

## Price Sources Hierarchy

### What We Discovered

The arbitrage is NOT:
```
Binance price → Kalshi updates with delay
```

It's actually:
```
Binance price → CF Benchmarks BRTI → Kalshi settlement
                 ↑
                 Unknown delay here!
```

### CF Benchmarks BRTI

**What it is:**
- "Bitcoin Real-Time Index" by CF Benchmarks
- Industry-standard BTC price reference
- Used by CME Bitcoin futures and other regulated markets
- Aggregates prices from multiple exchanges

**Resolution rules (from Kalshi):**
> "Not all cryptocurrency price data is the same. While checking a source like Google or Coinbase may help guide your decision, the price used to determine this market is based on CF Benchmarks' corresponding Real Time Index (RTI)."

**Critical question**: Can we access CF Benchmarks BRTI in real-time?
- ❓ Public API available?
- ❓ What exchanges feed into BRTI?
- ❓ Binance.US included in BRTI calculation?

## Delay Measurement Results

### Test #1: Binance.US vs Kalshi (30 seconds, 5s interval)

**Setup:**
- Duration: 30 seconds
- Interval: 5 seconds  
- Measurements: 6 samples
- Market: KXBTC15M-26FEB012100-00

**Results:**

| Time | Binance.US Price | Kalshi YES bid/ask | Kalshi Updated? |
|------|------------------|-------------------|-----------------|
| 01:45:39 | $77,706.54 | 0.41 / 0.44 | N/A |
| 01:45:44 | $77,706.54 | 0.41 / 0.44 | ❌ No change |
| 01:45:49 | $77,656.32 | 0.41 / 0.44 | ❌ No change ($50 drop ignored!) |
| 01:45:54 | $77,656.32 | 0.41 / 0.44 | ❌ No change |
| 01:45:59 | $77,656.32 | 0.41 / 0.44 | ❌ No change |
| 01:46:05 | $77,656.32 | 0.41 / 0.44 | ❌ No change |

**By 01:47 (checking market details):**
- Binance.US: $77,656.32 (still)
- Kalshi: YES 0.40 / 0.42 (SPREAD TIGHTENED)

**Observations:**
1. ✅ **Delay exists**: BTC dropped $50, Kalshi didn't react immediately
2. ✅ **Low volume during test**: Only 29 contracts (market just opened)
3. ⚠️ **Market DID update eventually**: Spread went from 3¢ to 2¢
4. ❓ **Update trigger unclear**: Was it CF Benchmarks or just new orders?

**API Latencies:**
- Binance.US: ~109ms average
- Kalshi: ~103ms average
- **Difference: Only 6ms** (APIs are equally fast)

## Revised Strategy Implications

### Original Assumption (WRONG)
"Binance price updates faster than Kalshi → trade before Kalshi updates"

### Actual Reality
Kalshi settlement is based on **CF Benchmarks BRTI**, not Binance directly.

### New Arbitrage Opportunities

**Option A: CF Benchmarks Delay Arbitrage** 
- Monitor Binance.US (or other BRTI constituents)
- Predict CF Benchmarks BRTI direction
- Trade on Kalshi before BRTI fully reflects movement
- **Blocker**: Need access to real-time BRTI data

**Option B: Market Maker Delay Arbitrage**
- Kalshi market prices are set by traders, not oracle
- If market is slow to update (low volume/activity)
- Fast BTC movement → stale Kalshi prices
- Trade before human market makers update their orders
- **Evidence**: We saw $50 drop with no immediate Kalshi update

**Option C: Logic Arbitrage** (from @w1nklerr research)
- Use Binance momentum/volatility to predict direction
- Kalshi market may misprice due to information lag
- Trade when we have better prediction than current odds
- **Advantage**: Doesn't require price arbitrage window

## Next Steps

### Immediate (This Session)
1. 🔄 **Research CF Benchmarks BRTI**
   - Is there a public API?
   - Which exchanges are included?
   - Can we track it in real-time?

2. 🔄 **Extended delay test**
   - Run 5-10 minute test
   - Capture market price updates
   - See if updates correlate with BRTI or trader activity

3. 🔄 **Volume analysis**
   - Track volume during different times
   - Higher volume = more efficient pricing
   - Lower volume = more arbitrage opportunities?

### This Week
- [ ] Compare Binance vs other BRTI exchanges (Coinbase, Kraken, etc.)
- [ ] Build BRTI proxy (aggregate Binance + Coinbase + Kraken)
- [ ] Test if our proxy predicts Kalshi settlement
- [ ] Decide which strategy to pursue

## Open Questions

1. **CF Benchmarks BRTI access**
   - Can we get real-time BRTI data? (Likely paid)
   - Can we build a good proxy using public exchange APIs?
   - How accurate would a proxy be?

2. **Kalshi pricing mechanism**
   - How often do market prices update?
   - Is it trader-driven or oracle-driven?
   - What's the typical lag during high volatility?

3. **Competition**
   - How many other bots are doing this?
   - What's the minimum viable edge?
   - Can we be fast enough with REST APIs?

4. **Settlement accuracy**
   - How often does Kalshi settle correctly?
   - Are there edge cases or delays in settlement?
   - What happens during exchange outages?

## Resources

- [CF Benchmarks](https://www.cfbenchmarks.com/)
- [CF Benchmarks BRTI Methodology](https://www.cfbenchmarks.com/indices/BRTI)
- [Kalshi KXBTC15M series](https://kalshi.com/markets/kxbtc15m)
- [Our delay measurement data](data/delay_measurement_binance_us_20260202_014610.json)

---

**Key Insight**: This is NOT simple price arbitrage. We need to understand CF Benchmarks BRTI to make this work.

**Decision Point**: Should we continue with delay arbitrage OR pivot to logic arbitrage?
