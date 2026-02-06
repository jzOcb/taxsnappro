# Quantitative Trading Research — Improvements for V10/V11
## Date: 2026-02-04

## Current Problems Identified
1. **No trend awareness** — steam_follow trades both directions regardless of macro trend
2. **Fixed stops** — $0.15/$0.12 regardless of current volatility regime
3. **No volatility regime detection** — same strategy in calm vs chaotic markets
4. **No RSI/overbought-oversold filtering** — enters at extreme levels
5. **Single timeframe momentum** — only 1-min or 5-min, no multi-timeframe confirmation

---

## Research Findings: What Professional Quants Use

### 1. VOLATILITY REGIME DETECTION (Priority: HIGH)
**Concept:** Market behavior changes fundamentally between low-vol and high-vol regimes.

**Implementation: ATR (Average True Range)**
- Calculate 14-period ATR on BTC 1-min candles
- **Low vol regime** (ATR < 0.05%): Mean-reversion works, tight stops
- **High vol regime** (ATR > 0.15%): Only trend-following, wide stops
- **Transition regime**: Reduce position size or sit out

**For our Kalshi strategy:**
- High vol → widen stops dynamically (ATR-based instead of fixed $)
- High vol → only trade WITH trend (V11 approach)
- Low vol → can trade both directions with tighter stops
- Very high vol (>0.25%) → stop trading entirely (circuit breaker)

### 2. MULTI-TIMEFRAME TREND CONFIRMATION (Priority: HIGH)
**Concept:** Align signals across multiple timeframes before entering.

**Implementation:**
- **5-min EMA** (fast trend): Direction of immediate momentum
- **15-min EMA** (medium trend): Direction of broader move  
- **1-hour change** (macro trend): Overall session direction

**Entry rule:** Only enter when 2/3 timeframes agree with signal direction.
- All 3 aligned = full size
- 2/3 aligned = half size
- 1/3 or 0/3 = no trade

### 3. RSI FILTER (Priority: MEDIUM)
**Concept:** Don't buy when already overbought, don't sell when oversold.

**Implementation for Kalshi:**
- Calculate 14-period RSI on BTC 1-min candles
- RSI > 70 → don't enter YES (already overbought, likely to pull back)
- RSI < 30 → don't enter NO (already oversold, likely to bounce)
- RSI 40-60 → strongest signals (room to move in either direction)

**Key insight from research:** "RSI works best in trading ranges, NOT trending markets."
- So: use RSI filter in low-vol regimes, disable in high-vol trending markets

### 4. BOLLINGER BAND SQUEEZE (Priority: MEDIUM)  
**Concept:** Bollinger Band width predicts upcoming volatility expansion.

**Implementation:**
- Track 20-period BB width on BTC 1-min
- **Squeeze** (bands narrow): Breakout incoming — prepare for steam signal
- **Expansion** (bands wide): Trend already in motion — be cautious of late entry

**For Kalshi:** If BB width is below 20th percentile (squeeze), steam signals are more reliable because the breakout has more potential energy.

### 5. ADAPTIVE STOP-LOSS (Priority: HIGH)
**Concept:** Stop distance should be function of current volatility, not fixed.

**Current:** Fixed $0.15 BTC / $0.12 ETH
**Improved:** 1.5x ATR(14) in dollars

Example:
- ATR(14) = 0.08% on BTC at $73,000 → $58/min range
- Kalshi mid-price ~$0.50, so 1.5x ATR translated to contract = ~$0.06-0.08
- ATR(14) = 0.20% → wider range → stop at $0.12-0.15

**This automatically tightens in calm markets and widens in volatile ones.**

### 6. DIRECTIONAL CHANGE (DC) ALGORITHM (Priority: LOW — future)
**From Wikipedia/academic research:** DC algorithms detect trend transitions by measuring when price moves beyond a threshold, then entering during the "overshoot" period.

This is conceptually what our steam_follow does — detect a significant price move and follow it. But DC adds:
- **Threshold calibration** based on asset volatility
- **Overshoot measurement** — how far price goes after the directional change
- Better entry timing (after confirmation, not at detection)

### 7. EMA CROSSOVER AS REGIME INDICATOR (Priority: MEDIUM)
**Concept:** Fast EMA crossing slow EMA = trend change confirmation.

**Implementation:**
- EMA(5) crossing above EMA(20) = bullish regime
- EMA(5) crossing below EMA(20) = bearish regime
- Use as a macro filter (like V11 trend filter but more robust)

**Advantage over simple momentum:** Less noisy, filters out micro-fluctuations

---

## Recommended Implementation Priority

### Phase 1 (Implement in V12 — Immediate)
1. ✅ **Trend filter** (already in V11) — 5-min momentum direction
2. 🔧 **ATR-based adaptive stops** — replace fixed $0.15/$0.12
3. 🔧 **Volatility regime detection** — ATR threshold to pause trading
4. 🔧 **Multi-timeframe confirmation** — require 2/3 timeframes aligned

### Phase 2 (After baseline data)
5. **RSI filter** — add overbought/oversold guard in ranging markets
6. **BB squeeze detector** — enhance steam signal quality
7. **EMA crossover regime** — replace simple momentum with EMA cross

### Phase 3 (Advanced)
8. **DC algorithm** — academic approach to trend detection
9. **ML signal model** — train on our trade history
10. **Kelly sizing with regime adjustment** — reduce size in uncertain regimes

---

## Key Principles from Research

1. **"The RSI works best in trading ranges, NOT trending markets"**
   → Different tools for different regimes. Don't use one strategy for all conditions.

2. **"Bollinger Bands widen = high vol, narrow = low vol"**
   → Volatility clustering is real. High vol begets high vol.

3. **"Moving averages as dynamic support/resistance"**
   → Price tends to bounce off EMAs — useful for entry timing.

4. **"Adaptive systems outperform static ones in volatile markets"** (from DC research)
   → Our fixed thresholds ($0.15 stop, 3¢ steam threshold) should be dynamic.

5. **"Align trades with the trend"** (from Investopedia)
   → "Using bullish signals primarily when price is in a bullish trend" — exactly what V11 does.

6. **"Most profitable strategies combine multiple confirming indicators"**
   → Single indicator (steam alone) = noisy. Steam + trend + volatility regime = robust.
