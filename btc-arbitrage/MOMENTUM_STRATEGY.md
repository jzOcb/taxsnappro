# Momentum/Logic Arbitrage Strategy
**Created:** 2026-02-02T15:50Z  
**Status:** Design Phase  
**Target:** Kalshi 15-minute BTC markets

---

## 📋 Executive Summary

**Core Thesis:** Kalshi market makers react slowly to BTC momentum. We can predict short-term direction using momentum indicators and enter before Kalshi prices fully adjust.

**Key Difference from Delay Arbitrage:**
- ❌ Delay Arb: Needs perfect BRTI proxy (95%+ accuracy) → we only have 73%
- ✅ Momentum Arb: Needs directional edge from BTC trends → achievable with technical indicators

**Edge:** Market makers use lagging indicators or wider bands. We use real-time momentum to predict next 5-15 minute direction.

---

## 🎯 Strategy Logic

### Core Concept
Kalshi 15-minute markets ask: "Will BTC close above $X?"

Market makers price these based on:
1. Current BTC price relative to strike
2. Time remaining in window
3. Realized volatility

**Our edge:** When BTC shows strong momentum (e.g., breaking resistance, RSI extremes), the *probability* of continuing in that direction for next 5-15 minutes is >50%, but Kalshi prices lag 20-60 seconds behind due to:
- REST API polling delays
- Conservative market maker risk management
- Human intervention on their side

### Signal Generation

We combine multiple momentum indicators:

#### 1. **Price Rate of Change (ROC)**
```
ROC = (Price_now - Price_t-N) / Price_t-N × 100
```
- **Fast ROC** (N=2min): Captures immediate momentum
- **Medium ROC** (N=5min): Filters noise
- **Threshold:** |ROC| > 0.15% = strong momentum

#### 2. **RSI (Relative Strength Index)**
```
RSI = 100 - (100 / (1 + RS))
RS = Avg Gain / Avg Loss over 14 periods
```
- **Overbought:** RSI > 70 → expect reversal or continuation squeeze
- **Oversold:** RSI < 30 → expect bounce or capitulation
- **Mid-extremes (40-60):** Ignore, no edge

#### 3. **MACD (Moving Average Convergence Divergence)**
```
MACD = EMA12 - EMA26
Signal Line = EMA9(MACD)
Histogram = MACD - Signal
```
- **Bullish cross:** MACD crosses above signal → upward momentum
- **Bearish cross:** MACD crosses below signal → downward momentum
- **Histogram expansion:** Strengthening trend

#### 4. **Volume-Weighted Momentum**
```
Volume Spike = Current_Volume / Avg_Volume_10min
```
- Volume spike + price move = stronger conviction
- Kalshi volume spike = late entry (avoid)

### Decision Matrix

| Condition | Signal | Confidence |
|-----------|--------|------------|
| Fast ROC >0.2% + RSI 60-75 + MACD bullish | BUY YES | High |
| Fast ROC >0.15% + Medium ROC >0.1% | BUY YES | Medium |
| Fast ROC <-0.2% + RSI 25-40 + MACD bearish | BUY NO | High |
| Fast ROC <-0.15% + Medium ROC <-0.1% | BUY NO | Medium |
| RSI >85 or <15 + ROC aligned | BUY (fade) | Medium |
| Near market close (<2min) + price away from strike | AVOID | N/A |

### Entry Rules

1. **Time Window:** Only trade if >5 minutes remaining (avoid late-stage convergence)
2. **Spread Filter:** Only enter if spread ≤ $0.05 (otherwise friction too high)
3. **Strike Distance:** Prefer strikes within 0.3% of current price (higher edge)
4. **Position Sizing:** Risk 1-2% of bankroll per trade
5. **Max Exposure:** No more than 3 concurrent positions

### Exit Rules

1. **Time-based:** Close at 1 minute before market close (avoid settlement risk)
2. **Profit target:** +10% ROI (e.g., buy at $0.50, sell at $0.55)
3. **Stop loss:** -15% (e.g., buy at $0.50, stop at $0.425)
4. **Momentum reversal:** If indicators flip (e.g., RSI crosses 50 in opposite direction)

---

## 📊 Backtest Plan

### Data Requirements
- ✅ 12.9 hours of tick data (1,518 points)
- ✅ BTC price with timestamps
- ✅ Kalshi bid/ask/volume
- Need to calculate: RSI, MACD, ROC from BRTI proxy

### Backtest Parameters
```python
{
  "lookback_rsi": 14,           # RSI period (in ticks, ~7 minutes at 30s interval)
  "lookback_macd_fast": 12,     # MACD fast EMA
  "lookback_macd_slow": 26,     # MACD slow EMA
  "lookback_macd_signal": 9,    # MACD signal line
  "roc_fast_period": 4,         # 2 minutes (4 × 30s)
  "roc_medium_period": 10,      # 5 minutes (10 × 30s)
  "min_time_remaining": 300,    # 5 minutes in seconds
  "max_spread": 0.05,           # $0.05 max spread
  "entry_threshold_roc": 0.15,  # 0.15% momentum threshold
  "profit_target": 0.10,        # 10% ROI
  "stop_loss": 0.15             # 15% max loss
}
```

### Success Criteria
- **Win rate:** >55% (need edge over random)
- **Avg trade ROI:** >5% (overcome spread + slippage)
- **Trade frequency:** >5/day (signal abundance)
- **Sharpe ratio:** >1.0 (risk-adjusted returns)
- **Max drawdown:** <20% (risk management)

---

## 🔬 Validation Approach

### Phase 1: Indicator Calculation (✅ Next)
1. Parse `collection_20260202_024420.jsonl`
2. Calculate RSI, MACD, ROC for each tick
3. Visualize indicators vs BTC price movement
4. Identify historical signal quality

### Phase 2: Backtest Execution
1. Simulate entries based on decision matrix
2. Track paper trades with realistic spread assumptions
3. Calculate PnL, win rate, trade frequency
4. Generate detailed report with charts

### Phase 3: Robustness Testing
1. Parameter sensitivity analysis (what if ROC threshold = 0.10% vs 0.20%?)
2. Forward-looking walk-forward test (train on first 6 hours, test on last 6 hours)
3. Worst-case scenario: What if we're 2 minutes late on every signal?

### Phase 4: Live Paper Trading
1. Deploy strategy in monitor mode (no real trades)
2. Run for 48 hours alongside current monitors
3. Compare predictions vs actual outcomes
4. Tune parameters based on live performance

---

## 🚀 Implementation Roadmap

### Step 1: Analysis Script (Today)
- [x] Design strategy
- [ ] Write `momentum_backtest.py`
- [ ] Calculate indicators on historical data
- [ ] Generate backtest report

### Step 2: Strategy Module (Tomorrow)
- [ ] Create `src/momentum_strategy.py`
- [ ] Implement signal generation logic
- [ ] Add risk management (position sizing, stops)
- [ ] Unit tests

### Step 3: Live Integration (Day 3)
- [ ] Integrate with existing monitor infrastructure
- [ ] Add Kalshi order execution (dry-run first)
- [ ] Real-time indicator calculation
- [ ] Alert system for signal generation

### Step 4: Production (Day 4-5)
- [ ] 48-hour live paper trading
- [ ] Tune parameters based on results
- [ ] Deploy with small capital ($100)
- [ ] Monitor and iterate

---

## ⚠️ Risk Considerations

### Market Risks
1. **Momentum reversal:** BTC can reverse suddenly (use stops)
2. **Kalshi liquidity:** Spread widening during volatility
3. **Settlement risk:** Wrong side of binary outcome

### Operational Risks
1. **Latency:** Our 20-30s polling might miss signals (solution: reduce to 10s)
2. **API rate limits:** Kalshi might throttle if we poll too aggressively
3. **Data quality:** Outlier ticks could trigger false signals

### Strategy Risks
1. **Overfitting:** Backtest looks good, live fails (solution: walk-forward validation)
2. **Market adaptation:** If strategy works, others copy → edge disappears
3. **Correlation breakdown:** Momentum indicators might not predict Kalshi as well as assumed

### Mitigation
- Conservative position sizing (1-2% per trade)
- Strict stop losses (-15% max)
- Continuous monitoring and parameter adjustment
- Kill switch if daily loss exceeds -5%

---

## 📈 Expected Performance (Hypothesis)

Based on analysis of delay arbitrage data:
- **Trade frequency:** ~10-15/day (vs 3/day for delay arb)
- **Win rate:** 60-65% (vs 67% but with more signals)
- **Avg ROI per trade:** 6-8% (vs 3% for delay arb)
- **Daily ROI:** 0.5-1.0% (vs 0.01% for delay arb)

**Reasoning:**
- Momentum signals are more abundant than perfect arbitrage windows
- We don't need 95% accuracy — just >50% with good risk/reward
- BTC is volatile enough that 15-min trends exist and persist
- Kalshi market makers ARE slow (we observed this in delay arb data)

---

## 🔗 References

**Internal:**
- `ANALYSIS.md` — Delay arbitrage findings
- `data/collection_20260202_024420.jsonl` — Historical data
- `scripts/analyze_pattern.py` — Existing analysis code

**Theoretical Basis:**
- RSI: Wilder, J. W. (1978). *New Concepts in Technical Trading Systems*
- MACD: Appel, G. (2005). *Technical Analysis: Power Tools for Active Investors*
- Momentum Trading: Jegadeesh & Titman (1993). "Returns to Buying Winners and Selling Losers"
- Prediction Markets: Wolfers & Zitzewitz (2004). "Prediction Markets"

**Assumptions:**
1. BTC momentum persists for 5-15 minute windows (verifiable in backtest)
2. Kalshi market makers have 20-60s latency (observed in data)
3. Technical indicators provide >50% directional accuracy (to be validated)
4. Spread remains <$0.05 under normal conditions (median $0.03 in data)

---

## ✅ Next Steps

1. **Implement `momentum_backtest.py`** — Calculate indicators and simulate trades
2. **Run backtest on 12.9h data** — Validate hypothesis
3. **Generate report with charts** — Win rate, PnL curve, signal distribution
4. **Update STATUS.md and ANALYSIS.md** — Document findings

**ETA:** Backtest complete by end of day (2026-02-02)
