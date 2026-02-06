# LLM & AI for Prediction Market Trading Research
**Date:** 2026-02-06
**Focus:** Probability estimation, calibration, mention markets, dynamic modeling

---

## Executive Summary

This research covers how LLMs and AI are being used for prediction market trading, with emphasis on:
- Probability estimation techniques
- Calibration methods
- Multi-agent decision systems
- Technical trading strategies for short-term markets (15-min BTC markets)

---

## 1. Academic Research Papers

### 1.1 Key Papers on LLM Forecasting

#### "Approaching Human-Level Forecasting with Language Models" (arXiv:2402.18563)
**Authors:** Danny Halawi et al. (Feb 2024)

**Key Findings:**
- Developed retrieval-augmented LM system for automatic forecasting
- System includes: automatic search, forecast generation, prediction aggregation
- Performance: "nears the crowd aggregate of competitive forecasters, and in some settings surpasses it"
- **Actionable Insight:** Use retrieval-augmented generation (RAG) for context gathering before probability estimation

**Architecture:**
```
1. Question Input
2. Automated Search → Retrieve relevant news/data
3. LLM Forecast Generation
4. Aggregation of multiple forecasts
5. Final probability output
```

#### "PRISM: Probability Reconstruction via Shapley Measures" (arXiv:2601.09151)
**Authors:** Yang Nan et al. (Jan 2026)

**Key Technique:**
- Uses **Shapley values** to decompose probability estimates by factor contribution
- Aggregates factor-level contributions to reconstruct calibrated estimates
- Improves accuracy over direct prompting across finance, healthcare, agriculture

**Actionable Implementation:**
```python
# Conceptual PRISM approach
def estimate_probability_prism(event_description, factors):
    """
    Shapley-based probability estimation
    """
    # 1. Identify key factors affecting outcome
    factors = extract_factors(event_description)  # e.g., ["speaker_history", "topic_relevance", "timing"]
    
    # 2. Calculate marginal contribution of each factor
    shapley_values = {}
    for factor in factors:
        # Estimate P(outcome | with factor) - P(outcome | without factor)
        shapley_values[factor] = calculate_marginal_contribution(factor, event_description)
    
    # 3. Aggregate to final probability
    base_probability = 0.5  # neutral baseline
    final_prob = base_probability + sum(shapley_values.values())
    return clip(final_prob, 0, 1)
```

#### "AIA Forecaster: Technical Report" (arXiv, Nov 2025)
**Focus:** LLM-based judgmental forecasting with calibration

**Three Core Elements:**
1. **Agentic Search** - Search over high-quality news sources
2. **Supervisor Agent** - Reconciles disparate forecasts for same event
3. **Statistical Calibration** - Post-hoc calibration of raw LLM outputs

**Calibration Method:** Uses historical forecast accuracy to adjust future predictions

#### "TruthTensor: Evaluating LLMs through Human Imitation on Prediction Market" (Jan 2026)
- Evaluates models as "human-imitation systems in socially-grounded, high-entropy environments"
- Tests reasoning under evolving conditions (drift)
- **Insight:** Models need to handle distribution shift in prediction markets

#### "AI-Augmented Predictions: LLM Assistants Improve Human Forecasting Accuracy" (Feb 2024)
**Authors:** Philipp Schoenegger, Peter S. Park, **Philip E. Tetlock** (superforecasting expert)
- LLMs can augment human forecasters to improve accuracy
- Hybrid human+AI approaches outperform either alone

---

## 2. Calibration Techniques

### 2.1 Key Calibration Papers

#### "Balancing Classification and Calibration Performance via Calibration Aware RL" (Jan 2026)
- Uses reinforcement learning to balance accuracy vs. calibration
- **Key Insight:** Standard training objectives often sacrifice calibration for accuracy

#### "BaseCal: Unsupervised Confidence Calibration via Base Model Signals" (Jan 2026)
- Calibrates post-trained LLMs using signals from base models
- Useful when labeled calibration data is unavailable

#### "Conformal Prediction Sets for Next-Token Prediction" (Dec 2025)
- Applies conformal prediction for uncertainty quantification
- Provides coverage guarantees with set efficiency
- **Actionable:** Can be adapted for probability interval estimation

### 2.2 Practical Calibration Approaches

```python
# Temperature scaling for calibration
def calibrated_probability(raw_logits, temperature=1.0):
    """
    Simple temperature scaling for better calibration
    """
    scaled_logits = raw_logits / temperature
    return softmax(scaled_logits)

# Platt scaling
def platt_scaling(llm_confidence, a, b):
    """
    Platt scaling: learns parameters a, b from calibration set
    calibrated_prob = 1 / (1 + exp(a * confidence + b))
    """
    return 1 / (1 + np.exp(a * llm_confidence + b))

# Isotonic regression calibration
from sklearn.isotonic import IsotonicRegression
def isotonic_calibration(confidences, outcomes):
    """
    Non-parametric calibration using isotonic regression
    """
    ir = IsotonicRegression(out_of_bounds='clip')
    ir.fit(confidences, outcomes)
    return ir
```

### 2.3 Calibration Metrics

```python
def expected_calibration_error(predicted_probs, actual_outcomes, n_bins=10):
    """
    ECE: weighted average of bin-level calibration errors
    """
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0
    for i in range(n_bins):
        mask = (predicted_probs >= bins[i]) & (predicted_probs < bins[i+1])
        if mask.sum() > 0:
            bin_acc = actual_outcomes[mask].mean()
            bin_conf = predicted_probs[mask].mean()
            ece += mask.sum() * abs(bin_acc - bin_conf)
    return ece / len(predicted_probs)

def brier_score(predicted_probs, actual_outcomes):
    """
    Brier score: mean squared error of probability predictions
    """
    return np.mean((predicted_probs - actual_outcomes) ** 2)
```

---

## 3. GitHub Trading Bots Analysis

### 3.1 Kalshi AI Trading Bot (ryanfrigo/kalshi-ai-trading-bot)
**Stars:** 114 | **Language:** Python | **LLM:** Grok-4

**Architecture:**
```
Multi-Agent Decision Engine:
├── Forecaster Agent → Estimates true probability
├── Critic Agent → Identifies flaws/missing context  
└── Trader Agent → Makes BUY/SKIP decisions with sizing
```

**Key Features:**
- Kelly Criterion position sizing
- Risk parity allocation
- Real-time news analysis for market context
- Confidence calibration and validation

**Code Pattern - Multi-Agent Decision:**
```python
class TradingDecision:
    def __init__(self, forecaster_llm, critic_llm, trader_llm):
        self.forecaster = forecaster_llm
        self.critic = critic_llm
        self.trader = trader_llm
    
    def decide(self, market_data, news_context):
        # Step 1: Forecaster estimates probability
        forecast = self.forecaster.estimate_probability(market_data, news_context)
        
        # Step 2: Critic reviews and finds issues
        critique = self.critic.analyze(forecast, market_data)
        
        # Step 3: Trader makes final decision
        decision = self.trader.decide(forecast, critique, market_data['current_odds'])
        
        return decision
```

### 3.2 Kalshi Deep Trading Bot (OctagonAI/kalshi-deep-trading-bot)
**Stars:** 96 | **Uses:** Octagon Deep Research + OpenAI

**Workflow:**
1. Fetch top 50 events by volume
2. Process top 10 markets per event
3. **Research events WITHOUT seeing odds** (unbiased estimate)
4. Fetch current market odds
5. Compare research probability vs market odds
6. Execute when edge detected

**Key Insight - Unbiased Estimation:**
```python
# Research BEFORE seeing market odds to avoid anchoring bias
research_result = octagon_research(event_description, markets_without_odds)
predicted_probability = research_result.probability

# Only then fetch market odds
market_odds = fetch_market_odds(market_id)

# Calculate edge
edge = predicted_probability - market_odds
if abs(edge) > MIN_EDGE_THRESHOLD:
    execute_trade(...)
```

**Hedging Configuration:**
```python
ENABLE_HEDGING = True
HEDGE_RATIO = 0.25  # Hedge 25% of main bet on opposite side
MIN_CONFIDENCE_FOR_HEDGING = 0.6  # Only hedge low-confidence bets
MAX_HEDGE_AMOUNT = 50.0
```

### 3.3 Polymarket LLM Bot (voicegn/polymarket-bot)
**Stars:** 12 | **Language:** Rust | **LLMs:** DeepSeek, Claude, GPT, Ollama

**Strategies:**
1. **Edge-Based Trading** - LLM estimates "true" probability, trades when edge >6%
2. **Compound Growth** - Dynamic Kelly with sqrt scaling
3. **Copy Trading** - Follow successful traders

**Kelly Criterion Implementation:**
```python
def kelly_fraction(probability, odds, fraction=0.35):
    """
    Conservative Kelly sizing
    f* = (bp - q) / b
    where: b = odds - 1, p = win probability, q = 1 - p
    """
    b = odds - 1
    p = probability
    q = 1 - p
    full_kelly = (b * p - q) / b
    return max(0, full_kelly * fraction)  # Use fractional Kelly

# Compound growth with sqrt scaling
def compound_sizing(base_size, current_balance, initial_balance):
    """
    4x balance → 2x sizing (sqrt scaling)
    """
    multiplier = np.sqrt(current_balance / initial_balance)
    return base_size * min(multiplier, 2.0)  # Cap at 2x
```

**Risk Management:**
```python
RISK_CONFIG = {
    'max_position_pct': 0.05,      # 5% max per position
    'max_exposure_pct': 0.50,       # 50% max total exposure
    'max_daily_loss_pct': 0.10,     # 10% daily loss limit
    'min_balance_reserve': 100,     # Keep $100 reserve
    'max_open_positions': 10,
}
```

### 3.4 Polymarket RSI/MACD Bot (pio-ne-er/Polymarket-RSI-MACD-Momentum-Trading-Bot)
**Stars:** 156 | **Language:** Rust | **Focus:** 15-minute BTC markets

**Technical Indicators:**
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Momentum

**Relevant for 15-min BTC Markets:**
```rust
// Strategy configuration
struct StrategyConfig {
    trend_threshold: f64,     // e.g., 90.0 for RSI
    profit_threshold: f64,    // e.g., 0.02 for 2%
    sl_threshold: f64,        // stop loss
    lookback: usize,          // indicator period
    position_size: f64,
}

// Data flow
// MarketMonitor → MarketSnapshot → PricePoint → Strategy → TradeAction → Execute
```

### 3.5 Sports Prediction Bot (kratos-te/polymarket-sports-prediction-bot)
**Stars:** 98 | **Languages:** Rust + Python

**5 Trading Strategies:**
1. **CLV Arbitrage** - Compare to Pinnacle/Betfair closing lines
2. **Poisson EV** - Monte Carlo simulation for totals
3. **Injury News Scalping** - React to breaking news in <60s
4. **Market Microstructure** - Follow whale wallets
5. **Sentiment Gap** - Fade extreme public sentiment (VADER + BERT)

**Poisson Expected Value:**
```python
def poisson_expected_value(team_offense, team_defense, opp_offense, opp_defense, 
                           market_line, market_odds, simulations=10000):
    """
    Monte Carlo simulation for totals markets
    """
    expected_points_team = (team_offense + opp_defense) / 2
    expected_points_opp = (opp_offense + team_defense) / 2
    
    results = []
    for _ in range(simulations):
        team_score = np.random.poisson(expected_points_team)
        opp_score = np.random.poisson(expected_points_opp)
        total = team_score + opp_score
        results.append(total > market_line)
    
    true_probability = np.mean(results)
    edge = true_probability - market_odds
    
    return true_probability, edge
```

---

## 4. Mention Market Probability Modeling

### 4.1 Event Mention Estimation Framework

For markets like "Will X be mentioned in SOTU?" or "Will CEO mention Y in earnings call?":

```python
class MentionProbabilityEstimator:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.historical_data = {}
    
    def estimate_mention_probability(self, event_context):
        """
        Estimate probability of a topic being mentioned in an event
        """
        factors = {
            'topic_relevance': self._assess_topic_relevance(event_context),
            'speaker_history': self._analyze_speaker_history(event_context),
            'current_events': self._current_events_pressure(event_context),
            'audience_expectations': self._audience_expectations(event_context),
            'timing_factors': self._timing_analysis(event_context),
            'historical_base_rate': self._get_base_rate(event_context),
        }
        
        # LLM synthesizes factors
        prompt = self._build_estimation_prompt(event_context, factors)
        raw_estimate = self.llm.estimate(prompt)
        
        # Apply calibration
        calibrated = self.calibrate(raw_estimate)
        
        return calibrated, factors
    
    def _assess_topic_relevance(self, ctx):
        """Score 0-1 based on topic's relevance to event theme"""
        prompt = f"""
        Event: {ctx['event_name']}
        Topic: {ctx['mention_topic']}
        
        Rate relevance 0-100 based on:
        - Is this topic within the event's typical scope?
        - Has this topic been trending recently?
        - Is there pressure to address this topic?
        
        Return only a number.
        """
        return self.llm.query(prompt) / 100
    
    def _analyze_speaker_history(self, ctx):
        """Analyze past mentions by this speaker"""
        # Query historical transcripts
        past_mentions = self.historical_data.get(ctx['speaker'], {})
        topic_mention_rate = past_mentions.get(ctx['mention_topic'], 0.1)
        return topic_mention_rate
```

### 4.2 Dynamic Probability Updates (Predict_anon Style)

Based on @predict_anon's methodology (A/B testing, KISS principle, manipulation cost models):

```python
class DynamicProbabilityModel:
    """
    Dynamic probability model that updates based on new information
    """
    def __init__(self, initial_estimate, confidence):
        self.probability = initial_estimate
        self.confidence = confidence
        self.evidence_history = []
    
    def update_bayesian(self, new_evidence, evidence_weight):
        """
        Bayesian update based on new evidence
        
        P(H|E) = P(E|H) * P(H) / P(E)
        """
        prior = self.probability
        
        # Likelihood of evidence given hypothesis
        likelihood = self._assess_likelihood(new_evidence)
        
        # Update
        posterior = (likelihood * prior) / (
            likelihood * prior + (1 - likelihood) * (1 - prior)
        )
        
        # Weight by evidence strength
        self.probability = prior + evidence_weight * (posterior - prior)
        self.evidence_history.append({
            'evidence': new_evidence,
            'weight': evidence_weight,
            'prior': prior,
            'posterior': self.probability
        })
        
        return self.probability
    
    def update_from_market_movement(self, old_price, new_price, volume):
        """
        Incorporate market information (but discount for manipulation)
        """
        price_delta = new_price - old_price
        
        # Estimate manipulation probability based on volume
        manipulation_cost = self._estimate_manipulation_cost(volume)
        information_signal = 1 - (1 / (1 + manipulation_cost))
        
        # Partial update toward market price
        market_weight = 0.3 * information_signal
        self.probability = (1 - market_weight) * self.probability + market_weight * new_price
        
        return self.probability
    
    def _estimate_manipulation_cost(self, volume):
        """
        Higher volume = higher manipulation cost = more likely genuine signal
        """
        # Assume manipulation becomes expensive above $10k
        return volume / 10000
```

### 4.3 A/B Testing for Strategy Validation

```python
class ABTestingFramework:
    """
    A/B test different probability estimation approaches
    """
    def __init__(self):
        self.strategies = {}
        self.results = {}
    
    def register_strategy(self, name, estimator_fn):
        self.strategies[name] = {
            'estimator': estimator_fn,
            'predictions': [],
            'outcomes': []
        }
    
    def record_prediction(self, strategy_name, market_id, predicted_prob):
        self.strategies[strategy_name]['predictions'].append({
            'market_id': market_id,
            'predicted': predicted_prob,
            'timestamp': time.time()
        })
    
    def record_outcome(self, market_id, actual_outcome):
        for name, data in self.strategies.items():
            for pred in data['predictions']:
                if pred['market_id'] == market_id:
                    data['outcomes'].append({
                        'predicted': pred['predicted'],
                        'actual': actual_outcome
                    })
    
    def evaluate(self):
        """Calculate metrics for each strategy"""
        results = {}
        for name, data in self.strategies.items():
            if len(data['outcomes']) < 10:
                continue
            
            preds = [o['predicted'] for o in data['outcomes']]
            actuals = [o['actual'] for o in data['outcomes']]
            
            results[name] = {
                'brier_score': brier_score(preds, actuals),
                'ece': expected_calibration_error(preds, actuals),
                'accuracy': np.mean([
                    (p > 0.5) == a for p, a in zip(preds, actuals)
                ]),
                'n_predictions': len(preds)
            }
        
        return results
```

---

## 5. 15-Minute BTC Market Strategies

### 5.1 Price Momentum with LLM Context

```python
class BTCShortTermPredictor:
    """
    Combines technical indicators with LLM market sentiment analysis
    """
    def __init__(self, llm_client, price_feed):
        self.llm = llm_client
        self.price_feed = price_feed
        self.lookback = 15  # 15-minute windows
    
    def predict_15min_direction(self):
        # Technical signals
        prices = self.price_feed.get_recent(minutes=60)
        rsi = calculate_rsi(prices, period=14)
        macd, signal = calculate_macd(prices)
        momentum = prices[-1] / prices[-15] - 1
        
        # LLM context analysis
        recent_news = self.get_recent_btc_news()
        sentiment = self.llm.analyze_sentiment(recent_news)
        
        # Combine signals
        technical_score = self._technical_score(rsi, macd, momentum)
        combined_probability = self._combine_signals(technical_score, sentiment)
        
        return combined_probability
    
    def _technical_score(self, rsi, macd, momentum):
        """
        Score -1 to 1 based on technical indicators
        """
        score = 0
        
        # RSI: oversold/overbought
        if rsi < 30:
            score += 0.3  # Oversold = likely to go up
        elif rsi > 70:
            score -= 0.3  # Overbought = likely to go down
        
        # MACD crossover
        if macd > 0:
            score += 0.2
        else:
            score -= 0.2
        
        # Momentum
        score += np.clip(momentum * 5, -0.3, 0.3)
        
        return score
    
    def _combine_signals(self, technical, sentiment):
        """
        Convert combined score to probability
        """
        combined = 0.6 * technical + 0.4 * sentiment  # Weight technical higher
        probability = 1 / (1 + np.exp(-combined * 3))  # Sigmoid
        return probability
```

### 5.2 Volatility-Adjusted Position Sizing

```python
def volatility_adjusted_size(base_size, current_volatility, target_volatility=0.02):
    """
    Reduce size when volatility is high
    """
    adjustment = target_volatility / max(current_volatility, target_volatility)
    return base_size * adjustment

def calculate_realized_volatility(prices, window=15):
    """
    15-minute realized volatility
    """
    returns = np.diff(np.log(prices))
    return np.std(returns[-window:]) * np.sqrt(window)
```

---

## 6. Actionable Implementation Checklist

### 6.1 For Mention Markets
- [ ] Build historical database of speaker transcripts
- [ ] Calculate base rates for topic mentions
- [ ] Implement factor-based probability estimation
- [ ] Apply Platt scaling calibration
- [ ] Track and A/B test different estimation methods

### 6.2 For 15-min BTC Markets
- [ ] Set up real-time price feed
- [ ] Implement RSI/MACD/Momentum indicators
- [ ] Add LLM sentiment layer
- [ ] Use fractional Kelly for sizing
- [ ] Implement volatility adjustment

### 6.3 Calibration Pipeline
- [ ] Collect calibration dataset (predictions + outcomes)
- [ ] Train temperature/Platt scaling parameters
- [ ] Monitor ECE and Brier scores over time
- [ ] Retrain calibration weekly

### 6.4 Risk Management
- [ ] Max 5% per position
- [ ] Max 50% total exposure
- [ ] Daily loss limit (10%)
- [ ] Drawdown protection (reduce at -10%, halt at -20%)

---

## 7. Key Takeaways

1. **Multi-Agent Systems Work** - Forecaster → Critic → Trader pattern improves decision quality
2. **Avoid Anchoring** - Estimate probability BEFORE seeing market odds
3. **Calibration is Essential** - Raw LLM outputs need post-hoc calibration
4. **Fractional Kelly** - Use 30-50% Kelly for conservative sizing
5. **Factor Decomposition** - Shapley values help understand probability drivers
6. **A/B Test Everything** - Track and compare strategy performance
7. **Manipulation Awareness** - Discount thin markets, trust high-volume signals

---

## 8. Resources & References

### Papers
- arXiv:2402.18563 - "Approaching Human-Level Forecasting with Language Models"
- arXiv:2601.09151 - "PRISM: Probability Reconstruction via Shapley Measures"
- arXiv:2411.06309 - "AIA Forecaster: Technical Report"

### GitHub Repos
- ryanfrigo/kalshi-ai-trading-bot (114⭐) - Multi-agent Kalshi bot
- OctagonAI/kalshi-deep-trading-bot (96⭐) - Deep research approach
- voicegn/polymarket-bot (12⭐) - Rust LLM bot with Kelly
- pio-ne-er/Polymarket-RSI-MACD-Momentum-Trading-Bot (156⭐) - Technical indicators
- kratos-te/polymarket-sports-prediction-bot (98⭐) - Multi-strategy sports bot

### Calibration Resources
- Manifold Markets calibration: https://manifold.markets/calibration
- Metaculus forecasting resources

---

*Research compiled 2026-02-06 | Web search unavailable, used direct fetching*
