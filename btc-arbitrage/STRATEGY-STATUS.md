# BTC Kalshi Strategy Status — DO NOT REPEAT FAILED RESEARCH

Last updated: 2026-02-05 02:50 UTC

## ✅ WORKING / IN PRODUCTION

### V10 (baseline — v7 params + 6 strategies)
1. **delay_arb** — 0.20% threshold, 3min timeout (v7 params, best WR 65.7%)
2. **orderbook_imbalance** — bid/ask volume ratio predicts direction (imbalance > 0.3)
3. **settlement_rush** — last 5 min before settlement, trade based on BTC vs strike
4. **momentum_cluster** — 3+/4 exchanges moving same direction simultaneously
5. **tick_burst** — 4+ consecutive BTC ticks same direction, >0.10% total
6. **steam_follow** — detect smart money via Kalshi price jumps >3¢/60s or volume spikes >3x
7. **Kelly Criterion sizing** — dynamic position sizing based on per-strategy win rate
8. **CLV tracking** — closing line value analytics (not a strategy, measures signal quality)

### V11 (A/B test — V10 + 5-min trend filter)
- Same as V10 but blocks counter-trend and flat-market trades
- Data validated: with-trend +$1.56, counter-trend -$2.55, flat -$4.42

### V12 (quant enhanced — V11 + technical analysis + OKX derivatives)
- ATR(14), RSI(14), EMA(5/20), Bollinger Bands
- Volatility regime detection, multi-timeframe confirmation
- OKX derivatives: funding rate, open interest, long/short ratio
- ATR-based adaptive stops (1.5x-2.0x ATR, clamped $0.05-$0.20)
- Coinbase historical bootstrap (300 candles, instant indicators)

### V13 (Polymarket lead — V12 + cross-platform price discovery)
- **NEW**: Polymarket price feed as leading indicator (20x volume vs Kalshi)
- **pm_lead strategy**: detect PM price divergence → trade Kalshi lag
- PM event auto-discovery (highest volume daily BTC/ETH event)
- PM sentiment tracking (volume-weighted average across strikes)
- PM resolves noon ET, Kalshi 5pm ET — direction correlation, not same event
- All V12 features preserved

## ❌ CONFIRMED NOT WORKING — DO NOT REVISIT
1. **mean_reversion** (all variants: high, low, flash crash) — LOSES MONEY in every version. v6: -$29.60, v7: -$40.70, v8: -$61.50. Disabled everywhere.
2. **rebalancing arbitrage** — IMPOSSIBLE on Kalshi BTC. Single binary per event. YES+NO = $1.00 + spread mechanically. Only works on multi-bracket events (GDP, CPI).
3. **cross-platform arbitrage (Kalshi vs Polymarket)** — IMPOSSIBLE as risk-free arb. Resolution times differ (PM=noon ET, Kalshi=5pm ET). Price gaps only 2-5¢ (fees eat it). Capital split across USDC/USD. BUT: PM prices work as a LEADING INDICATOR — see V13 pm_lead strategy.
4. **calendar spreads** — 15min and 1h markets don't overlap enough for consistent opportunities.

## 🔍 RESEARCHED BUT NOT YET IMPLEMENTED
1. **BTC Futures correlation** — CME futures implied probability vs Kalshi. 3-10¢ edge. NEEDS: CME data feed.
2. **ML signal model** — Multi-feature prediction. 55-58% accuracy. NEEDS: 4-6 weeks dev.
3. **News-driven trading** — Fast news → trade. 3-10% on events. NEEDS: news feed API.
4. **Market making** — Provide liquidity both sides. NEEDS: Kalshi write API (we only have read-only).
5. **ETF flow arbitrage** — GBTC/BITO/IBIT premiums lead BTC by 30-90s. NEEDS: ETF data feed.
6. **Whale tracking** — Large BTC wallet movements. NEEDS: on-chain data integration.
7. **Fed rate correlation** — Kalshi Fed markets predict BTC vol. Event-driven, occasional.
8. **Stablecoin depeg monitoring** — USDC/USDT stress = BTC crash. Rare but high impact.
9. **Google Trends spikes** — Search volume predicts volatility. Has delays.
10. **Weekend pattern specialization** — Different strategies for weekends vs weekdays.

## 🔑 KEY CONSTRAINTS
- Kalshi BTC = single binary contract per event (above/below threshold)
- READ-ONLY API key — can't place real orders yet
- Polymarket has no short-term BTC markets
- Low volatility = almost no signals for any strategy
- Settlement is based on BRTI (Bloomberg Real-Time Index)
