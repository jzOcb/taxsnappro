# ANALYSIS.md — BTC Arbitrage Data Analysis
Last updated: 2026-02-02T15:40Z

## 📊 Data Summary

**Collection Period:** 2026-02-02 02:44 UTC → 15:34 UTC (~12.9 hours)
**Primary Dataset:** `collection_20260202_024420.jsonl` — 1,518 data points
**Supplementary:** 2x continuous monitors (~480 min each), 2x paper trade sessions, overnight trackers
**Settlement Tracker:** Still running (PID 54477), 1 settlement recorded so far

---

## 1. BRTI Proxy Accuracy

### Price Tracking
| Metric | Value |
|--------|-------|
| BRTI Proxy Range | $74,571 — $78,865 |
| BRTI Proxy Average | $76,918 |
| Avg Tick-to-Tick Change | 0.051% |
| Max Single-Tick Up | +0.698% |
| Max Single-Tick Down | -0.319% |

### Direction Agreement (BRTI Proxy vs Kalshi Price Movement)
| Metric | Value |
|--------|-------|
| **Mean Agreement** | **73.0%** |
| Median Agreement | 71.8% |
| Best Market | 93.3% |
| Worst Market | 45.0% |
| Markets Analyzed | 52 of 53 |

### Settlement Validation
Only 1 settlement captured so far:
- **Market:** KXBTC15M-26FEB020300-00 (close: 08:00 UTC)
- **Result:** YES
- **BRTI Proxy at check:** $76,622.53
- **Volume:** 26,604 contracts

**Assessment:** 73% direction agreement is **below the 95% accuracy target**. The BRTI proxy tracks general direction but is NOT precise enough for confident settlement prediction. Missing: CF Benchmarks exact methodology, likely different weighting, more exchanges, volume-weighted calculation.

---

## 2. Arbitrage Window Analysis

### Window Detection (BRTI moved >0.05% while Kalshi stayed static)
| Metric | Value |
|--------|-------|
| **Total Windows** | **55** |
| **Windows per Hour** | **4.3** |
| Avg Duration | 40 seconds (1.3 ticks) |
| Longest Window | 180 seconds |

### Signal Detection (from continuous monitors)
| Source | Signals | Duration |
|--------|---------|----------|
| continuous_105014 | 8 WINDOW signals | 480 min |
| continuous_110118 | 5 WINDOW signals | 480 min |
| **Total unique** | **~10** | **960 min** |

### Signal Characteristics
Most signals occur near market close (last 1-2 minutes of 15-min window) when Kalshi prices are pinned at extremes:
- bid=0.99/ask=1.00 (outcome ~certain YES)
- bid=0.02/ask=0.05 (outcome ~certain NO)

These are **NOT tradeable** — the market has already priced in the outcome. No edge remains.

**Assessment:** 4.3 windows/hour meets the >5/day target but NOT the >5/hour ideal. Most "windows" are too brief (40s avg) and occur at extremes where spreads make entry unprofitable.

---

## 3. Kalshi Market Microstructure

### Bid-Ask Spread Distribution
| Spread | Frequency |
|--------|-----------|
| ≤ $0.01 | 4.8% |
| ≤ $0.02 | 30.5% |
| ≤ $0.03 | 53.2% |
| ≤ $0.05 | 85.8% |
| ≤ $0.10 | 95.3% |

| Stat | Value |
|------|-------|
| Mean Spread | $0.038 |
| Median Spread | $0.030 |
| Max Spread | $0.980 |

### Volume
| Stat | Value |
|------|-------|
| Mean Volume/Market | 10,910 contracts |
| Median Volume/Market | 8,822 contracts |
| Max Volume | 51,357 contracts |

**Assessment:** Median spread of $0.03 = 3% friction on a $1 contract. You need the market to move >3¢ in your favor just to break even. Significant friction.

---

## 4. Paper Trading Results

### Session 1 (paper_trade_20260202_105013.json)
| Metric | Value |
|--------|-------|
| Duration | 480 min (8 hours) |
| Trades | 2 |
| Win Rate | 50% (1W/1L) |
| Total PnL | $0.00 |
| Best Trade | +$0.10 |
| Worst Trade | -$0.10 |

### Session 2 (paper_trade_20260202_110119.json)
| Metric | Value |
|--------|-------|
| Duration | 480 min (8 hours) |
| Trades | 1 |
| Win Rate | 100% (1W/0L) |
| Total PnL | +$0.10 |

### Combined Paper Trading
| Metric | Value |
|--------|-------|
| **Total Trades** | **3** |
| **Win Rate** | **67%** (2W/1L) |
| **Total PnL** | **+$0.10** |
| **Avg PnL/Trade** | **$0.033** |
| **Annualized ROI** | **~0.2%** |

**Assessment:** Only 3 trades in 16 hours = extremely low signal frequency. PnL essentially flat ($0.10 on $1000 = 0.01% ROI). Not viable at current parameters.

---

## 5. Key Findings

### 🔴 Critical Issues

1. **BRTI Proxy insufficient (73% ≠ 95% target)**
   - Missing CF Benchmarks exact methodology
   - Equal weighting (33/33/34) likely wrong
   - Missing exchanges (Bitstamp, possibly others)
   - Volume-weighted vs equal-weighted makes a difference

2. **Tradeable signals are rare (3 trades in 16 hours)**
   - Most "windows" at market extremes (untradeable)
   - By the time BRTI moves enough, Kalshi already adjusted
   - 20-30s polling interval too slow for fleeting opportunities

3. **Spread eats profits**
   - $0.03 median spread = 3% friction on a $1 contract
   - Winners barely cover spread costs

4. **15-minute markets too fast**
   - Price discovery happens quickly within each window
   - Last 2-3 minutes are "decided" — extreme bid/ask

### 🟡 Mixed Signals

1. Direction agreement at 73% is non-trivial (better than random 50%)
2. Exchange spread tight (0.07%) — proxy inputs are good quality
3. Volume decent (10K+ avg) — liquidity exists
4. 4.3 windows/hour — opportunities exist, just hard to capture

### 🟢 Positive

1. Infrastructure fully functional — all pipelines working
2. BTC volatility during collection ($74.5K–$78.8K = $4,300 range!) provides real stress test
3. Data quality high — 1,518 clean data points over 12.9 hours
4. Settlement tracker accumulating data

---

## 6. GO/NO-GO Assessment

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| BRTI Proxy >95% | 95% | 73% | ❌ FAIL |
| >5 windows/day | 5/day | ~100/day | ✅ PASS |
| Windows >10s | >10s | 40s avg | ✅ PASS |
| Win rate >60% | 60% | 67% | ⚠️ MARGINAL |
| Positive PnL | >0 | $0.10 | ⚠️ MARGINAL |
| >5 trades/day | 5/day | ~4.5/day | ⚠️ MARGINAL |

### Verdict: 🟡 CONDITIONAL NO-GO for Delay Arbitrage (as-is)

BRTI proxy accuracy (73%) is the dealbreaker. Without 90%+ directional accuracy, delay arbitrage is essentially gambling with a thin edge that gets consumed by the $0.03 median spread.

---

## 7. Recommendations

### Immediate (Next 24h)
1. ✅ **Monitor restarted** — new continuous_monitor.py running (PID 114976)
2. **Accumulate more settlement data** — need 10+ to validate proxy properly
3. **Reduce polling interval** to 10s (currently 20-30s)
4. **Add Bitstamp** to BRTI proxy for better accuracy

### Strategy Pivot
1. **🌟 Momentum/Logic Arbitrage (Option C) looks most promising**
   - Doesn't need perfect BRTI proxy
   - Trade based on BTC trend + probability modeling
   - More signals per hour possible
   - Sustainable edge even if others discover it

2. **Consider hourly markets** instead of 15-min
   - More time for price discovery lag
   - Bigger absolute moves = overcome spread more easily
   - More room for our signals to develop

3. **WebSocket implementation** critical if continuing delay approach
   - Current REST polling (20-30s) misses fast windows
   - Need sub-second reaction time for delay arb

### Data Collection Plan
- Keep monitors running 24/7
- Settlement tracker continues (PID 54477)
- Build dataset for momentum model training
- Target: 48 hours of continuous data before final strategy decision

---

## Appendix: Data Files

| File | Size | Description |
|------|------|-------------|
| collection_20260202_024420.jsonl | 320KB | Main: 1,518 pts over 12.9h |
| continuous_20260202_105014.json | 191KB | 8h monitor (8 signals, 2 trades) |
| continuous_20260202_110118.json | 192KB | 8h monitor (5 signals, 1 trade) |
| paper_trade_20260202_105013.json | 221KB | Paper: 2 trades, $0 PnL |
| paper_trade_20260202_110119.json | 217KB | Paper: 1 trade, +$0.10 PnL |
| overnight_20260202_110408.json | 112KB | Overnight (32 market transitions) |
| overnight_20260202_121511.json | 111KB | Overnight (32 market transitions) |
| settlements.json | 239B | 1 settlement recorded |
| brti_proxy_20260202_014905.json | 263B | Initial BRTI proxy calibration |
