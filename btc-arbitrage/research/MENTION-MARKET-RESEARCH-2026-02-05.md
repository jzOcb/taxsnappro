# Mention Market Research Report
**Date:** 2026-02-05
**Status:** Comprehensive Deep Dive

---

## Executive Summary

Mention markets are one of the fastest-growing and most active categories on both Polymarket and Kalshi. They allow traders to bet on whether specific words/phrases will be said during speeches, earnings calls, press briefings, sports broadcasts, and more. The Trump weekly mention market alone has **$3.17M volume** this week (Feb 8). Kalshi's EA earnings mention market hit **$4.06M**. The total addressable market across both platforms is likely **$10-20M+ per week** in volume.

Key insight: **YES is structurally overpriced** in most mention markets. The default winning strategy is selling YES / buying NO on unlikely mentions, while selectively going YES on high-probability mentions backed by transcript analysis.

---

## 1. The Foster Story ($600K+)

### What We Found
Could not locate a specific public article detailing "Foster making $600K on mention markets." This may refer to:
- A Polymarket username/wallet tracked on PolymarketAnalytics.com
- A reference from a podcast, Twitter Space, or Discord conversation
- Part of the NYT Jan 22 article (paywalled) which discussed prediction market traders making millions

### Context from NYT (Jan 22, 2026)
The New York Times article "Betting on prediction markets is their job. They make millions" specifically mentioned:
> "Both Kalshi and Polymarket, the two big prediction market platforms, were offering yes-or-no-style 'mention markets' asking users to bet on whether the president would say more than a dozen [words]..."

### Top Known Mention Market Whales
From Brave search / polymarketwhale strategy post, these top traders are known:
- **ImJustKen:** +$2.4M total PnL (diverse bets including mention markets)
- **SwissMiss:** +$2.8M total PnL
- **fengdubiying:** +$2.9M total PnL

**Action item:** Search PolymarketAnalytics.com for "foster" username or track wallets with high mention-market activity to identify this trader.

---

## 2. Active Mention Markets RIGHT NOW

### Polymarket (Live as of Feb 5, 2026)

| Market | Volume | End Date | Notes |
|--------|--------|----------|-------|
| **What will Trump say this week (Feb 8)?** | **$3,172,574** | Feb 8 | Flagship weekly market |
| What will be said during the Pro Football Championship? | $61,422 | Feb 8 | Super Bowl LX |
| What will Trump say during State of the Union? | $57,401 | Feb 24 | SOTU - huge upcoming opportunity |
| Who will Trump name during SOTU? | $54,988 | Feb 24 | People-specific |
| What places will Trump mention during SOTU? | $31,350 | Feb 24 | Geographic mentions |
| What will Trump say in February? | $43,050 | Feb 28 | Monthly aggregate |
| What nicknames will Trump say by Feb 28? | NEW | TBD | Just launched |
| What will Amazon say during earnings? | $21,375 | Feb 5 | Tonight! |
| What will Coinbase say during earnings? | $40,955 | Feb 20 | |
| What will Nebius say during earnings? | $19,652 | Feb 19 | |
| What will Karoline Leavitt say at WH press briefing? | $16,049 | Feb 6 | Tomorrow |
| All-In Podcast (Jan 23) | $324,916 | Past | Example of non-political |
| What will Reddit say during earnings? | $3,485 | Feb 5 | Tonight |
| What will Roblox say during earnings? | $475 | Feb 5 | Low volume |

### Kalshi (Live as of Feb 5, 2026)

| Market | Volume | Notes |
|--------|--------|-------|
| **EA Earnings Call Mentions** | **$4,064,112** | Biggest on Kalshi! |
| Pro Football Championship (Super Bowl) | $872,730 | 36 sub-markets |
| Mikie Sherrill MSNBC Interview | $561,853 | 12 sub-markets |
| Trump SOTU (words) | $363,394 | 27 sub-markets |
| Trump National Prayer Breakfast | $154,098 | 21 sub-markets |
| Trump Nicknames before April | $149,350 | 15 sub-markets |
| WH Press Briefing | $147,175 | 25 sub-markets |
| Trump SOTU (people named) | $100,715 | 34 sub-markets |
| Trump weekly (Feb 9) | $96,368 | 16 sub-markets |
| Trump SOTU (places) | $86,985 | 33 sub-markets |
| Trump monthly (Feb) | $63,021 | 25 sub-markets |
| Green Day says MAGA at Super Bowl? | $57,018 | Single yes/no |
| MrBeast YouTube video | $56,575 | 15 sub-markets |
| Amazon earnings | $49,741 | 16 sub-markets |
| Nebius earnings | $20,260 | 11 sub-markets |
| Reddit earnings | $17,361 | 11 sub-markets |
| Coinbase earnings | $16,611 | 14 sub-markets |
| KKR earnings | $8,439 | 9 sub-markets |
| Trump Announcement (misc) | $4,452 | 16 sub-markets |
| NBA game mentions (various) | $1-4K each | Multiple games |
| Governor State of State | $681 | Low volume |

### Key Observations
1. **Trump is king** — his weekly mention markets generate more volume than everything else combined
2. **Earnings calls** are a growing category (EA at $4M is massive)
3. **Sports broadcasts** (Super Bowl) are high-volume
4. **Kalshi has more variety** — NBA games, governors, specific TV interviews
5. **SOTU on Feb 24 will be ENORMOUS** — likely $5-10M+ combined volume across both platforms

---

## 3. Top 3 Strategies (Ranked by Feasibility)

### Strategy #1: "Default NO" on Overpriced YES Mentions ⭐⭐⭐⭐⭐
**Feasibility: HIGH | Expected Edge: 5-15% | Capital needed: $500-5000**

**Core Insight:** YES is structurally overpriced in mention markets because:
- Retail traders are attracted to underdog bets (cheap YES = lottery ticket feel)
- Emotional/wishful thinking inflates YES prices on exciting/funny words
- Trump in particular: people in crypto think he says "crypto" often. He doesn't.

**Execution:**
1. Analyze historical transcripts (use MentionMarkets.com or build own corpus)
2. Identify words Trump has NEVER or RARELY said in similar contexts
3. Buy NO at 85-95¢ for guaranteed-resolution words
4. Target: Words with YES at 10-25¢ that historically have 0-5% mention rate

**Example from Feb 8 market data:**
- "Autopen / Auto Pen" resolved YES with $1.17M volume — this was driven by a specific news event (auto-pen controversy)
- "Submarine / Helicopter" resolved YES with $9.7K volume
- "Cuba / Cigar" resolved YES with $16.8K volume

**Key Risk:** Black swan events (Trump goes off script, news breaks making unlikely word very likely)

### Strategy #2: Real-Time Speech Monitoring + Speed Trading ⭐⭐⭐⭐
**Feasibility: MEDIUM-HIGH | Expected Edge: 20-50% per event | Capital needed: $1000-10000**

**Core Insight:** From strategy research: "First 30 seconds decide the trade." When Trump says a word during a live speech, there's a window to buy YES before the market fully reprices.

**Execution:**
1. Set up real-time speech-to-text monitoring (Whisper API on live stream)
2. Pre-load list of all active mention market words
3. When word is detected → immediately submit market buy for YES at current ask
4. Resolution happens automatically after confirmation

**Infrastructure Needed:**
- YouTube/C-SPAN live stream capture
- Real-time speech-to-text (OpenAI Whisper, Google STT)
- Pre-configured Polymarket/Kalshi API order submission
- Latency target: <5 seconds from word spoken to order submitted

**Example Scenario:**
- Trump weekly market has 15 sub-markets at various YES prices
- Speech starts, within first 5 minutes Trump says "tremendous"
- Your bot detects it, buys YES at current market price (say 75¢)
- Market reprices to 95-99¢ within minutes
- Profit: ~25% on capital deployed

**Key Risk:** 
- Latency competition (others have same setup)
- Audio quality issues / false positives
- Market may already be near 99¢ for obvious words

### Strategy #3: Pre-Event Positioning via Transcript Analysis ⭐⭐⭐⭐
**Feasibility: HIGH | Expected Edge: 10-30% | Capital needed: $2000-10000**

**Core Insight:** Trump has predictable speech patterns. By analyzing historical transcripts, you can identify which words he uses in which contexts with high probability.

**Execution:**
1. Build corpus of all Trump speeches (A River Whale Substack has started this)
2. For each upcoming event type, calculate word frequency distributions
3. Buy YES early (when market opens) for high-probability mentions
4. Buy NO for words he never uses in that context
5. Sell positions as event approaches and prices converge

**Example:**
- Trump 100-Day Rally: Polymarket had 77% for "China 7+ times" and 82% for "eggs"
- Historical analysis would show China mentioned in 95%+ of economic speeches
- Buy YES early when market is at 70%, sell at 85% before speech even starts

**Tools:**
- MentionMarkets.com ($199/mo) — has all transcripts searchable
- MentionMetrix — alternative transcript tool
- Build own: scrape transcripts from Rev.com, C-SPAN, White House transcripts

---

## 4. Data Infrastructure Requirements

### Must-Have Monitoring Sources

#### A. Trump Verbal Mentions (Primary)
| Source | Method | Latency | Notes |
|--------|--------|---------|-------|
| White House YouTube | YouTube API / yt-dlp live | Real-time | Official broadcasts |
| C-SPAN | Live stream scrape | Real-time | Uninterrupted coverage |
| Fox News / CNN streams | IPTV / streaming service | Real-time | Rally coverage |
| Rumble / RSBN | Stream capture | Real-time | Trump rally specific |
| Rev.com transcripts | API / scrape | 15-30 min delay | Post-event verification |
| White House transcripts | whitehouse.gov scrape | Hours delay | Official record |

#### B. Trump Written Posts (for context, not resolution)
- Truth Social: No official API. Scrapers exist (truthsocial-scraper on GitHub)
- Written posts do NOT count for Polymarket mention resolution but predict topics

#### C. White House Press Briefings
- Schedule: whitehouse.gov/briefing-room
- Usually 12:00-2:00 PM ET weekdays
- Live stream on YouTube (White House channel)
- Karoline Leavitt mention markets are recurring

#### D. Congressional Hearings
- senate.gov / house.gov committee schedules
- C-SPAN live coverage
- For future expansion (not current focus)

#### E. Earnings Calls
- Company IR pages for schedules
- Live audio feeds from earnings call services
- Seeking Alpha / The Motley Fool provide transcripts
- Kalshi has major volume here (EA: $4M!)

#### F. Sports Broadcasts
- NBC official broadcast for Super Bowl
- ESPN/TNT for NBA games
- Need broadcast audio capture + STT

#### G. Real-Time Monitoring Tools We Already Have
- **bird CLI** (Twitter/X monitoring) — track Trump posts, news, insider-hunters
- Server infrastructure for running speech-to-text models
- Python for API integration

### Speech-to-Text Pipeline Architecture

```
Live Stream → Audio Capture → Whisper/STT → Word Detection → API Order
   ↓              ↓              ↓              ↓              ↓
YouTube       ffmpeg         OpenAI API     Keyword Match   Polymarket/
C-SPAN        yt-dlp         Whisper        vs Active       Kalshi API
Fox           stream         (local or      Markets
              capture        cloud)
```

**Target Latency Budget:**
- Stream delay: 5-15 seconds (inherent)
- Audio processing: 1-3 seconds (with streaming Whisper)
- Keyword matching: <100ms
- API order submission: 200-500ms
- **Total: 7-20 seconds from word spoken to order placed**

---

## 5. Speed-to-Market Analysis

### How Fast Do Mention Markets Move?

**From research data:**
- "First 30 seconds decide the trade" — polymarketwhale strategy
- When Trump says "Autopen" → $1.17M volume market resolved almost instantly
- White House briefing at 64:30 (vs 65min threshold) → "50x returns in seconds"

### Speed Tiers

| Tier | Latency | Who | Edge |
|------|---------|-----|------|
| **Tier 1: Insiders** | Pre-event | WH staff, speechwriters | Illegal but exists |
| **Tier 2: Live monitors** | 5-20 sec | Bots watching live stream | High edge on first detection |
| **Tier 3: Social media** | 30-120 sec | Twitter watchers, clip posters | Moderate edge |
| **Tier 4: Retail** | 5-30 min | Manual Polymarket users | Low/no edge |

### Key Finding: Mention Markets Are Slower Than Crypto
Unlike HFT in equities or crypto, prediction markets have:
- Lower liquidity → bigger spread → more edge for speed
- No institutional HFT (yet)
- Manual resolution process creates delay
- Retail-heavy participant base moves slowly

**This means there IS alpha in speed** — but the window is 30 seconds to 5 minutes, not milliseconds.

### Order Book Dynamics
From the polymarketwhale article:
> "If Trump during the speech mentions the word 'Hottest', people will open a limit order at 99c to grab all the available liquidity since it's an already decided outcome and make risk-free some small profit."

This means:
1. When a word IS said → race to buy YES at anything below 99¢
2. When a word is NOT said (event ends) → NO resolves to $1
3. The edge is in being FIRST to detect the mention

---

## 6. Beyond Trump: Other Mention/Event Markets

### Currently Active Non-Trump Mention Markets

| Category | Examples | Platform | Volume |
|----------|----------|----------|--------|
| **Earnings Calls** | EA, Amazon, Coinbase, Reddit, KKR, Nebius, Roblox, ON Semi, Microchip Tech | Both | $100K-$4M+ |
| **Sports Broadcasts** | Super Bowl LX announcer mentions, NBA game commentary | Both | $1K-$900K |
| **Press Briefings** | Karoline Leavitt WH briefings | Both | $16K-$147K |
| **YouTube/Podcasts** | MrBeast videos, All-In Podcast | Both | $57K-$325K |
| **Celebrity/Public Figures** | Green Day at Super Bowl, Governors | Kalshi | $57K+ |
| **TV Interviews** | Mikie Sherrill MSNBC | Kalshi | $562K |

### High-Potential Future Categories
- **Fed Chair Powell** — FOMC press conferences (rate decisions)
- **Elon Musk** — tweets, Tesla earnings (Polymarket has "Elon Tracker" Telegram bot)
- **State of the Union** — Feb 24 will be a massive event across all platforms
- **Presidential Debates** (future cycles)
- **Supreme Court decisions** — announcement day markets
- **Major tech CEO keynotes** — Apple WWDC, Google I/O, etc.

---

## 7. Tools & Ecosystem

### Paid Analytics Tools

| Tool | Price | What It Does |
|------|-------|-------------|
| **MentionMarkets.com** | $199/mo | #1 transcript search tool. Covers FOMC, Trump speeches, WH briefings, earnings calls. Client-side search (private). |
| **MentionMetrix** | Unknown | Historical keyword analysis, trend charts, contextual excerpts |
| **Mention Markets Demo** | Free | Limited demo at demo.mentionmarkets.com |

### Free Tools

| Tool | What It Does |
|------|-------------|
| **PolyScope** | Free real-time monitoring, trending markets, odds changes |
| **Polymarket Analytics** | Trader leaderboard, whale tracking, every 5 min updates |
| **A River Whale Substack** | Free Trump speech transcripts + analysis |
| **Prediedge** | Whale tracking, insider activity detection |
| **EventWaves** | High-edge market identification |
| **Wandly** | Calendar-based event tracking for both platforms |
| **Polytrend** | Whale tracking + upcoming autonomous trading |
| **Polymarket Elon Tracker** | Telegram bot for Elon tweet count markets |
| **future fun** | Edge Score rankings for traders |

### API Access
- **Polymarket:** `gamma-api.polymarket.com` for market data (public, no auth needed for reads)
- **Kalshi:** `docs.kalshi.com` — official API with real-time data and trade execution
- Both support programmatic trading

### Key Tool for Us: Build vs Buy
**Recommendation: Build our own transcript analysis tool**
- Cost of MentionMarkets.com: $199/mo = $2,388/year
- Building equivalent: ~1-2 days of development
- Advantage: Custom real-time monitoring, integration with our trading bot
- Use Rev.com API, Whisper local, or White House transcript scraping

---

## 8. Detailed Strategy Playbook

### 8.1 The "NO Grinder" (Low-Risk, Steady Returns)

**Setup:**
1. For each new mention market, analyze all sub-markets
2. Identify words with YES at 5-20¢ that Trump has NEVER said in similar contexts
3. Buy NO at 80-95¢ for these words
4. Wait for event to end → collect $1 per NO share

**Expected Returns:**
- Buy NO at 85¢ → Collect $1 → 17.6% return per event
- Buy NO at 90¢ → Collect $1 → 11.1% return per event
- Buy NO at 95¢ → Collect $1 → 5.3% return per event

**Risk Management:**
- Never put >10% of bankroll on single sub-market
- Diversify across 5-10 NO positions per event
- Set stop-loss: if YES rises above 50¢, exit NO position

### 8.2 The "Speed Trader" (High-Risk, High-Reward)

**Setup:**
1. Before each Trump speech, set up real-time STT monitoring
2. Pre-load all active mention market sub-markets
3. When word is detected, immediately buy YES
4. Hold until resolution

**Expected Returns:**
- Buy YES at 60¢ when word detected → Collect $1 → 66.7% return
- Buy YES at 80¢ when word detected → Collect $1 → 25% return
- Need speed advantage over other monitors

### 8.3 The "Transcript Analyst" (Medium-Risk, Informed)

**Setup:**
1. Build historical transcript corpus (Trump speeches, earnings calls, etc.)
2. Calculate base rates for each word across different event types
3. Before market opens, generate probability estimates
4. Buy YES where market price < your estimate; buy NO where market price > your estimate

**Expected Returns:**
- Depends on quality of analysis
- Edge of 5-15% per market is realistic
- Compound across many sub-markets per event

---

## 9. Implementation Plan

### Phase 1: Foundation (Week 1)
- [ ] Set up Polymarket and Kalshi API access
- [ ] Build market data scraper for both platforms
- [ ] Create mention market tracker (aggregate all active markets)
- [ ] Collect historical Trump speech transcripts (A River Whale + our own)

### Phase 2: Analytics (Week 2)
- [ ] Build transcript analysis tool (word frequency by event type)
- [ ] Create probability estimator for each word in each context
- [ ] Backtest against resolved mention markets (compare our estimates vs actual outcomes)
- [ ] Build dashboards for monitoring active markets + our positions

### Phase 3: Real-Time Monitoring (Week 3)
- [ ] Set up YouTube/C-SPAN live stream capture pipeline
- [ ] Deploy Whisper-based speech-to-text (local GPU or cloud)
- [ ] Build keyword detection + alert system
- [ ] Integrate with trading API for semi-automated execution

### Phase 4: Automation (Week 4)
- [ ] Build fully automated speed-trading bot
- [ ] Implement risk management (position sizing, stop-losses)
- [ ] Deploy monitoring for earnings calls, press briefings
- [ ] Launch with small capital ($500-1000) for testing

### Phase 5: Scale (Month 2+)
- [ ] Increase capital allocation based on proven edge
- [ ] Expand to earnings calls (Kalshi EA market was $4M!)
- [ ] Add sports broadcast monitoring (Super Bowl alone = $900K+)
- [ ] Build multi-platform arbitrage (same mention market on Polymarket vs Kalshi)

### Immediate Opportunities (This Week!)
1. **Trump Feb 8 market** — $3.17M volume, many sub-markets still open
2. **Super Bowl LX (Feb 8)** — $61K (PM) + $873K (Kalshi)
3. **Amazon earnings (Tonight Feb 5)** — $21K (PM) + $50K (Kalshi)
4. **Reddit earnings (Tonight Feb 5)** — $3.5K (PM) + $17K (Kalshi)
5. **WH Press Briefing (Feb 6)** — $16K (PM) + $147K (Kalshi)
6. **Green Day says MAGA at Super Bowl?** — $57K (Kalshi) — fun market!
7. **Trump SOTU (Feb 24)** — Early positioning opportunity, $57K+ already

---

## 10. Risk Assessment

### Risk 1: Resolution Ambiguity ⚠️ HIGH
**Problem:** "What counts as a mention?" is often subjective
- Compound words: Does "killjoy" count for "joy"? (Yes per rules, but disputed)
- Audio quality: Unclear pronunciation = disputes
- Context: Trump says "Cuba" referring to the car, not the country — still counts
- Multiple speakers: Only Trump's words count, not others on stage

**Mitigation:** Read resolution criteria extremely carefully. Polymarket uses UMA oracle system (decentralized dispute resolution). Kalshi uses internal review.

### Risk 2: Liquidity Traps ⚠️ MEDIUM
**Problem:** Some sub-markets have very thin order books
- Can buy in easily but can't sell out
- Spread can be 10-20% on low-volume sub-markets
- Example: Roblox earnings mention = only $475 total volume

**Mitigation:** Only trade sub-markets with >$5K volume. Stick to flagship markets (Trump weekly, SOTU, Super Bowl).

### Risk 3: Speed Competition ⚠️ MEDIUM
**Problem:** Other bots/traders also monitor speeches in real-time
- Professional mention market tools already exist ($199/mo)
- Some traders may have lower latency (closer to stream source)
- As mention markets grow, competition will intensify

**Mitigation:** Build superior infrastructure, focus on less-competitive sub-markets (earnings calls, podcasts vs. Trump weekly which everyone watches).

### Risk 4: Platform Risk ⚠️ LOW-MEDIUM
**Problem:** Regulatory changes could affect platforms
- CFTC is actively debating prediction market regulation
- Torres bill could ban government insiders (doesn't affect us)
- Polymarket US access requires VPN (ToS violation)
- Kalshi is fully regulated but more restricted market selection

**Mitigation:** Use Kalshi for US-regulated markets, Polymarket for broader selection. Stay within legal boundaries.

### Risk 5: Insider Trading Front-Running ⚠️ MEDIUM
**Problem:** Insiders (speechwriters, WH staff) can bet before events
- Guardian found $2.17M in suspicious insider profits
- These accounts move markets BEFORE the public event
- Can create false signals

**Mitigation:** Use insider-hunter accounts on X to detect suspicious activity. If a market moves suspiciously pre-event, follow the move rather than fighting it. The blockchain analyst "Andrew 10 Gwei" publicly tracks and shares insider accounts.

### Risk 6: Market Manipulation ⚠️ LOW
**Problem:** Someone in position of authority changes behavior to win a bet
- Karoline Leavitt 65-minute briefing incident (likely coincidence)
- ISW map manipulation for Myrnohrad war market (confirmed)
- Trump could theoretically be influenced by prediction markets

**Mitigation:** This risk benefits us if we detect it. Watch for unusual market movements.

---

## 11. Competitive Landscape

### Who's Already Doing This?

1. **Professional Mention Market Traders** — Using tools like MentionMarkets.com, placing $10K+ bets
2. **Insider-Hunters** (Andrew 10 Gwei et al.) — Track suspicious accounts, copy their bets
3. **Bot Operators** — Real-time STT monitoring, auto-trading
4. **Whale Copiers** — Track ImJustKen, SwissMiss, etc. and mirror their positions
5. **A River Whale (Substack)** — Publishing free transcript analysis, building audience

### Our Competitive Advantages
1. **Technical capability** — We can build STT pipeline + trading bot
2. **Multi-platform** — Can trade both Polymarket AND Kalshi simultaneously
3. **Already have bird CLI** — Can monitor Twitter/X for real-time news
4. **Existing prediction market infrastructure** — From BTC arbitrage work
5. **LLM integration** — Can use AI to analyze transcripts + predict likely mentions

---

## 12. Cross-Platform Arbitrage Opportunities

### Same Market, Different Platforms
Both Polymarket and Kalshi offer Trump mention markets, but with:
- Different word selections
- Different pricing
- Different liquidity levels

**Strategy:** When the same word appears on both platforms with different YES prices, buy on the cheaper platform and sell on the more expensive one.

**Example (Hypothetical):**
- "Iran" on Polymarket: YES at 55¢
- "Iran" on Kalshi: YES at 62¢
- Buy YES on PM at 55¢, sell NO on Kalshi (equivalent to selling YES at 62¢)
- Locked-in 7¢ profit regardless of outcome

**Caveat:** Resolution timing may differ between platforms. Check rules carefully.

---

## 13. Key Upcoming Events Calendar

| Date | Event | Expected Mention Market Volume | Priority |
|------|-------|-------------------------------|----------|
| **Feb 5** | Amazon + Reddit earnings | $75K+ | TONIGHT |
| **Feb 6** | WH Press Briefing | $160K+ | Tomorrow |
| **Feb 8** | Trump weekly resolution | $3.17M | This weekend |
| **Feb 8** | Super Bowl LX | $935K+ | This weekend |
| **Feb 9** | ON Semi earnings | NEW | Low |
| **Feb 19** | Nebius earnings | $40K+ | Medium |
| **Feb 20** | Coinbase earnings | $58K+ | Medium |
| **Feb 24** | **TRUMP STATE OF THE UNION** | **$5-10M+ expected** | **CRITICAL** |
| **Feb 28** | Trump monthly resolution | $106K+ | Medium |

---

## 14. Sources & References

1. NYT: "Betting on prediction markets is their job. They make millions" (Jan 22, 2026)
2. The Guardian: "On Polymarket, 'privileged' users made millions" (Jan 30, 2026)
3. A River Whale Substack: Mention market transcript analysis (Sep 2024)
4. PolymarketWhale (Paragraph.com): "Strategies and Tools to make money on Polymarket" (Jan 2, 2026)
5. BeInCrypto: "White House Briefing Fuels Insider Trading Debate" (Jan 2026)
6. AInvest: "Polymarket Tracker: Trump 100 Day Commemorative Rally" (Apr 2025)
7. MentionMarkets.com — Paid transcript analytics tool
8. Kalshi Market Integrity page — insider trading rules
9. Polymarket API (gamma-api.polymarket.com)
10. Kalshi API (docs.kalshi.com)

---

## 15. Bottom Line

**Mention markets are a legitimate, high-volume opportunity** with multiple proven strategies. The key advantages:

1. **Predictable events** — speeches, earnings calls, briefings happen on schedule
2. **Analyzable** — historical transcripts give statistical edge
3. **Speed alpha** — prediction markets are slower than traditional markets, first-mover wins
4. **YES is overpriced** — structural edge in buying NO on unlikely mentions
5. **Growing rapidly** — volumes are increasing weekly as more platforms add mention markets

**Recommended starting capital:** $2,000-5,000
**Expected annualized return:** 30-100% (depends on strategy and frequency)
**Time investment:** 5-10 hours/week (monitoring + analysis)
**Breakeven timeline:** 1-2 weeks with active trading

The biggest upcoming opportunity is **Trump's State of the Union on February 24** — start building transcript analysis corpus and positioning NOW.
