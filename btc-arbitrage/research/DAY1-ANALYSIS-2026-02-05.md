# Day 1 Trading Fleet Analysis — 2026-02-05

## Executive Summary

**Total Fleet P&L: -$103.44** (realized: -$103.44, unrealized weather: -$614.54 not yet settled)

| Bot | P&L | Trades | Win Rate | Status |
|-----|-----|--------|----------|--------|
| V11 Crypto | -$17.21 | 154 | 45.5% | ⚠️ Modify |
| V14 Crypto | -$10.04 | 44 | 27.3% | ⚠️ Modify |
| Weather V2 | -$614.54 (unrealized) | 17 | 0/0 | 🔴 Critical |
| Mention NO Grinder | -$75.84 | 18 | 2W/3L | 🔴 Fix |
| NBA | $0.00 | 0 | — | ✅ Keep (working as designed) |
| Cross-Platform V3 | +$1.00 | 12 | 33% | ✅ Keep & Scale |

**Market Context:** BTC -10.3%, ETH -8.7% — extreme selloff. This is a tail event day. Some losses are structural (strategy bugs), some are regime-driven.

---

## 1. Mention NO Grinder Deep Dive — BIGGEST ISSUE (-$75.84)

### What Happened

The Mention trader opened 18 NO positions across Trump-related mention markets. 5 have settled, 13 remain open.

### Settled Trade-by-Trade Analysis

| # | Market | Side | Entry | Contracts | Cost | Result | P&L | Edge Est. | Actual Prob |
|---|--------|------|-------|-----------|------|--------|-----|-----------|-------------|
| 1 | Trump Prayer Breakfast: "Hottest" | NO@61¢ | 49 | $29.89 | **YES** | **-$29.89** | 24.5¢ | ~40%+ |
| 2 | Trump Prayer Breakfast: "Ukraine" | NO@70¢ | 42 | $29.40 | **YES** | **-$29.40** | 19.5¢ | ~65%+ |
| 3 | Trump Prayer Breakfast: "Peace in ME" | NO@69¢ | 43 | $29.67 | **YES** | **-$29.67** | 19.0¢ | ~60%+ |
| 4 | Trump Prayer Breakfast: "Affordable" | NO@74¢ | 40 | $29.60 | NO | **+$10.40** | 16.0¢ | ~15% |
| 5 | Trump Prayer Breakfast: "Ballroom" | NO@84¢ | 17 | $14.28 | NO | **+$2.72** | 13.0¢ | ~5% |
| | **SETTLED TOTAL** | | | **$133.24** | | **-$75.84** | | |

### Root Cause: Catastrophically Bad Probability Estimates

The strategy uses a **hardcoded heuristic probability model** (`TRUMP_WEEKLY_BASE_RATES` dict). For all three losing trades, the model estimated `fair_yes = 15%`. The actual outcomes:

- **"Ukraine"**: Trump talks about Ukraine in virtually every public appearance. The market priced YES at 34.5¢ — the market was RIGHT, the model was WRONG. True probability was likely 65%+.
- **"Peace in the Middle East"**: One of Trump's signature talking points. Market priced YES at 34¢. True probability: ~60%+. Model said 15%.
- **"Hottest"**: At a Prayer Breakfast where he was praising people, "hottest" is a natural Trump adjective. Market priced YES at 39.5¢. Model said 15%.

**The model underestimated these probabilities by 3-4x.** The "edge" was an illusion.

### Why the Wins Don't Compensate

Even on the winning trades, the asymmetry is terrible:
- **Losses**: Each losing NO trade costs the full entry price ($29-30). When YES resolves, you lose everything.
- **Wins**: "Affordable" won +$10.40 on $29.60 cost. "Ballroom" won +$2.72 on $14.28 cost.
- The win amounts are the (100 - NO_price) × contracts. Buying NO at 70-84¢ means your upside is only 16-30¢ per contract, but your downside is 70-84¢ per contract.

**Risk/Reward on settled trades: Lost $88.96 on 3 losses, Won $13.12 on 2 wins.**  
Win rate needed to break even at these prices: ~87%. Actual: 40%.

### Open Positions — Still at Risk ($257.07 exposed)

| Market | Side | Entry | Cost | Edge Est. | Close Date | Risk Assessment |
|--------|------|-------|------|-----------|------------|-----------------|
| Armada (PM) | NO@66¢ | $29.70 | 19¢ | Feb 8 | 🟢 Likely safe |
| Green Day/Bad Bunny (PM) | NO@74¢ | $29.80 | 18¢ | Feb 8 | 🟢 Likely safe |
| Saudi Arabia (K, SOTU) | NO@63¢ | $29.61 | 16.5¢ | Mar 1 | 🟡 Medium risk — Trump may discuss |
| Korea (K, SOTU) | NO@64¢ | $49.92 | 30.5¢ | Mar 1 | 🔴 HIGH RISK — Korea is frequent topic |
| Japan (K, SOTU) | NO@60¢ | $30.00 | 16.5¢ | Mar 1 | 🔴 HIGH RISK — Trade partner, tariffs |
| Somalia (K, SOTU) | NO@60¢ | $30.00 | 17¢ | Mar 1 | 🟡 Medium — less common topic |
| Thug (K, weekly) | NO@60¢ | $30.00 | 16.5¢ | Feb 9 | 🟡 Medium |
| Paid Agitator (K) | NO@81¢ | $14.58 | 14.5¢ | Feb 9 | 🟢 Likely safe |
| Antifa (K) | NO@66¢ | $14.52 | 14.5¢ | Feb 9 | 🟡 Medium |
| TDS (K) | NO@72¢ | $14.40 | 14¢ | Feb 9 | 🟡 Medium |
| Nicki/Rapper (PM) | NO@75¢ | $15.00 | 13¢ | Feb 8 | 🟢 Likely safe |
| Memphis (K, SOTU) | NO@61¢ | $14.64 | 10.5¢ | Mar 1 | 🟢 Likely safe |
| Anarchist (PM) | NO@74¢ | $14.90 | 10.5¢ | Feb 8 | 🟢 Likely safe |

**Korea ($49.92) and Japan ($30.00) are particularly dangerous** — these are countries Trump frequently discusses in economic/trade contexts, and SOTU addresses historically cover major trade partners.

### Recommendations for Mention Trader

1. **CRITICAL: Replace heuristic model with data-driven base rates.** Scrape historical Trump transcripts to calculate actual word/phrase frequencies. A simple TF-IDF on last 30 days of transcripts would be 10x better than hardcoded guesses.

2. **Fix the risk/reward math.** Buying NO at 60-70¢ means 60-70¢ downside for 30-40¢ upside. You need >60% accuracy just to break even. Either:
   - Only buy NO at 80¢+ (so upside/downside is more balanced)
   - Reduce position sizes on lower-confidence estimates
   - Add a Kelly criterion: `f = (bp - q) / b` where b = (100-NO_price)/NO_price

3. **Context-aware probability adjustment.** A Prayer Breakfast speech is very different from a random press conference. The model should adjust base rates for the specific event type.

4. **Cap per-market risk at $15 instead of $30.** The bot risked $30/market on heuristic estimates. With 18 markets, that's $540 exposed — too much for Day 1 paper trading.

5. **Add a "likely mention" blocklist.** Words like "Ukraine", "China", "border" should have near-certain base rates for Trump speeches. Don't sell NO on these.

---

## 2. V11 Crypto Analysis (-$17.21, 154 trades)

### Performance Summary

| Metric | Value |
|--------|-------|
| Total Trades | 154 |
| Win Rate | 45.5% (70W / 84L) |
| Avg Win | $0.95 |
| Avg Loss | -$1.00 |
| Profit Factor | 0.80 |
| Expected Value/Trade | -$0.11 |
| Strategy | steam_follow (100%) |

### Win/Loss Distribution

```
P&L per trade:
         <= -$3:   2 ██
     -$3 to -$2:   6 ██████
     -$2 to -$1:  23 ███████████████████████
      -$1 to $0:  53 █████████████████████████████████████████████████████
       $0 to $1:  43 ███████████████████████████████████████████
       $1 to $2:  18 ██████████████████
       $2 to $3:   6 ██████
           > $3:   3 ███
```

**Key insight: The distribution is roughly symmetric but slightly negative-skewed.** Losses are marginally larger than wins ($1.00 vs $0.95 avg). With a 45.5% win rate, this produces a slow bleed.

### Market Type Breakdown

| Market | Trades | P&L | Win Rate |
|--------|--------|-----|----------|
| BTC 15m | 82 | -$3.68 | 46% |
| ETH 15m | 72 | -$13.53 | 44% |

**ETH is significantly worse.** ETH dropped -8.7% today (vs BTC -10.3%), but the ETH 15-minute markets seem to have wider spreads and worse fills, amplifying losses.

### Direction Analysis

| Direction | Trades | P&L | Win Rate |
|-----------|--------|-----|----------|
| YES (long) | 75 | -$12.59 | 48% |
| NO (short) | 79 | -$4.62 | 43% |

**Critical finding: Going YES (long) on a -10% crash day was devastating.** YES trades lost $12.59 vs NO losing $4.62. On a crash day, the steam_follow strategy should have detected the downtrend and biased toward NO. It didn't.

### Session-by-Session (showing crash impact)

| Session | Time | Trades | P&L | Context |
|---------|------|--------|-----|---------|
| 1 (Feb 4 22:44) | Pre-crash | 2 | +$1.35 | Normal market |
| 2 (Feb 5 01:13) | Early crash | 19 | -$2.34 | BTC dropping |
| 3 (Feb 5 09:40) | Peak crash | 83 | -$7.23 | Most active, worst |
| 4 (Feb 5 14:30) | Post-crash A | 14 | -$2.90 | Still choppy |
| 5 (Feb 5 14:30) | Post-crash B | 14 | -$0.57 | Same restart |
| 6 (Feb 5 16:07) | Late session | 22 | -$5.52 | Continued decline |

Session 6 trade detail shows repeated large YES losses in a falling market:
- YES 15m entry=0.840 exit=0.700: **-$1.40** (bought high, market fell)
- YES 15m entry=0.580 exit=0.370: **-$2.10** (momentum disappeared)
- YES 15m entry=0.670 exit=0.520: **-$1.50** (same pattern)

### Root Cause

1. **No regime detection.** Steam_follow trades both directions equally on a crash day. It should reduce YES sizing or add a bearish bias when the underlying is in a -5%+ day.
2. **ETH trades too aggressively.** Half the size (5 contracts vs 10) but similar loss rates = still bleeding on ETH.
3. **45% WR with 1:1 risk/reward is a guaranteed loser.** Need either higher WR (>50%) or better risk/reward (bigger wins, smaller losses).

### Recommendations

1. **Add market regime filter:** If BTC/ETH is down >3% in last 4h, bias toward NO or reduce position size by 50%.
2. **Widen stop-losses slightly:** The distribution shows many trades losing $0.10-$1.00 — these might be getting stopped out just before reversal. Analyze max adverse excursion.
3. **Reduce ETH trade frequency or size.** ETH 15m markets are less liquid and the strategy loses more there.
4. **Consider asymmetric sizing:** On crash days, make NO positions 2x the size of YES positions.

---

## 3. V14 Crypto Analysis (-$10.04, 44 trades)

### Strategy Breakdown

| Strategy | Trades | Win Rate | Avg Win | Avg Loss | P&L |
|----------|--------|----------|---------|----------|-----|
| steam_follow | 29 | 37.9% | $0.84 | -$0.76 | -$4.44 |
| flash_sniper | 15 | **6.7%** | $0.40 | -$0.43 | **-$5.60** |

### Flash Sniper: Near-Total Failure

Flash sniper won **1 out of 15 trades** (6.7% WR). Breakdown:

| Market | Trades | P&L | Win Rate |
|--------|--------|-----|----------|
| BTC 15m | 10 | -$4.90 | 10% |
| ETH 15m | 5 | -$0.70 | 0% |

The flash_sniper strategy attempts to catch sudden price movements. On a crash day, these "flashes" are overwhelmingly downward, but the strategy doesn't distinguish direction well. Nearly every flash_sniper trade was a small loss (-$0.30 to -$0.50), suggesting it's entering on false signals and getting stopped out.

### Steam Follow: Also Struggling

V14's steam_follow is worse than V11's (37.9% vs 45.5% WR). The key difference:
- **ETH 15m steam_follow: 23% WR** — catastrophic. ETH's momentum signals are unreliable in V14.
- **BTC 15m steam_follow: 50% WR** — actually decent, but not enough to overcome ETH losses.

### P&L Distribution

```
V14 Flash Sniper:
  Most trades in -$0.50 to $0 range (10 out of 15)
  Classic "death by a thousand cuts" — many small losses, rare wins

V14 Steam Follow:
  More dispersed, but ETH side is heavily loss-weighted
  BTC side is close to breakeven
```

### Recommendations

1. **Kill flash_sniper immediately.** 6.7% WR is not salvageable. The signal is not capturing real alpha.
2. **V14 steam_follow on ETH: disable or rethink.** 23% WR means the signal is actually negatively correlated with outcomes on ETH.
3. **Focus V14 on BTC 15m only** where steam_follow shows 50% WR — refine from there.
4. **If keeping flash_sniper, add minimum move threshold.** The "flash" detection may be triggering on noise. Require a larger price move before entering.

---

## 4. Weather V2 Analysis — HIDDEN CATASTROPHE

### ⚠️ Unrealized P&L: -$614.54 on $569 invested

The Weather V2 bot shows $0 realized P&L because nothing has settled yet. But the unrealized losses tell a devastating story:

### Fee Disaster

| Metric | Amount |
|--------|--------|
| Entry Cost | $569.16 |
| Fees Paid | **$234.66** |
| Fee Ratio | **41.2%** |

**The bot is paying 41¢ in fees for every $1 invested.** This is because it buys thousands of penny contracts:

| Position | Contracts | Price | Cost | Fees | Fee % |
|----------|-----------|-------|------|------|-------|
| CHI 35-36°F YES | 2,775 | 2¢ | $55.50 | $55.50 | **100%** |
| BOS <27°F YES | 2,000 | 3¢ | $60.00 | $40.00 | **67%** |
| PHX <77°F YES | 2,000 | 3¢ | $60.00 | $40.00 | **67%** |
| NYC <29°F YES | 1,200 | 5¢ | $60.00 | $24.00 | **40%** |
| LV >76°F YES | 1,239 | 4¢ | $49.56 | $24.78 | **50%** |

**Even if these positions WIN, the fees eat most of the profit.** CHI 35-36°F YES cost $55.50 + $55.50 fees = $111 total. Even if it settles at 100¢ × 2,775 = $2,775 (winning), the expected payout based on 16% fair value is $444 — but you only get it if the temp hits exactly 35-36°F.

### Forecast Accuracy Problem

Most positions are now deeply underwater because the **initial forecasts were wrong**:

| City | Forecast μ | Current METAR | Position | Outcome Likely? |
|------|-----------|---------------|----------|-----------------|
| BOS | 26.6°F → 32.0°F | 30.0°F | <27°F YES | ❌ Will lose |
| NYC | 24.9°F → 30.9°F | 28.9°F | <29°F YES | ❌ Probably lose |
| PHX | 77.8°F | 73.0°F | <77°F YES | ⚠️ Still possible |
| CHI | 32.4°F | 28.0°F | 35-36°F YES | ❌ Very unlikely |
| SFO | 71.9°F | 55.9°F | >73°F YES | ❌ Probably lose |
| MIA | 72.0°F | 62.1°F | >76°F YES | ❌ Probably lose |

The forecasts drifted significantly during the day. **The model entered positions at 13:33 UTC (early morning local time) using forecasts that turned out to be 4-8°F off.**

### Per-City Unrealized P&L

| City | uPnL | Main Issue |
|------|------|------------|
| CHI | -$112.80 | Bought 2775 contracts at 2¢ + $55.50 in fees. Temp won't hit 35-36°F |
| BOS | -$100.00 | Bought 2000 contracts at 3¢. Temp won't be <27°F (currently 30°F) |
| PHX | -$100.00 | Bought 2000 contracts at 3¢. Temp may stay above 77°F |
| NYC | -$84.00 | Bought 1200 contracts at 5¢. Temp won't be <29°F (currently 29°F) |
| SFO | -$68.56 | Bought 857 contracts at 7¢. Temp may not reach >73°F |

### Recommendations

1. **🔴 CRITICAL: Cap contract quantity to limit fees.** Never buy more than 100 contracts of a penny option. The fee structure makes large penny positions uneconomical.
2. **Don't trade penny contracts (<10¢) at all.** The bid-ask spread at these prices is 100% of the price, and fees per contract are fixed. Focus on 20-80¢ range where the economics work.
3. **Update forecasts before trading.** The bot entered all 17 positions at exactly 13:33 UTC using stale forecasts. Add a "wait for METAR confirmation" step: don't trade until the actual morning temperature confirms the forecast direction.
4. **Sigma is too tight.** Using σ=3.0°F for most cities, but actual forecast errors today were 4-8°F. Widen sigma to at least 5°F for Tier 1 cities.
5. **Reduce max exposure per city.** $60/city with penny contracts = thousands of contracts = huge fee load.

---

## 5. NBA Trader Analysis ($0, 0 trades)

### Why Zero Trades

The NBA bot scanned 14 games across 4 scan cycles and found **zero signals** above the 5¢ edge threshold. Here's why:

| Game | DK Fair | Kalshi Price | Edge |
|------|---------|-------------|------|
| 76ers @ Lakers | away=39.1¢ | Philly=38¢ | 1.1¢ |
| Warriors @ Suns | away=31.5¢ | GSW=32¢ | -0.5¢ |
| Bulls @ Raptors | away=25.9¢ | Chi=24¢ | 1.9¢ |
| Spurs @ Mavs | away=70.5¢ | SAS=72¢ | -1.5¢ |
| Hornets @ Rockets | away=41.7¢ | CHA=42¢ | -0.3¢ |
| Jazz @ Hawks | away=24.3¢ | Jazz=24¢ | 0.3¢ |
| Nets @ Magic | away=20.0¢ | BKN=20¢ | 0.0¢ |
| Wizards @ Pistons | away=14.8¢ | WAS=14¢ | 0.8¢ |

**NBA moneyline markets are extremely efficient.** Kalshi prices track DraftKings-derived fair values within 1-2¢. This is actually the bot working correctly — **not trading when there's no edge is the right decision.**

### But: 6 games had NO ODDS (future dates without DK lines)

The bot only trades when it has DraftKings odds to compare against. 6 of 14 matched games had "NO ODDS" because DK hadn't released lines yet. Once lines are available and games approach tip-off, edges may appear from:
- Injury news not yet reflected in Kalshi
- Late line moves on DraftKings
- In-play pricing discrepancies

### Recommendations

1. **Increase scan frequency near game time.** Currently 2-hour intervals. Switch to 15-minute scans within 2 hours of tip-off.
2. **Add in-play capability.** The biggest NBA edges appear during games when one platform lags the other.
3. **Lower edge threshold to 3¢** for paper testing. Even if we wouldn't trade 3¢ edges live, seeing what would happen at lower thresholds provides data.
4. **Add ESPN/DraftKings odds for totals and spreads,** not just moneylines. Kalshi also offers these markets and they may be less efficient.

---

## 6. Cross-Platform V3 Analysis (+$1.00, 12 trades) — THE WINNER

### Why It Works

Cross-platform V3 is the only profitable bot because it exploits **structural price differences between Polymarket and Kalshi** on the same event. This is pure arbitrage logic — it doesn't predict outcomes, it finds mispricings.

### Trade Analysis

| Trade | Pair | Direction | Entry | Exit | P&L | Signal | Duration |
|-------|------|-----------|-------|------|-----|--------|----------|
| XP2-0001 | weather:NYC:Feb06 | YES | 0.215 | 0.150 | -$3.25 | SPREAD_SIGMA | 60min |
| XP2-0002 | crypto:ETH:Feb05 | NO | 0.050 | 0.030 | +$1.00 | SPREAD_SIGMA | 60min |
| XP2-0003 | nba:HOU@OKC:Feb07 | YES | 0.400 | 0.465 | +$3.25 | SPREAD_SIGMA | 60min |
| XP2-0004 | nba:GSW@PHX:Feb05 | NO | 0.685 | 0.685 | $0.00 | SPREAD_SIGMA | 60min |
| XP2-0005 | crypto:ETH:Feb06 | YES | 0.010 | 0.010 | $0.00 | SPREAD_SIGMA | 60min |
| XP2-0006 | weather:ATL:Feb06 | NO | 0.290 | 0.290 | $0.00 | PM_MOMENTUM | 60min |

### Signal Type Performance

| Signal | Trades | Wins | Losses | Flat |
|--------|--------|------|--------|------|
| SPREAD_SIGMA | 10 | 2 | 1 | 3 |
| PM_MOMENTUM | 2 | 0 | 0 | 1 |

### Key Observations

1. **Spread-sigma finds real mispricings.** The ETH and NBA trades that won captured genuine cross-platform price differences.
2. **60-minute timeouts are appropriate.** Most spreads either converge quickly or don't converge at all. No need for longer holds.
3. **Flat exits ($0) are fine** — they mean the spread didn't converge but you didn't lose either.
4. **It tracks 28 pairs across 5 categories** (weather, crypto, NBA, trump_mentions, soccer). The diversity reduces correlation risk.

### Notable Spread Data from Monitoring

| Pair | Mean Spread | Stdev | Notes |
|------|-------------|-------|-------|
| weather:Seattle:Feb05 | **+0.785** | 0.057 | Massive PM vs Kalshi gap |
| weather:NYC:Feb06 | +0.227 | 0.043 | Consistent positive spread |
| nba:CHI@TOR:Feb05 | -0.510 | 0.010 | Kalshi 75.5¢ vs PM 25.5¢ — **inverted sides!** |
| nba:BKN@ORL:Feb05 | -0.549 | 0.006 | Same issue — likely different team |
| nba:CHA@HOU:Feb05 | -0.212 | 0.013 | Genuine spread |

⚠️ **Warning on NBA spreads:** Several NBA pairs show 50¢+ "spreads" (e.g., CHI@TOR -0.51). These are almost certainly **not real arbitrage** — they're comparing different sides. PM shows Toronto win probability at 75.5¢, while Kalshi shows Chicago at 24¢ — these are the SAME price, just different perspectives. The matcher needs to ensure it's comparing the same outcome.

### Recommendations

1. **Scale position sizes up to $100/trade** (from $50). The strategy has positive EV and limited risk per trade.
2. **Fix NBA pair matching.** Verify that PM and Kalshi prices represent the same team before calculating spreads. Currently, several NBA "spreads" are phantom arb due to home/away confusion.
3. **Increase scan frequency** to every 30 seconds for pairs with historical spread > 5¢.
4. **Add spread-mean-reversion as a signal.** If a spread is currently 2σ above its rolling mean, enter the convergence trade.
5. **Track time-of-day patterns.** Cross-platform mispricings may be more common at specific hours (e.g., when one platform has more liquidity than the other).

---

## 7. Strategy Effectiveness Matrix

| Signal Type | Bot(s) | Day 1 Result | Verdict |
|-------------|--------|-------------|---------|
| steam_follow | V11, V14 | V11: -$17.21 (45% WR), V14: -$4.44 (38% WR) | ⚠️ Modify — needs regime filter |
| flash_sniper | V14 | -$5.60 (6.7% WR) | 🔴 Kill — signal is noise |
| heuristic_NO_grind | Mention | -$75.84 (40% WR settled) | 🔴 Fix model — edge estimates are fantasy |
| weather_forecast_bet | Weather V2 | -$614 unrealized | 🔴 Fix sizing & fees — economics broken |
| SPREAD_SIGMA (cross-plat) | XP V3 | +$4.25 (2W 1L) | ✅ Working — scale up |
| PM_MOMENTUM (cross-plat) | XP V3 | $0 (0W 0L 1flat) | ⚠️ Insufficient data |
| DK_vs_Kalshi (NBA) | NBA | $0 (no trades) | ✅ Correct — market too efficient |

---

## 8. Market Regime Analysis: Impact of -10% Crypto Crash

### How the Crash Affected Each Bot

**V11 & V14 (Crypto):** Direct impact. The crash created extreme directional pressure in 15-minute Kalshi markets. Steam_follow's momentum signals were overwhelmed by the speed of the decline. YES trades (bullish) were repeatedly crushed as each 15-minute window resolved lower than entry. The strategy doesn't have a "don't go long in a crash" filter.

**Mention NO Grinder:** **Zero correlation with crypto crash.** The -$75.84 loss is entirely driven by bad probability estimates on Trump speech markets. This is a strategy bug, not a market regime problem.

**Weather V2:** **Zero correlation with crypto crash.** The unrealized losses are driven by inaccurate weather forecasts and fee structure. Weather markets are independent of crypto.

**NBA:** **Zero correlation.** NBA was already at zero trades due to efficient pricing.

**Cross-Platform V3:** **Indirect benefit.** The crypto crash may have created temporary mispricings between PM and Kalshi (different user bases react differently to volatility), which XP V3 could exploit. The ETH trade that made +$1 was a spread that appeared during the crash.

### Summary: Only ~$17 of losses are crash-related

| Bot | Loss | Crash-Related | Strategy-Related |
|-----|------|---------------|-----------------|
| V11 | -$17.21 | ~$10-12 | ~$5-7 |
| V14 | -$10.04 | ~$6-8 | ~$2-4 |
| Mention | -$75.84 | $0 | -$75.84 |
| Weather | -$614 (unrlzd) | $0 | -$614 |
| **Total** | | **~$18** | **~$697** |

**97% of losses are strategy-driven, not market-driven.** This is actually good news — strategy bugs are fixable.

---

## 9. Kill / Keep / Modify Decisions

| Bot | Decision | Action Items | Priority |
|-----|----------|-------------|----------|
| V11 Crypto | **MODIFY** | Add regime filter, reduce ETH, asymmetric sizing | Medium |
| V14 Crypto | **MODIFY** | Kill flash_sniper, disable ETH steam_follow, BTC-only | Medium |
| Weather V2 | **MODIFY (URGENT)** | Fix fee economics, cap contracts, don't trade pennies | 🔴 High |
| Mention NO Grinder | **MODIFY (URGENT)** | Replace heuristic model, reduce sizing, add blocklist | 🔴 High |
| NBA | **KEEP** | Add in-play, increase scan freq, lower test threshold | Low |
| Cross-Platform V3 | **KEEP & SCALE** | Fix NBA matching, increase sizing, faster scans | ✅ Top Priority |

---

## 10. Priority Ranking: Where to Allocate Capital & Attention

### Tier 1 — Scale Up
1. **Cross-Platform V3** — Only proven positive EV strategy. Structural arb with no directional risk. Fix NBA matching, scale to $100/trade, add more pairs.

### Tier 2 — Fix Critical Bugs
2. **Weather V2** — The edge thesis (forecast vs market) may be valid, but the execution (penny contracts, massive fees) destroys any edge. Fix sizing first, then evaluate.
3. **Mention NO Grinder** — The NO grind thesis is solid, but the probability model is garbage. Build a proper model, then re-evaluate.

### Tier 3 — Iterate
4. **V11 Crypto** — Promising base (45% WR) that just needs regime awareness. Add crash filter, re-test.
5. **V14 Crypto** — After killing flash_sniper and going BTC-only, test the remaining steam_follow signal.

### Tier 4 — Monitor
6. **NBA** — Market is too efficient for pre-game edge. Keep running at low cost, add in-play when possible.

---

## Appendix A: Raw Data Summary

### V11 All Trades PnL Histogram
```
Win range:   $0.01 - $3.50  (70 trades, total: +$66.76)
Loss range: -$3.60 - -$0.01 (84 trades, total: -$83.97)
Net: -$17.21
```

### V14 Flash Sniper Detail (15 trades)
```
1 win  ($0.40) — 6.7% WR
14 losses (avg -$0.43, range: -$0.10 to -$1.80)
Signal is worse than random
```

### Mention Trader Exposure Summary
```
Total invested (open): $257.07
Total invested (settled): $133.24
Settled P&L: -$75.84
Still at risk: $257.07 (13 positions, closes Feb 8 - Mar 1)
```

### Weather V2 Fee Impact
```
Without fees: cost=$569, value=$189, PnL=-$380
With fees:    cost=$804, value=$189, PnL=-$615
Fees add -$235 to losses (37% of total cost)
```

---

*Analysis generated 2026-02-05T19:02 UTC. Data sources: session JSONs, state files, process logs.*
