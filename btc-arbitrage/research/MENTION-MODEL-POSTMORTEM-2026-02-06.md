# Mention Market Probability Model Post-Mortem

**Date:** 2026-02-06
**Total P&L:** -$153.54
**Win Rate:** 2W/7L (22%)

## Settlement Analysis

### LOSSES (NO bets, word WAS mentioned)
| Word | Context | PnL | Our Est | Actual | Error |
|------|---------|-----|---------|--------|-------|
| ukraine | Trump speech | -$29.40 | ~25% | 100% | -75pp |
| peace in middle east | Trump speech | -$29.67 | ~25% | 100% | -75pp |
| hottest | Trump speech | -$29.89 | ~20% | 100% | -80pp |
| hochul/governor | NY politics | -$34.80 | 20% | 100% | -80pp |
| manufacture | Trump speech | -$17.40 | ~30% | 100% | -70pp |

### WINS (NO bets, word was NOT mentioned)
| Word | Context | PnL | Our Est | Actual | Error |
|------|---------|-----|---------|--------|-------|
| affordable | Trump speech | +$10.40 | ~20% | 0% | +20pp |
| ballroom | Trump speech | +$2.72 | ~5% | 0% | +5pp |

### YES bets
| Word | Context | PnL | Our Est | Actual |
|------|---------|-----|---------|--------|
| tariff | Trump speech | +$24.42 | 95% | 100% ✓ |
| biden | Trump speech | -$49.92 | 99% | 0% ✗ |

## Root Cause Analysis

### Problem 1: Category Blindness
Our model treated all words equally. Reality:
- **Policy words** (ukraine, peace, tariff) = 80-99% in political speeches
- **Superlatives** (hottest, greatest, best) = 90%+ for Trump specifically
- **Random words** (ballroom, armada) = <10%

### Problem 2: No Speaker Profile
Trump has predictable vocabulary patterns:
- Uses superlatives constantly ("hottest", "greatest", "best")
- Always mentions key policy topics (Ukraine, China, border, tariffs)
- Uses specific phrases repeatedly ("peace through strength")

### Problem 3: Static vs Dynamic Context
Markets for current events (Ukraine war, tariff policy) should have ~100% probability
because these are active topics. Our model didn't account for news context.

## Correct Probability Model Design

### Tier 1: Near-Certain Words (90-99%)
For Trump specifically:
- Current policy topics (Ukraine, China, border, tariffs, inflation)
- Superlatives (greatest, best, hottest, biggest, tremendous)
- Self-references (Trump, President, administration)
- Named enemies (Biden, Democrats, fake news, radical left)

### Tier 2: Likely Words (60-80%)
- General political terms (Congress, America, economy, jobs)
- Countries in the news (Russia, Israel, Iran, North Korea)
- Common verbs (win, fight, build, make)

### Tier 3: Possible Words (20-50%)
- Specific policy jargon (amortization, appropriations)
- Lesser-known places (specific cities, small countries)
- Technical terms

### Tier 4: Unlikely Words (5-20%)
- Random nouns (ballroom, armada, penguin)
- Uncommon words not in typical political vocabulary
- Pop culture references (usually)

### Tier 5: Near-Zero (<5%)
- Obscure words Trump would never use
- Words that would be inappropriate for context

## Implementation Plan

### Option A: Historical Transcript Analysis
1. Collect all Trump speeches/transcripts (public data)
2. Build word frequency table by context (rally, SOTU, press conf)
3. Calculate empirical P(word | speaker, event_type)

### Option B: LLM-Assisted Classification
1. For each word, ask LLM to classify into Tier 1-5
2. LLM considers speaker, event type, current news context
3. Already implemented in dynamic_probability.py but needs better prompting

### Option C: Market-Based Learning
1. Track what the market prices words at
2. Assume market is ~80% efficient for liquid markets
3. Only trade when we have strong disagreement + evidence

### Recommended: Hybrid Approach
1. Use historical transcripts to build base rates (Option A)
2. Adjust with LLM for current context (Option B)  
3. Require significant edge vs market price (Option C)
4. Start with SMALL positions until model is calibrated

## Immediate Actions

1. **PAUSE trading** - Done ✓
2. **Collect historical transcripts** - Trump speeches 2024-2026
3. **Build word frequency database** - By event type
4. **Recalibrate model** - Update TRUMP_WEEKLY_BASE_RATES
5. **Paper trade with new model** - 1 week minimum before live

## Key Lesson

> The "NO Grinder" thesis is WRONG for high-frequency political words.
> YES is NOT always overpriced - for near-certain words, YES is often UNDERPRICED.
> Need category-aware probability model, not blanket "NO" strategy.
