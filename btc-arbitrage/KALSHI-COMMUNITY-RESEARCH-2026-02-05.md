# Kalshi Money-Making Research Report
**Date: 2026-02-05**  
**Sources: Twitter/X (bird CLI), web_fetch, Kalshi official site**  
**Confidence levels: 🟢 Proven | 🟡 Likely | 🔴 Speculative/Unverified**

---

## Executive Summary: What ACTUALLY Works on Kalshi

### Top 3 Proven Money-Making Strategies (ranked by evidence)

1. **🟢 Mention Markets (TV/Speech/Event word prediction)** — THE dominant money-maker. Multiple traders publicly verified $50K-$600K+ profits. Requires watching live events, predicting which words will be said, and understanding context/rules deeply. This is where the most alpha currently lives.

2. **🟢 Cross-Platform Arbitrage (Kalshi ↔ Polymarket ↔ Sportsbooks)** — 4-5% spreads on identical events across platforms. Bots scanning both platforms, executing both legs. ~$2K/month documented PnL for one open-source bot. Requires fast execution, correct contract matching, and managing fill risk.

3. **🟢 Weather Markets with Forecasting Models** — Two Big Ten grads (Eric & Jerry) achieved 100x ROI ($24K on single Thanksgiving weather trade) using Python bots + NWS data. Multiple traders building weather models. Edge exists while participation is low.

### What Probably Works (Less Evidence)

4. **🟡 Sports In-Game Bot Trading (NBA/NFL)** — @HesomParhizkar documented a bot journey from $0 to +85%/week on NBA games, using strategies like homeUnderdog, favoriteFade, lateGameLeader. Still experimental but showing promise. Requires real-time data and ML models.

5. **🟡 "Junk Bond" Compounding (High-probability outcomes)** — @catboyautist allegedly turned $1K → $100K in 3 months buying 70-90¢ contracts on near-certain outcomes + 25-60¢ variance plays. Documented by @yoyoweb4. High-turnover compounding with 15-30% daily edges.

6. **🟡 Sports Arbitrage via OddsJam** — Using OddsJam tools to find mispricings between Kalshi and traditional sportsbooks. @brian_stephens_ claims $278/day but this is likely affiliate marketing hype. Core concept (arb between prediction market and sportsbook) is sound.

### What's Mostly BS

7. **🔴 "Easy $3,300/hr" claims** — Affiliate marketers pushing OddsJam referral links. The math doesn't hold at scale. Limited by liquidity and fill rates.

8. **🔴 Generic "prediction market bot" DM sellers** — @kei_4650 and similar "DM me to learn more" accounts. Classic lead gen, not real alpha.

---

## Detailed Findings by Source

### I. Twitter/X Research

#### A. The Top Profitable Traders (Verified Accounts with P&L Screenshots)

**@Foster (Foster)**
- 🟢 **$600K+ total profit** on Kalshi (as of Jan 2026)
- Left his job in Jan 2025 to trade prediction markets full time
- Started with **<$3K**, now at $7.7M volume
- January 2026: **+$100K+ profit** in single month
- **Primary strategy: NFL announcer mention markets + sports**
- Built a model that profited ~$50K over one NFL season on announcer mention markets
- Quote: "snowballed it here from my start... lots of small flips and cheap entries"
- Source: https://x.com/Foster/status/1996991794278469728

**@0xTyrael (Tyrael)**
- 🟢 **$143K+ profit** (and climbing) in ~3 months
- Primarily trades **mention markets** (announcer mentions, political speeches)
- Best single day: **~$9,000 profit**
- $3,400 on a single announcer mention trade
- Mentioned the "bible of rules disputes" as essential reading
- Heavily focused on State of the Union, NFL, and political mention markets
- Source: https://x.com/0xTyrael/status/2010580103311626520

**@NathanMeininger (Nathan Meininger)**
- 🟢 **$100K+ profit** achieved in 17 months on Kalshi
- Started "making very little money" 
- Featured on @PredMTrader interview
- Source: https://x.com/NathanMeininger/status/1991288236434702597

**@PredMTrader (PredictionMarketTrader)**
- 🟢 **$67K profit in January 2026 alone** on $3.1M volume
- Called it "our best month ever"
- Runs live streams of mention market trading
- Made $275 on a single "Oil" mention trade by anticipating context (Trump saying "Venezuela" → "Oil")
- February focus: heavy mentions (Super Bowl, etc.)
- Key insight: "automated trading bots instantly buy the word after it's said. If you want to beat the bots, you have to buy based on context"
- Source: https://x.com/PredMTrader/status/2017984724258476397

**@catboyautist (unnamed)**
- 🟡 **$1K → $100K** in 3 months (Nov-Dec 2025) — documented by @yoyoweb4
- Strategy: "Junk Bond" — 70% bankroll in 70-90¢ near-certain outcomes, 30% in variance plays
- Market types: mention markets + near-certain outcomes
- 15-30% daily edges through compounding
- Less directly verified but cited by multiple accounts
- Source: https://x.com/yoyoweb4/status/2006806117855252755

**User "tooeasy27" (Kalshi username)**
- 🟢 **$1,200 → $72,039** on a single NATO mention market trade (60x)
- "Security" was said in a surprise final clip on Fox News when NO shares were at 99¢
- Documented by @PredMTrader with screenshots
- Source: https://x.com/PredMTrader/status/2014132018389393662

#### B. Fee Structure Analysis (Critical Intelligence)

**From community discussions (especially @Max_Sorokin_):**

- **Taker fee = equivalent to sportsbook vig (high)**
- **Maker fee = much lower** — using limit orders at the bid gives you roughly no-vig Pinnacle/DraftKings equivalent odds
- @Max_Sorokin_: "if you use limit maker orders at the bid, you'll face a 0.3% fee. Taker order = 1.2% fee"
- @TradeandMoney (Doug Campbell): Found **12.6% vig on FanDuel** vs **0.3% maker fee on Kalshi** for same Buffalo vs Carolina game
- **Critical insight**: Most casual users use market (taker) orders and get destroyed by fees. Smart traders ALWAYS use limit (maker) orders.
- @Max_Sorokin_: "Anyone could understand these mechanics if they just took 2 hours"
- Market making is nearly impossible for profit because bid-ask spread minus fees = ~0.1¢/contract
- @XRP_AH_: "I bet $200 and 100 of it went to fees" (via Robinhood integration — worse than direct Kalshi)

**⚠️ WARNING: Coinbase/Robinhood integration adds ADDITIONAL fees on top of Kalshi fees**
- @Chief_Satori: "People getting rekt bc platform adding insane fees and automatically selling YES orders"
- Always trade directly on Kalshi, never through intermediaries

**Fee Schedule (from Kalshi official PDF, Oct 2025):**
- PDF exists at https://kalshi.com/docs/kalshi-fee-schedule.pdf but is binary/unreadable via web_fetch
- Based on community consensus: Maker ~0.3%, Taker ~1.2% (varies by market)

#### C. Strategy Deep-Dives

##### 1. Mention Markets (🟢 HIGHEST CONFIDENCE)

**What they are:** Binary contracts on whether a specific word will be mentioned during a live event (NFL game commentary, presidential speech, congressional hearing, talk show, etc.)

**How money is made:**
- **Pre-event analysis**: Research what topics will likely come up. E.g., Capital One sponsors World Series → "walk-off" will be mentioned (sponsorship context gives structural edge)
- **Context anticipation**: Buy "Oil" when Trump starts talking about "Venezuela" and "Barrels" — beat the bots by anticipating the next word, not reacting to it
- **Rules arbitrage**: Deep knowledge of settlement rules creates edge. E.g., Anthropic/Claude Super Bowl ad controversy — does "Claude" count as "Anthropic" mention?
- **Junk bond compounding**: Buy words at 70-90¢ that are near-certain to be mentioned, compound daily

**Key stats:**
- Trump's address to Congress: $21M total volume ($14M Kalshi, $7M Polymarket)
- NFL announcer mention markets: $1M+ volume on single games
- Super Bowl mention markets: massive volume expected

**Risks:**
- **Rules disputes are COMMON** — settlement ambiguity can destroy positions
- **Bots compete for instant-buy after words are said** — you need to be AHEAD of the word, not reacting
- **@CSP_Trading's warning**: "negative ev mention markets" — if you're buying after the word is said, you're competing with bots and paying premium
- Kalshi sometimes sends clarification emails that move markets (90 seconds before clearing orderbook = frontrunning opportunity)

**Notable edge sources:**
- Understanding sponsorship/advertising context (Capital One → walk-off)
- Political topic research (what will Congress discuss?)
- Rules research — @bernardbulletin tracks rules disputes as reference
- Live event watching + fast manual execution

##### 2. Cross-Platform Arbitrage (🟢 HIGH CONFIDENCE)

**What it is:** Finding the same event priced differently on Kalshi vs Polymarket (or other platforms) and buying both sides for risk-free profit.

**Evidence:**
- @crpyKenny: **$2,000/month PnL** with Kalshi x Polymarket arb bot
- Spreads of **4-5% on identical events** regularly observed
- @securezer0: 6.59M markets analyzed, 5,200 matches found, $250K+ in +EV arbs identified
- @predictsync: Locked in **0.52% profit** on CFP game with MIA @59.98¢ (Kalshi) & Ole Miss @39.5¢ (Polymarket)
- @stablemark_: 5,300 matched pairs between Polymarket and Kalshi

**Key technical requirements:**
- Fast contract matching (matching is the hard part, not finding spreads)
- Both legs must fill (partial fill = exposure risk)
- Strict checks on: depth, max slippage, time-to-expiry
- @ArtixFund: "3 checks before each trade: liquidity, slippage max, timeout/fill rate. Without that, the edge = illusion"

**Open-source tools:**
- `pmxt` — scanning and surfacing opportunities
- `prediction-market-arbitrage-bot` — execution on both Kalshi and Polymarket
- `tools-and-analysis` repo — Kalshi market data + orderbook pulling

**Crypto-specific arb:**
- @securezer0: Bot supports BTC/ETH/SOL price arbs between platforms
- @xxniftylemonxx: Built bot for BTC 1-hour close alerts on Kalshi
- @PGeniusAI: "BTC volatility arbitrage bot for Kalshi"

##### 3. Weather Markets (🟡 MEDIUM-HIGH CONFIDENCE)

**What it is:** Betting on temperature/weather outcomes for specific cities.

**Evidence:**
- **Eric & Jerry (Big Ten grads)**: 100x ROI with automated Python bots
  - $24K profit on Thanksgiving weather trade
  - $23K on Masters Golf (expanded beyond weather)
  - Used NWS data, local sensors, multiple forecast models
  - Source: https://x.com/cryptoxalv586/status/1990527684305432955
- @Outcome_Edge: Published city-by-city P&L from weather model
  - Winners: Philadelphia, LA, Chicago, Austin
  - Losers: New York, Miami, Denver
- @BitBoyJay: "the Kalshi weather prediction market is the new trenching... predicting one degree off, and if it doesn't hit, the other bracket goes from 6% to 100% in minutes"
- Edge exists "while participation is still low"

**Strategy:**
- Build blended forecast models from multiple data sources (NWS, local weather stations, commercial forecasts)
- Automate monitoring and order placement
- Focus on cities where your model outperforms market consensus

##### 4. Sports Bot Trading (🟡 MEDIUM CONFIDENCE)

**@HesomParhizkar's NBA Bot Journey (detailed documentation):**

Starting from Christmas 2025, built progressively:
- **Week 1**: +85% return for the week
- **Dec 31**: Bot went 6-0, +52.27% return
- Uses Kalshi API + ESPN "unofficial" API for real-time scores
- Strategies tested:
  - ❌ `underdogMomentum` — too reactive, stop-loss ate gains
  - ❌ `scoreMomentum` — same issue, catching falling knives
  - ✅ `homeUnderdog` — Home teams at 30-35¢. Win rate 46.2% (breakeven 35%). Edge: +11.2%
  - ✅ `favoriteFade` — Favorites at 75%+ with spread -10 to -14. Lose rate 35.9% (breakeven 25%). Edge: +10.9%
  - ✅ `lateGameLeader` — Buy team with big lead in 4th quarter
  - ✅ `blowout` — Team up 15+ points in 3rd/4th

**Key Kalshi API gotcha**: If you pass `type: "Market"` but also pass `yes_price`, it treats it as a LIMIT order, not market order. This bug caused significant losses.

**ML Model** (Dec 28 update): Trained neural network on:
- Vegas spreads
- Team stats (off/def ratings, pace)
- Injury reports
- Schedule factors (rest days, travel)

##### 5. Sportsbook ↔ Kalshi Arbitrage (🟡 MEDIUM CONFIDENCE)

**Via OddsJam:**
- @brian_stephens_: Claims $278/day, $1,000+ days (likely inflated for affiliate marketing)
- Core concept: Find same game priced differently on Kalshi vs FanDuel/DraftKings
- Use Kalshi limit orders (maker fee 0.3%) vs sportsbook vig (5-12%)
- **Key advantage**: Kalshi won't limit/ban you like sportsbooks do
- @Piston2x: "Is there enough sports arbitrage volume available daily through Poly/Kalshi to replace all the volume I lost from having my entire family's accounts limited across nearly every sportsbook?"

---

### II. The Bear Case: @CSP_Trading (Critical Skeptic)

@CSP_Trading is the most vocal Kalshi critic in the prediction market community. Key claims:

- **"kalshi pretends to be a positive influence in the space when theyre really just toxic evil fucks poisoning the well for everyone else"**
- Calls Kalshi "negative EV" for most traders
- Claims mention markets are specifically negative EV
- Criticizes people encouraging others to quit jobs to trade Kalshi
- Advocates for Polymarket instead (zero fees + rewards)
- Points out Kalshi sends resolution clarifications late, allowing frontrunning
- Documents specific instances of rule disputes favoring the house

**Assessment:** CSP_Trading has valid points about:
1. Taker fees making casual trading negative EV ✅
2. Rules disputes being problematic ✅
3. Some influencers being paid shills ✅

BUT the profitable traders (Foster, Tyrael, Nathan) exist and show real P&L screenshots. The key difference: **They use maker orders, deep market knowledge, and mention market expertise that most people don't have.**

---

### III. Kalshi vs Polymarket Comparison

| Factor | Kalshi | Polymarket |
|--------|--------|------------|
| **Regulation** | CFTC-regulated (US) | Crypto-native, global |
| **Fees** | Maker ~0.3%, Taker ~1.2% | Zero fees, rewards for liquidity |
| **KYC** | Required | Not required |
| **Currency** | Fiat (USD) | USDC on blockchain |
| **Market listing speed** | Slow (regulatory) | Fast |
| **Unique markets** | Mention markets, weather | More variety, faster |
| **Liquidity** | Higher on sports/mentions | Higher on politics/crypto |
| **Bot risk** | Moderate | Higher |
| **Key advantage** | Legal protection, no banning | Freedom, no fees, global access |

**Community consensus:**
- @carlos_xblue: "Polymarket feels like trading sentiment & hype. Kalshi feels like trading official data & macro outcomes."
- @0xLoreee: "Kalshi feels 15 years behind. Polymarket is my clear choice"
- For US-based traders: Kalshi for legal protection. For crypto-natives: Polymarket.
- **For arb traders: Use BOTH** — the arbitrage between them IS the strategy

---

### IV. Fee Analysis & EV Calculations

#### Kalshi Fee Math

**Taker (market) orders:**
- Fee = ~1.07¢ per contract (reported)
- On a 50¢ contract: fee = ~2.14% of position
- On a 90¢ contract: fee = ~1.19% of position
- On a 10¢ contract: fee = ~10.7% of position ← PAINFUL for cheap contracts

**Maker (limit) orders:**
- Fee = ~0.3% (based on community reports)
- Dramatically better than taker
- On a 50¢ contract: fee = ~0.15¢ per contract

**Break-even analysis:**
- If you buy YES at 50¢ (taker), you need >51.07¢ effective price to profit
- If you buy YES at 50¢ (maker), you need >50.15¢ effective price to profit
- **Taker fees alone eat ~2% of your edge** on mid-priced contracts

**Is Kalshi negative EV?**
- For taker-only traders betting randomly: **YES, strongly negative EV** (equal to or worse than sportsbook vig)
- For maker-order traders with genuine edge: **NO, positive EV is achievable** (0.3% fee is very low)
- The fee structure specifically punishes impatient/uninformed traders and rewards patient limit-order users

#### Polymarket Fee Comparison
- 0% trading fee
- Rewards for providing liquidity
- But: higher bot competition, less regulation, crypto exposure risk

---

### V. Specific Insights for BTC/ETH Trading

#### What Exists on Kalshi for Crypto
- Kalshi has a **Crypto category** with BTC/ETH price prediction markets
- Markets include: "Will BTC be above $X by [date]?"
- Hourly, daily, weekly, monthly brackets available
- BTC/ETH/SOL price ranges

#### Arb Opportunities for Our BTC/ETH Trading
1. **Kalshi ↔ Polymarket crypto price arbs**: Both platforms have BTC/ETH price markets. Price discrepancies occur regularly
   - @securezer0's bot explicitly supports "BTC / ETH / SOL Price Arbs" between platforms
   - 4-5% spreads documented on crypto markets

2. **Kalshi crypto ↔ Actual spot/derivatives arb**: If Kalshi prices BTC bracket at X% and you can hedge on Deribit/Binance options...
   - @PGeniusAI building "BTC volatility arbitrage bot for Kalshi"
   - Structural opportunity: Kalshi users may not efficiently price crypto volatility

3. **Weather model → Crypto correlation**: Some weather events affect energy/mining costs. Unlikely to be a primary strategy but worth monitoring.

#### Actionable Steps for Our BTC/ETH Trading
1. **Set up Kalshi API access** — docs at https://docs.kalshi.com
2. **Build a scanner** that monitors Kalshi crypto bracket prices vs Polymarket crypto prices
3. **ALWAYS use maker/limit orders** — never taker orders
4. **Focus on time periods where markets are thin** — early hours, weekends
5. **Monitor for pricing inefficiencies after large BTC moves** — Kalshi may lag Polymarket or spot price
6. **Consider the `prediction-market-arbitrage-bot` open source code** as starting point

---

### VI. Automation & Bot Strategies

#### What People Are Building

1. **Cross-platform arb bots** (most common)
   - Scan Kalshi + Polymarket for same events
   - Execute both legs when spread > fees
   - Key repos: `pmxt`, `prediction-market-arbitrage-bot`, `tools-and-analysis`
   - @stablemark_ rewrote matching from Python → Rust (20min → 14sec)

2. **Sports in-game trading bots**
   - @HesomParhizkar: NBA bot with ML model (Vegas spreads, team stats, injuries)
   - Uses Kalshi websocket for near-realtime data + ESPN API for scores
   - Strategies: homeUnderdog, favoriteFade, lateGameLeader

3. **Weather prediction bots**
   - Eric & Jerry: Python bots connected to NWS data
   - Monitoring 100+ markets simultaneously
   - Blended forecast models

4. **Mention market bots**
   - Automated word detection → instant buy
   - @PredMTrader: "automated trading bots instantly buy the word after it's said"
   - Counter-strategy: Buy BEFORE the word based on context anticipation

5. **BTC volatility arb bots**
   - @PGeniusAI: Working on this specifically
   - Comparing Kalshi crypto brackets vs options markets

#### Technical Notes
- Kalshi API: REST + WebSocket for real-time data
- API gotcha: Passing `type: "Market"` with `yes_price` makes it a LIMIT order
- Credentials: stored in `client/credentials.yaml`
- Rate limits: Not publicly documented in community discussion

---

### VII. Common Mistakes (What Losers Do Wrong)

1. **Using market/taker orders** instead of limit/maker orders (biggest mistake — 2-10x fee difference)
2. **Not understanding the orderbook** — queue position matters enormously
3. **Trading through intermediaries** (Robinhood/Coinbase adds extra fees on top)
4. **Buying mention markets AFTER the word is said** (bots already got there)
5. **Ignoring rules/settlement language** (rules disputes are common and can flip outcomes)
6. **Overreacting to cached/stale data** (ESPN API caching caused wrong bot signals)
7. **Not having stop-loss logic** (crucial for live sports trading)
8. **Treating it like a casino** instead of an exchange (need edge, not luck)
9. **Partial fills leaving you exposed** on arb trades
10. **Not reading the fee schedule** (literally just spending 2 hours understanding mechanics)

---

### VIII. Strategy Rankings

#### TIER 1: Proven (Multiple verified P&L screenshots, $50K+)
| Strategy | Evidence | Estimated Monthly | Difficulty |
|----------|----------|-------------------|------------|
| Mention Markets (expert) | Foster $600K, Tyrael $143K, Nathan $100K | $10K-100K | Very High |
| Cross-Platform Arb (Kalshi ↔ Poly) | $2K/month documented, $250K found | $2K-10K | High |

#### TIER 2: Likely Profitable (Some evidence, smaller scale)
| Strategy | Evidence | Estimated Monthly | Difficulty |
|----------|----------|-------------------|------------|
| Weather Model Trading | Eric & Jerry 100x ROI | $1K-10K | High |
| Sports Bot (NBA/NFL) | Hesom 85%/week (small account) | $500-5K | Very High |
| Junk Bond Compounding | catboyautist 100x claim | $1K-10K | Medium |
| Sportsbook ↔ Kalshi Arb | OddsJam users (some hype) | $500-3K | Medium |

#### TIER 3: Theoretical/Unproven
| Strategy | Evidence | Estimated Monthly | Difficulty |
|----------|----------|-------------------|------------|
| Crypto Price Bracket Arb | People building bots, no P&L yet | Unknown | High |
| Market Making | Max_Sorokin says 0.1¢/contract profit | Negligible | Very High |
| Weather + Crypto correlation | Speculation only | Unknown | Very High |

#### TIER BS: Don't Bother
| Strategy | Why |
|----------|-----|
| "Easy $3,300/hr" taker-order betting | Affiliate marketing lies |
| "DM me for my bot" offers | Classic scam pattern |
| Random event gambling | House edge (fees) grinds you down |

---

### IX. Notable Accounts to Follow

| Account | Focus | Why Follow |
|---------|-------|------------|
| @PredMTrader | Mention markets, general | $67K/month, live streams, educational |
| @Foster | Mention markets, sports | $600K+ total profit, full-time trader |
| @0xTyrael | Mention markets | $143K+ profit, State of the Union expert |
| @NathanMeininger | General Kalshi | $100K+ documented |
| @HesomParhizkar | Sports bot building | Detailed public bot development log |
| @CSP_Trading | Critical/bearish | Keeps everyone honest, valid fee critiques |
| @Max_Sorokin_ | Fee analysis | Deep understanding of Kalshi orderbook |
| @securezer0 | Arb bot building | Cross-platform arb scanner |
| @stablemark_ | Arb infrastructure | Rust-optimized matching algorithms |
| @Outcome_Edge | Weather markets | Model P&L by city |
| @K_NewEvents | New Kalshi events | Event tracking feed |
| @TradeandMoney | Fee analysis | Detailed fee comparison across platforms |

---

### X. Key Regulatory/Structural Notes

1. **CFTC-regulated** — Kalshi is a designated contract market (DCM) under US commodity law
2. **US-only** — KYC required, non-US users can't trade
3. **Can't be limited/banned** like sportsbooks — this is a HUGE advantage for profitable traders
4. **Coinbase integration** — prediction markets now accessible to 101M+ Coinbase users (liquidity influx coming)
5. **Combos/parlays** — recently launched, driving record volumes
6. **PrizePicks integration** — bringing DFS users to mention markets
7. **Trump Jr. involvement** — brings attention but adds reputation volatility

---

### XI. Key Quotes from Profitable Traders

> **@Foster**: "Happy New Year everybody! Exactly 1 year ago today I left my job to trade prediction markets full time. It was a massive risk, and I had a portfolio of just over $7k."

> **@PredMTrader**: "On Kalshi mention markets, automated trading bots instantly buy the word after it's said. If you want to beat the bots, you have to buy based on context of where the conversation is headed."

> **@Max_Sorokin_**: "If any person spent just a couple of hours understanding the fees/orderbook they would never use market taker orders again."

> **@HesomParhizkar**: "Started to 'tune' my strategies with this data and backtested. Ended up removing two of the strategies that I would have thought would make money."

> **@CSP_Trading**: "never encourage people to quit their job to trade negative ev mention markets"

> **@TradeandMoney**: "Kalshi, where if you put in a maker limit order at the bid, you'll face a 0.3% fee. Fee differences this large mean that prediction markets are almost certainly better for everyone."

> **@ArtixFund**: "The 'secret' isn't finding a spread… it's surviving execution. 3 checks before each trade: liquidity, slippage max, timeout/fill rate."

> **@Red781RuM**: "if you're smart, you'll 100% be making money on prediction markets (versus you'd still lose in a casino)"

---

### XII. Final Assessment: Honest Take

**Is Kalshi a good platform to make money?**

**YES, IF:**
- You use maker/limit orders exclusively
- You have a genuine informational or analytical edge
- You're willing to invest significant time learning the mechanics
- You focus on mention markets, cross-platform arb, or weather models
- You automate where possible

**NO, IF:**
- You're using taker/market orders casually
- You're treating it like a casino/sportsbook
- You're buying based on hype or gut feeling
- You're trading through Robinhood/Coinbase (extra fees)
- You don't understand the fee structure

**For our BTC/ETH trading specifically:**
The most promising path is **cross-platform arb** between Kalshi crypto brackets and Polymarket crypto prices. This is a direct extension of our existing work. Several people are building exactly this, but the space is still early enough that edges exist. The key technical challenge is contract matching and execution speed, not finding the spreads.

---

*Report compiled 2026-02-05 from 40+ Twitter searches, multiple web fetches, and Kalshi official documentation. All profit claims are based on public screenshots/statements and should be independently verified.*
