#!/usr/bin/env python3
"""
Mention Market Probability Estimation V2
=========================================

Three-layer probability model based on research:

Layer 1: Static Knowledge (trump_word_model.py)
  - Tiered word categories from domain knowledge
  - Fast, no API calls, handles 80% of cases

Layer 2: Dynamic LLM Estimation (dynamic_probability.py)  
  - For unknown words, uses Gemini to estimate
  - Context-aware: considers speaker, event type, current news

Layer 3: Calibration Adjustment
  - Tracks prediction vs actual outcomes
  - Learns systematic biases and corrects them
  - Implements Bayesian update based on historical accuracy

Final: P(word) = calibrate(blend(static_prob, llm_prob, market_prob))
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict
from pathlib import Path

# Import our modules
try:
    from trump_word_model import get_base_probability, classify_word_tier
    HAS_STATIC_MODEL = True
except ImportError:
    HAS_STATIC_MODEL = False

try:
    from dynamic_probability import estimate_probability_llm, estimate_with_confidence
    HAS_DYNAMIC_MODEL = True
except ImportError:
    HAS_DYNAMIC_MODEL = False

logger = logging.getLogger(__name__)

# Calibration data path
CALIBRATION_FILE = Path("/home/clawdbot/clawd/btc-arbitrage/data/mention_calibration.jsonl")
CALIBRATION_SUMMARY = Path("/home/clawdbot/clawd/btc-arbitrage/data/mention_calibration_summary.json")


# ============================================================================
# LAYER 3: CALIBRATION
# ============================================================================

class CalibrationTracker:
    """
    Tracks prediction accuracy and computes calibration adjustments.
    
    Based on research: models have systematic biases that can be corrected
    by tracking historical prediction vs actual outcomes.
    """
    
    def __init__(self):
        self.records = []
        self.summary = {
            "total_predictions": 0,
            "mean_error": 0,
            "bias_by_tier": {},  # tier -> average error (positive = overconfident)
            "bias_by_range": {},  # "0-20", "20-40", etc -> average error
        }
        self._load()
    
    def _load(self):
        """Load historical calibration data."""
        if CALIBRATION_FILE.exists():
            try:
                with open(CALIBRATION_FILE) as f:
                    for line in f:
                        if line.strip():
                            self.records.append(json.loads(line))
            except Exception as e:
                logger.warning(f"Failed to load calibration data: {e}")
        
        if CALIBRATION_SUMMARY.exists():
            try:
                with open(CALIBRATION_SUMMARY) as f:
                    self.summary = json.load(f)
            except:
                pass
    
    def record(self, word: str, tier: int, predicted: float, actual: float, 
               series_type: str = None, event_type: str = None):
        """
        Record a prediction outcome for calibration.
        
        Args:
            word: The word/phrase
            tier: Which tier it was classified into (0=unknown, 1-6=tiers)
            predicted: Our predicted probability (0-100)
            actual: Actual outcome (0 or 100)
            series_type: e.g., 'trump_weekly', 'sotu'
            event_type: e.g., 'speech', 'rally'
        """
        error = predicted - actual  # positive = we were too high (overconfident)
        
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "word": word,
            "tier": tier,
            "predicted": predicted,
            "actual": actual,
            "error": error,
            "series_type": series_type,
            "event_type": event_type,
        }
        
        self.records.append(record)
        
        # Append to file
        CALIBRATION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CALIBRATION_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
        
        # Update summary
        self._update_summary()
    
    def _update_summary(self):
        """Recompute calibration summary from all records."""
        if not self.records:
            return
        
        self.summary["total_predictions"] = len(self.records)
        
        # Overall mean error
        errors = [r["error"] for r in self.records]
        self.summary["mean_error"] = sum(errors) / len(errors)
        
        # Bias by tier
        tier_errors = {}
        for r in self.records:
            tier = r.get("tier", 0)
            if tier not in tier_errors:
                tier_errors[tier] = []
            tier_errors[tier].append(r["error"])
        
        self.summary["bias_by_tier"] = {
            str(t): sum(errs) / len(errs) for t, errs in tier_errors.items()
        }
        
        # Bias by probability range
        range_errors = {"0-20": [], "20-40": [], "40-60": [], "60-80": [], "80-100": []}
        for r in self.records:
            pred = r["predicted"]
            if pred < 20:
                range_errors["0-20"].append(r["error"])
            elif pred < 40:
                range_errors["20-40"].append(r["error"])
            elif pred < 60:
                range_errors["40-60"].append(r["error"])
            elif pred < 80:
                range_errors["60-80"].append(r["error"])
            else:
                range_errors["80-100"].append(r["error"])
        
        self.summary["bias_by_range"] = {
            k: (sum(v) / len(v) if v else 0) for k, v in range_errors.items()
        }
        
        # Save summary
        with open(CALIBRATION_SUMMARY, "w") as f:
            json.dump(self.summary, f, indent=2)
    
    def get_adjustment(self, tier: int, raw_probability: float) -> float:
        """
        Get calibration adjustment for a prediction.
        
        Returns adjustment to SUBTRACT from raw probability.
        (positive adjustment = model was overconfident, reduce probability)
        """
        # Start with tier-specific bias if available
        tier_bias = self.summary.get("bias_by_tier", {}).get(str(tier), 0)
        
        # Add range-specific bias
        if raw_probability < 20:
            range_key = "0-20"
        elif raw_probability < 40:
            range_key = "20-40"
        elif raw_probability < 60:
            range_key = "40-60"
        elif raw_probability < 80:
            range_key = "60-80"
        else:
            range_key = "80-100"
        
        range_bias = self.summary.get("bias_by_range", {}).get(range_key, 0)
        
        # Blend tier and range bias (tier more specific, weight higher)
        if self.summary.get("total_predictions", 0) < 10:
            # Not enough data, don't adjust
            return 0
        
        adjustment = 0.6 * tier_bias + 0.4 * range_bias
        
        # Cap adjustment to avoid extreme corrections
        adjustment = max(-20, min(20, adjustment))
        
        return adjustment


# Global calibration tracker
_calibrator = CalibrationTracker()


# ============================================================================
# MAIN PROBABILITY FUNCTION
# ============================================================================

def estimate_mention_probability(
    word: str,
    speaker: str = "trump",
    event_type: str = "speech",
    market_price: float = None,
    series_type: str = None,
) -> Tuple[Optional[float], Dict]:
    """
    Three-layer probability estimation for mention markets.
    
    Args:
        word: The word/phrase to estimate
        speaker: Who is speaking (e.g., "trump", "biden", "press_secretary")
        event_type: Type of event ("sotu", "rally", "weekly", "press")
        market_price: Current market YES price in cents (for blending)
        series_type: Market series type for logging
    
    Returns:
        (probability, metadata) where:
        - probability: 0-100 or None if should not trade
        - metadata: dict with layer contributions and confidence
    """
    metadata = {
        "word": word,
        "speaker": speaker,
        "event_type": event_type,
        "layers": {},
    }
    
    # =========================================================================
    # LAYER 1: Static Model
    # =========================================================================
    static_prob = None
    tier = 0
    tier_name = "UNKNOWN"
    
    if HAS_STATIC_MODEL:
        tier, tier_name, static_prob = classify_word_tier(word)
        
        if static_prob is not None:
            # Adjust for event type
            static_prob = get_base_probability(word, event_type) or static_prob
            metadata["layers"]["static"] = {
                "probability": static_prob,
                "tier": tier,
                "tier_name": tier_name,
            }
            logger.debug(f"Static model: {word} = {static_prob}% (Tier {tier})")
    
    # =========================================================================
    # LAYER 2: Dynamic LLM (for unknowns or low-confidence statics)
    # =========================================================================
    llm_prob = None
    llm_confidence = 0
    
    # Use LLM if: unknown word OR mid-tier word (want second opinion)
    use_llm = (static_prob is None) or (30 <= (static_prob or 50) <= 70)
    
    if use_llm and HAS_DYNAMIC_MODEL:
        market_dict = {
            "keyword": word,
            "event_title": f"{speaker} {event_type}",
            "series_type": series_type or "unknown",
            "yes_mid": market_price or 50,
        }
        
        llm_prob, llm_confidence = estimate_with_confidence(market_dict)
        
        if llm_prob is not None:
            metadata["layers"]["llm"] = {
                "probability": llm_prob,
                "confidence": llm_confidence,
            }
            logger.debug(f"LLM estimate: {word} = {llm_prob}% (conf={llm_confidence:.2f})")
    
    # =========================================================================
    # BLEND LAYERS
    # =========================================================================
    if static_prob is not None and llm_prob is not None:
        # Both available - blend based on confidence
        # Static model trusted more for known tiers
        if tier in [1, 2, 5, 6]:  # High/low confidence tiers
            static_weight = 0.8
        else:
            static_weight = 0.5
        
        llm_weight = 1 - static_weight
        raw_prob = static_prob * static_weight + llm_prob * llm_weight
        metadata["blend"] = "static+llm"
        
    elif static_prob is not None:
        raw_prob = static_prob
        metadata["blend"] = "static_only"
        
    elif llm_prob is not None:
        raw_prob = llm_prob
        metadata["blend"] = "llm_only"
        
    else:
        # No estimate available - don't trade
        logger.info(f"No probability estimate for {word}, skipping")
        metadata["blend"] = "none"
        return None, metadata
    
    # =========================================================================
    # LAYER 3: Calibration Adjustment
    # =========================================================================
    adjustment = _calibrator.get_adjustment(tier, raw_prob)
    calibrated_prob = raw_prob - adjustment
    
    # Clamp to valid range
    calibrated_prob = max(1, min(99, calibrated_prob))
    
    metadata["layers"]["calibration"] = {
        "raw": raw_prob,
        "adjustment": adjustment,
        "final": calibrated_prob,
    }
    
    # =========================================================================
    # OPTIONAL: Blend with market price (market knows things we don't)
    # =========================================================================
    if market_price is not None and 5 < market_price < 95:
        # Only blend if market price is reasonable
        # Our model: 70%, Market: 30%
        final_prob = calibrated_prob * 0.7 + market_price * 0.3
        metadata["market_blend"] = True
    else:
        final_prob = calibrated_prob
        metadata["market_blend"] = False
    
    metadata["final_probability"] = final_prob
    
    logger.info(f"Probability estimate for '{word}': {final_prob:.0f}% "
                f"(static={static_prob}, llm={llm_prob}, adj={adjustment:.1f})")
    
    return final_prob, metadata


def record_outcome(word: str, tier: int, predicted: float, actual_yes: bool,
                   series_type: str = None, event_type: str = None):
    """
    Record the actual outcome for calibration learning.
    
    Call this after each settlement to improve future predictions.
    """
    actual = 100.0 if actual_yes else 0.0
    _calibrator.record(word, tier, predicted, actual, series_type, event_type)
    
    error = predicted - actual
    logger.info(f"Calibration recorded: {word} predicted={predicted:.0f}% "
                f"actual={'YES' if actual_yes else 'NO'} error={error:+.0f}")


def get_calibration_stats() -> Dict:
    """Get current calibration statistics."""
    return _calibrator.summary


# ============================================================================
# DECISION HELPER
# ============================================================================

def should_trade(probability: float, market_yes: float, min_edge: float = 8) -> Tuple[bool, str, float]:
    """
    Decide if we should trade based on probability vs market price.
    
    Args:
        probability: Our estimated P(YES) in cents (0-100)
        market_yes: Market YES price in cents
        min_edge: Minimum edge required to trade (default 8¢)
    
    Returns:
        (should_trade, side, edge) where:
        - should_trade: True if edge is sufficient
        - side: "YES" or "NO"
        - edge: Expected edge in cents
    """
    # Calculate edges
    yes_edge = probability - market_yes  # Positive = YES underpriced
    no_edge = (100 - probability) - (100 - market_yes)  # = market_yes - probability
    
    if yes_edge >= min_edge:
        return True, "YES", yes_edge
    elif -yes_edge >= min_edge:  # no_edge = -yes_edge
        return True, "NO", -yes_edge
    else:
        return False, None, max(abs(yes_edge), abs(no_edge))


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("=" * 60)
    print("MENTION PROBABILITY V2 - THREE LAYER MODEL TEST")
    print("=" * 60)
    
    test_cases = [
        # (word, speaker, event_type, market_price)
        ("ukraine", "trump", "sotu", 75),
        ("peace in the middle east", "trump", "sotu", 70),
        ("hottest", "trump", "rally", 60),
        ("ballroom", "trump", "weekly", 15),
        ("armada", "trump", "weekly", 20),
        ("tariff", "trump", "sotu", 80),
        ("affordable", "trump", "weekly", 25),
        ("hochul", "mamdani", "press", 65),  # Unknown speaker
    ]
    
    print("\nTest Results:")
    print("-" * 60)
    
    for word, speaker, event_type, market in test_cases:
        prob, meta = estimate_mention_probability(
            word, speaker, event_type, market
        )
        
        if prob is not None:
            should, side, edge = should_trade(prob, market)
            trade_str = f"→ {side} (edge={edge:.0f}¢)" if should else "→ NO TRADE"
        else:
            trade_str = "→ SKIP (no model)"
        
        tier = meta.get("layers", {}).get("static", {}).get("tier", "?")
        print(f"{word:25} | P={prob or '?':>3}% | mkt={market}¢ | {trade_str}")
    
    print("\nCalibration Stats:")
    print(json.dumps(get_calibration_stats(), indent=2))
