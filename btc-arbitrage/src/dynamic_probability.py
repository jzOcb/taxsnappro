#!/usr/bin/env python3
"""
Dynamic Probability Estimation using LLM

Instead of static lookup tables, use LLM to estimate probability
that a keyword will be mentioned in a specific event context.

Iron Rule #11: No model = No trade
This module provides dynamic model generation for new/unknown events.
"""

import os
import json
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime
import hashlib

# Use Gemini API for LLM calls (gemini-2.0-flash for cost efficiency)
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
HAS_LLM = bool(GEMINI_API_KEY)

logger = logging.getLogger(__name__)

# Cache for LLM responses (avoid repeated calls for same market)
PROBABILITY_CACHE: Dict[str, Tuple[float, datetime]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache

# Calibration database path
CALIBRATION_DB = "/home/clawdbot/clawd/btc-arbitrage/data/probability_calibration.jsonl"

# Rate limiting for Gemini API (avoid 429 errors)
_last_api_call = 0
API_CALL_INTERVAL = 1.5  # seconds between calls


def _cache_key(market: dict) -> str:
    """Generate cache key from market details."""
    key_data = f"{market.get('series_ticker', '')}:{market.get('keyword', '')}:{market.get('event_title', '')}"
    return hashlib.md5(key_data.encode()).hexdigest()


def estimate_probability_llm(market: dict) -> Optional[float]:
    """
    Use LLM to estimate probability that keyword will be mentioned.
    
    Returns:
        float 0-100: Estimated probability in cents/percentage
        None: If LLM is uncertain or unavailable (don't trade)
    """
    if not HAS_LLM:
        logger.warning("OpenAI API key not available, skipping LLM estimation")
        return None
    
    # Check cache first
    cache_key = _cache_key(market)
    if cache_key in PROBABILITY_CACHE:
        prob, timestamp = PROBABILITY_CACHE[cache_key]
        age = (datetime.utcnow() - timestamp).total_seconds()
        if age < CACHE_TTL_SECONDS:
            logger.debug(f"Using cached probability for {market.get('keyword')}: {prob}")
            return prob
    
    # Build prompt
    event_title = market.get("event_title", "Unknown event")
    keyword = market.get("keyword", "")
    series_ticker = market.get("series_ticker", "")
    close_time = market.get("close_time", "")
    description = market.get("description", "")
    
    # Extract speaker/source from event title
    speaker = "Unknown"
    if "trump" in event_title.lower():
        speaker = "Donald Trump (US President)"
    elif "biden" in event_title.lower():
        speaker = "Joe Biden (former US President)"
    elif "sotu" in event_title.lower() or "state of the union" in event_title.lower():
        speaker = "US President (State of the Union address)"
    elif "press briefing" in event_title.lower():
        speaker = "White House Press Secretary"
    elif "earnings" in event_title.lower():
        speaker = "Company executives (earnings call)"
    elif "super bowl" in event_title.lower():
        speaker = "Super Bowl halftime performer / commentators"
    
    prompt = f"""You are a probability estimation expert for prediction markets.

EVENT DETAILS:
- Event: {event_title}
- Description: {description}
- Speaker/Source: {speaker}
- Keyword to predict: "{keyword}"
- Market closes: {close_time}
- Series: {series_ticker}

TASK: Estimate the probability (0-100%) that the exact word or phrase "{keyword}" 
will be mentioned/said during this event.

CONSIDER:
1. Who is speaking and their typical vocabulary
2. What type of event this is (formal speech, casual, interview, etc.)
3. How relevant this keyword is to the event topic
4. Historical patterns for similar events
5. Current news context that might make this word more/less likely

IMPORTANT:
- If this is a politician speaking about their specialty topics, common words are VERY likely (>80%)
- If this is an entertainment event, political words are RARE (<20%)
- Generic words like "America", "people", "great" are almost certain (>90%) in speeches
- Specific names/places depend heavily on current events

OUTPUT FORMAT:
Return ONLY one of these:
- A number 0-100 (your probability estimate)
- "UNCERTAIN" if you don't have enough context to estimate reliably

Your response (just the number or UNCERTAIN):"""

    try:
        # Rate limit to avoid 429 errors
        import time
        global _last_api_call
        elapsed = time.time() - _last_api_call
        if elapsed < API_CALL_INTERVAL:
            time.sleep(API_CALL_INTERVAL - elapsed)
        _last_api_call = time.time()
        
        # Use Gemini API with gemini-2.0-flash for cost efficiency
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": 50,
                    "temperature": 0.3
                }
            },
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Gemini API error: {response.status_code} - {response.text[:200]}")
            return None
        
        data = response.json()
        result = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        if result.upper() == "UNCERTAIN":
            logger.info(f"LLM uncertain about {keyword} in {event_title}")
            return None
        
        try:
            prob = float(result)
            if 0 <= prob <= 100:
                # Cache the result
                PROBABILITY_CACHE[cache_key] = (prob, datetime.utcnow())
                logger.info(f"LLM estimated {keyword} probability: {prob}% for {event_title[:50]}")
                return prob
            else:
                logger.warning(f"LLM returned out-of-range probability: {prob}")
                return None
        except ValueError:
            logger.warning(f"LLM returned non-numeric response: {result}")
            return None
            
    except Exception as e:
        logger.error(f"LLM estimation failed: {e}")
        return None


def estimate_with_confidence(market: dict) -> Tuple[Optional[float], float]:
    """
    Estimate probability with confidence score.
    
    Returns:
        (probability, confidence) where:
        - probability: 0-100 or None
        - confidence: 0-1 (how confident we are in this estimate)
    """
    llm_prob = estimate_probability_llm(market)
    
    if llm_prob is None:
        return None, 0.0
    
    # Factors that increase confidence
    confidence = 0.5  # Base confidence
    
    keyword = market.get("keyword", "").lower()
    event_title = market.get("event_title", "").lower()
    
    # Higher confidence for well-known patterns
    if "trump" in event_title and keyword in ["america", "great", "border", "china", "jobs"]:
        confidence += 0.3  # These are near-certain in Trump speeches
    
    if "state of the union" in event_title:
        confidence += 0.2  # SOTU is very predictable
    
    if "earnings" in event_title and keyword in ["revenue", "growth", "customers", "ai"]:
        confidence += 0.2
    
    # Lower confidence for unusual combinations
    if "entertainment" in market.get("series_type", "") and keyword in ["tariff", "immigration", "ukraine"]:
        confidence -= 0.2  # Political words in entertainment events = uncertain
    
    # Extreme probabilities = higher confidence (clear cases)
    if llm_prob > 90 or llm_prob < 10:
        confidence += 0.1
    
    confidence = max(0.1, min(1.0, confidence))
    
    return llm_prob, confidence


def bayesian_blend(llm_prob: float, market_price: float, llm_weight: float = 0.6) -> float:
    """
    Blend LLM probability with market price (which reflects collective wisdom).
    
    Args:
        llm_prob: LLM's probability estimate (0-100)
        market_price: Current market YES price in cents (0-100)
        llm_weight: How much to weight LLM vs market (0-1)
    
    Returns:
        Blended probability estimate
    """
    market_weight = 1 - llm_weight
    return llm_prob * llm_weight + market_price * market_weight


def record_calibration(market: dict, predicted_prob: float, actual_result: str):
    """
    Record prediction vs actual for calibration tracking.
    
    Args:
        market: Market details
        predicted_prob: Our predicted probability (0-100)
        actual_result: "yes" or "no" (actual settlement)
    """
    actual_prob = 100.0 if actual_result.lower() == "yes" else 0.0
    error = actual_prob - predicted_prob
    
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "series_ticker": market.get("series_ticker", ""),
        "keyword": market.get("keyword", ""),
        "event_title": market.get("event_title", ""),
        "predicted_prob": predicted_prob,
        "actual_result": actual_result,
        "actual_prob": actual_prob,
        "error": error,
        "abs_error": abs(error),
    }
    
    try:
        with open(CALIBRATION_DB, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.info(f"Recorded calibration: {market.get('keyword')} predicted={predicted_prob:.0f}% actual={actual_result} error={error:+.0f}")
    except Exception as e:
        logger.error(f"Failed to record calibration: {e}")


def analyze_calibration() -> Dict:
    """
    Analyze calibration data to assess model accuracy.
    
    Returns:
        Dict with calibration metrics
    """
    if not os.path.exists(CALIBRATION_DB):
        return {"error": "No calibration data yet"}
    
    records = []
    try:
        with open(CALIBRATION_DB) as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except Exception as e:
        return {"error": f"Failed to read calibration data: {e}"}
    
    if not records:
        return {"error": "No calibration records"}
    
    total = len(records)
    abs_errors = [r["abs_error"] for r in records]
    mean_abs_error = sum(abs_errors) / total
    
    # Brier score (lower is better, 0 = perfect)
    brier_scores = [((r["predicted_prob"]/100 - r["actual_prob"]/100) ** 2) for r in records]
    brier_score = sum(brier_scores) / total
    
    # Accuracy buckets
    within_10 = sum(1 for e in abs_errors if e <= 10) / total
    within_20 = sum(1 for e in abs_errors if e <= 20) / total
    
    return {
        "total_predictions": total,
        "mean_absolute_error": round(mean_abs_error, 1),
        "brier_score": round(brier_score, 4),
        "within_10pct": round(within_10 * 100, 1),
        "within_20pct": round(within_20 * 100, 1),
    }


# ============================================================================
# INTEGRATION WITH MENTION TRADER
# ============================================================================

def get_dynamic_probability(market: dict, use_static_if_available: bool = True) -> Optional[float]:
    """
    Main entry point: Get probability estimate for a market.
    
    Strategy:
    1. If static model exists and use_static_if_available=True, use static
    2. Otherwise, use LLM dynamic estimation
    3. Blend with market price for final estimate
    
    Args:
        market: Market details dict
        use_static_if_available: Prefer static models when available
    
    Returns:
        Probability 0-100, or None if should not trade
    """
    # Try LLM estimation
    llm_prob, confidence = estimate_with_confidence(market)
    
    if llm_prob is None:
        return None
    
    # Only trade if confidence is high enough
    MIN_CONFIDENCE = 0.4
    if confidence < MIN_CONFIDENCE:
        logger.info(f"Skipping {market.get('keyword')}: confidence {confidence:.2f} < {MIN_CONFIDENCE}")
        return None
    
    # Blend with market price (market knows things we don't)
    market_yes = market.get("yes_mid", 50)
    
    # Weight LLM more when we're confident, market more when uncertain
    llm_weight = 0.4 + (confidence * 0.4)  # 0.4-0.8 based on confidence
    
    final_prob = bayesian_blend(llm_prob, market_yes, llm_weight)
    
    logger.info(f"Dynamic probability for {market.get('keyword')}: "
                f"LLM={llm_prob:.0f}% (conf={confidence:.2f}) + market={market_yes}¢ "
                f"→ final={final_prob:.0f}%")
    
    return final_prob


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    test_market = {
        "series_ticker": "KXMAMDANIMENTION",
        "keyword": "hochul / governor",
        "event_title": "Mamdani's childcare announcement",
        "description": "Will Hochul/Governor be mentioned in Mamdani's childcare announcement?",
        "close_time": "2026-02-27",
        "yes_mid": 60,
    }
    
    print("Testing dynamic probability estimation...")
    prob = get_dynamic_probability(test_market)
    print(f"Result: {prob}")
    
    if prob:
        print(f"\nFor hochul/governor in NY state childcare announcement:")
        print(f"LLM should recognize this is near-certain (~95%+)")
        print(f"Unlike static model which returned 20%")
