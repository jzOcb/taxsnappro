#!/usr/bin/env python3
"""
Probability Scorer — Standalone module for estimating short-term crypto direction probability.

Estimates P(price goes UP in next 15 minutes) using a weighted scoring system.
KISS principle: no ML, just principled signal combination with proper normalization.

Usage:
    from probability_scorer import ProbabilityScorer
    scorer = ProbabilityScorer()
    result = scorer.estimate_probability(indicators, market_type='BTC')
    # result = {"prob_up": 0.62, "confidence": 0.45, "factors": {...}}
"""

import time
import math


class ProbabilityScorer:
    """
    Weighted scoring system for short-term crypto direction estimation.
    
    Each factor contributes a score between -1.0 (bearish) and +1.0 (bullish),
    weighted by importance. The aggregate is normalized to a probability [0, 1].
    
    Confidence reflects how many signals are available and how strongly they agree.
    """
    
    # Factor weights (sum to ~1.0 for interpretability, but normalization handles any sum)
    WEIGHTS = {
        'momentum_1m':   0.15,   # Short-term momentum (most responsive)
        'momentum_5m':   0.15,   # Medium-term momentum
        'momentum_15m':  0.10,   # Longer-term trend context
        'rsi':           0.10,   # Mean reversion signal
        'ls_ratio':      0.10,   # Contrarian crowd signal
        'bb_position':   0.10,   # Bollinger Band mean reversion
        'ema_trend':     0.15,   # Trend following signal
        'time_factor':   0.05,   # Time remaining adjustment (affects confidence more than direction)
        'volume_accel':  0.10,   # Volume acceleration
    }
    
    def __init__(self):
        pass
    
    def estimate_probability(self, indicators, market_type='BTC'):
        """
        Estimate probability of price going UP in the next 15 minutes.
        
        Args:
            indicators: dict with available indicator values:
                - momentum_1m: float, 1-minute price change % (e.g., 0.15 = +0.15%)
                - momentum_5m: float, 5-minute price change %
                - momentum_15m: float, 15-minute price change %
                - rsi: float, RSI(14) value 0-100
                - ls_ratio: float, OKX long/short ratio (1.0 = balanced)
                - bb_position: float, price position relative to BB (-1=lower, 0=middle, +1=upper)
                - bb_upper: float, upper Bollinger Band price
                - bb_lower: float, lower Bollinger Band price
                - bb_middle: float, middle Bollinger Band (SMA)
                - current_price: float, current asset price
                - ema_5: float, EMA(5) value
                - ema_20: float, EMA(20) value
                - ema_trend: str, 'bullish'/'bearish'/'neutral'
                - time_remaining_sec: float, seconds until 15min window closes
                - volume_ratio: float, recent volume / average volume (1.0 = normal)
            
            market_type: str, 'BTC' or 'ETH' (affects some thresholds)
        
        Returns:
            dict: {
                "prob_up": float 0.0-1.0,
                "confidence": float 0.0-1.0,
                "factors": {factor_name: {"score": float, "weight": float, "raw": any, "note": str}}
            }
        """
        factors = {}
        total_weight = 0.0
        weighted_score = 0.0
        available_count = 0
        
        # --- Factor 1: 1-minute momentum ---
        score, note, raw = self._score_momentum(indicators.get('momentum_1m'), '1m', market_type)
        if score is not None:
            w = self.WEIGHTS['momentum_1m']
            factors['momentum_1m'] = {'score': score, 'weight': w, 'raw': raw, 'note': note}
            weighted_score += score * w
            total_weight += w
            available_count += 1
        
        # --- Factor 2: 5-minute momentum ---
        score, note, raw = self._score_momentum(indicators.get('momentum_5m'), '5m', market_type)
        if score is not None:
            w = self.WEIGHTS['momentum_5m']
            factors['momentum_5m'] = {'score': score, 'weight': w, 'raw': raw, 'note': note}
            weighted_score += score * w
            total_weight += w
            available_count += 1
        
        # --- Factor 3: 15-minute momentum ---
        score, note, raw = self._score_momentum(indicators.get('momentum_15m'), '15m', market_type)
        if score is not None:
            w = self.WEIGHTS['momentum_15m']
            factors['momentum_15m'] = {'score': score, 'weight': w, 'raw': raw, 'note': note}
            weighted_score += score * w
            total_weight += w
            available_count += 1
        
        # --- Factor 4: RSI mean reversion ---
        score, note, raw = self._score_rsi(indicators.get('rsi'))
        if score is not None:
            w = self.WEIGHTS['rsi']
            factors['rsi'] = {'score': score, 'weight': w, 'raw': raw, 'note': note}
            weighted_score += score * w
            total_weight += w
            available_count += 1
        
        # --- Factor 5: Long/Short ratio (contrarian) ---
        score, note, raw = self._score_ls_ratio(indicators.get('ls_ratio'))
        if score is not None:
            w = self.WEIGHTS['ls_ratio']
            factors['ls_ratio'] = {'score': score, 'weight': w, 'raw': raw, 'note': note}
            weighted_score += score * w
            total_weight += w
            available_count += 1
        
        # --- Factor 6: Bollinger Band position ---
        score, note, raw = self._score_bb_position(indicators, market_type)
        if score is not None:
            w = self.WEIGHTS['bb_position']
            factors['bb_position'] = {'score': score, 'weight': w, 'raw': raw, 'note': note}
            weighted_score += score * w
            total_weight += w
            available_count += 1
        
        # --- Factor 7: EMA trend ---
        score, note, raw = self._score_ema_trend(indicators)
        if score is not None:
            w = self.WEIGHTS['ema_trend']
            factors['ema_trend'] = {'score': score, 'weight': w, 'raw': raw, 'note': note}
            weighted_score += score * w
            total_weight += w
            available_count += 1
        
        # --- Factor 8: Volume acceleration ---
        score, note, raw = self._score_volume(indicators.get('volume_ratio'))
        if score is not None:
            w = self.WEIGHTS['volume_accel']
            factors['volume_accel'] = {'score': score, 'weight': w, 'raw': raw, 'note': note}
            weighted_score += score * w
            total_weight += w
            available_count += 1
        
        # --- Factor 9: Time remaining (mostly affects confidence) ---
        time_remaining = indicators.get('time_remaining_sec')
        time_confidence_modifier = 1.0
        if time_remaining is not None:
            score, note, raw = self._score_time_factor(time_remaining)
            if score is not None:
                w = self.WEIGHTS['time_factor']
                factors['time_factor'] = {'score': score, 'weight': w, 'raw': raw, 'note': note}
                # Time factor doesn't really predict direction, but it multiplies momentum
                # Late in window + momentum = stronger signal
                # We apply it as a confidence modifier instead
                time_confidence_modifier = self._time_confidence(time_remaining)
        
        # --- Normalize to probability ---
        if total_weight > 0:
            # Normalized score in [-1, 1]
            normalized = weighted_score / total_weight
            # Map to probability [0, 1] via sigmoid-like transform
            # Using tanh/2 + 0.5 keeps it smooth and centered at 0.5
            prob_up = 0.5 + 0.5 * math.tanh(normalized * 2.0)
        else:
            prob_up = 0.5  # No signals = maximum uncertainty
        
        # --- Calculate confidence ---
        # Confidence based on: (1) how many signals available, (2) how strongly they agree, (3) time factor
        signal_availability = available_count / len(self.WEIGHTS)  # 0-1
        
        # Agreement: do signals point the same way?
        if available_count > 0:
            signs = [f['score'] for f in factors.values() if f['score'] != 0]
            if signs:
                positive = sum(1 for s in signs if s > 0)
                negative = sum(1 for s in signs if s < 0)
                agreement = abs(positive - negative) / len(signs)
            else:
                agreement = 0.0
        else:
            agreement = 0.0
        
        # Signal strength: how far from 0.5 is the probability?
        strength = abs(prob_up - 0.5) * 2  # 0-1
        
        # Combine: availability * agreement * time_modifier, weighted
        confidence = (
            0.3 * signal_availability +
            0.4 * agreement +
            0.3 * strength
        ) * time_confidence_modifier
        
        confidence = max(0.0, min(1.0, confidence))
        
        return {
            'prob_up': round(prob_up, 4),
            'confidence': round(confidence, 4),
            'factors': factors
        }
    
    def calculate_ev(self, prob_up, direction, kalshi_price, fee_rate=0.07):
        """
        Calculate Expected Value for a Kalshi binary option trade.
        
        Args:
            prob_up: float, estimated probability of price going up
            direction: str, 'YES' or 'NO'
            kalshi_price: float, the Kalshi contract price we'd pay (0-1)
            fee_rate: float, Kalshi fee as fraction of payout (default 7% = $0.07 per $1)
        
        Returns:
            dict: {
                "ev": float (expected value in dollars per $1 risked),
                "edge": float (our probability - market implied probability),
                "kelly_fraction": float (optimal bet fraction),
                "details": str
            }
        """
        if direction == 'YES':
            # Buying YES at kalshi_price
            # Win: pay kalshi_price, receive $1.00, net = (1 - kalshi_price) - fee
            # Lose: pay kalshi_price, receive $0, net = -kalshi_price
            prob_win = prob_up
            win_payout = (1.0 - kalshi_price) - (fee_rate * (1.0 - kalshi_price))  # Net win after fee
            loss_amount = kalshi_price  # Total loss
        else:
            # Buying NO at (1 - kalshi_price) effectively
            # Win: price goes DOWN, we profit
            # Lose: price goes UP, we lose
            prob_win = 1.0 - prob_up
            no_price = 1.0 - kalshi_price  # What we pay for NO
            win_payout = kalshi_price - (fee_rate * kalshi_price)  # Net win after fee
            loss_amount = no_price  # Total loss
        
        ev = prob_win * win_payout - (1.0 - prob_win) * loss_amount
        
        # Edge: our estimated prob vs implied market prob
        implied_prob = kalshi_price if direction == 'YES' else (1.0 - kalshi_price)
        edge = prob_win - implied_prob
        
        # Kelly fraction (half-Kelly for safety)
        if loss_amount > 0 and win_payout > 0:
            b = win_payout / loss_amount  # Odds ratio
            kelly_full = (prob_win * b - (1.0 - prob_win)) / b
            kelly_half = max(0, kelly_full / 2)
        else:
            kelly_half = 0.0
        
        details = (
            f"P(win)={prob_win:.3f} win=${win_payout:.3f} lose=${loss_amount:.3f} "
            f"implied={implied_prob:.3f} edge={edge:+.3f}"
        )
        
        return {
            'ev': round(ev, 4),
            'edge': round(edge, 4),
            'kelly_fraction': round(kelly_half, 4),
            'details': details
        }
    
    # ========== Individual factor scoring functions ==========
    
    def _score_momentum(self, momentum_pct, timeframe, market_type):
        """
        Score momentum signal. Returns (score, note, raw) or (None, None, None).
        Score in [-1, 1]: positive = bullish, negative = bearish.
        """
        if momentum_pct is None:
            return None, None, None
        
        # ETH has wider typical momentum ranges
        scale = 0.15 if market_type == 'BTC' else 0.20
        
        # Timeframe adjustments: longer timeframes need larger moves to matter
        if timeframe == '5m':
            scale *= 2.0
        elif timeframe == '15m':
            scale *= 3.0
        
        # Sigmoid-like scoring: saturates at ±1 for large moves
        score = math.tanh(momentum_pct / scale)
        
        direction = "bullish" if score > 0 else "bearish" if score < 0 else "neutral"
        note = f"{timeframe} {momentum_pct:+.3f}% → {direction}"
        
        return score, note, momentum_pct
    
    def _score_rsi(self, rsi):
        """
        RSI mean reversion signal.
        <30: bullish (oversold, expect bounce)
        >70: bearish (overbought, expect pullback)
        30-70: weak/no signal
        """
        if rsi is None:
            return None, None, None
        
        if rsi < 20:
            score = 0.8  # Strongly oversold → bullish
            note = f"RSI={rsi:.0f} strongly oversold"
        elif rsi < 30:
            score = 0.4  # Oversold → mildly bullish
            note = f"RSI={rsi:.0f} oversold"
        elif rsi > 80:
            score = -0.8  # Strongly overbought → bearish
            note = f"RSI={rsi:.0f} strongly overbought"
        elif rsi > 70:
            score = -0.4  # Overbought → mildly bearish
            note = f"RSI={rsi:.0f} overbought"
        elif rsi > 55:
            score = -0.1  # Slightly overbought zone
            note = f"RSI={rsi:.0f} slightly elevated"
        elif rsi < 45:
            score = 0.1  # Slightly oversold zone
            note = f"RSI={rsi:.0f} slightly depressed"
        else:
            score = 0.0  # Neutral zone
            note = f"RSI={rsi:.0f} neutral"
        
        return score, note, rsi
    
    def _score_ls_ratio(self, ls_ratio):
        """
        Contrarian signal from OKX long/short ratio.
        Extreme long (>2.0) → bearish (crowd usually wrong at extremes)
        Extreme short (<0.5) → bullish
        """
        if ls_ratio is None:
            return None, None, None
        
        if ls_ratio > 3.0:
            score = -0.7  # Very crowded long → strong bearish
            note = f"LS={ls_ratio:.1f} very crowded long"
        elif ls_ratio > 2.0:
            score = -0.4  # Crowded long → bearish
            note = f"LS={ls_ratio:.1f} crowded long"
        elif ls_ratio > 1.5:
            score = -0.15  # Mildly long → slight bearish
            note = f"LS={ls_ratio:.1f} slightly long"
        elif ls_ratio < 0.33:
            score = 0.7  # Very crowded short → strong bullish
            note = f"LS={ls_ratio:.1f} very crowded short"
        elif ls_ratio < 0.5:
            score = 0.4  # Crowded short → bullish
            note = f"LS={ls_ratio:.1f} crowded short"
        elif ls_ratio < 0.67:
            score = 0.15  # Mildly short → slight bullish
            note = f"LS={ls_ratio:.1f} slightly short"
        else:
            score = 0.0  # Balanced
            note = f"LS={ls_ratio:.1f} balanced"
        
        return score, note, ls_ratio
    
    def _score_bb_position(self, indicators, market_type):
        """
        Bollinger Band position: mean reversion signal.
        Below lower band → bullish (expect bounce to middle)
        Above upper band → bearish (expect pullback)
        """
        # Try explicit bb_position first
        bb_pos = indicators.get('bb_position')
        if bb_pos is not None:
            raw = bb_pos
        else:
            # Calculate from components
            current_price = indicators.get('current_price')
            bb_upper = indicators.get('bb_upper')
            bb_lower = indicators.get('bb_lower')
            bb_middle = indicators.get('bb_middle')
            
            if None in (current_price, bb_upper, bb_lower, bb_middle):
                return None, None, None
            
            bb_range = bb_upper - bb_lower
            if bb_range <= 0:
                return None, None, None
            
            # Position: -1 = at lower band, 0 = at middle, +1 = at upper band
            raw = (current_price - bb_middle) / (bb_range / 2)
        
        # Contrarian: at extremes, expect reversion
        if raw > 1.5:
            score = -0.6  # Far above upper band → bearish
            note = f"BB pos={raw:+.2f} well above upper"
        elif raw > 1.0:
            score = -0.3  # Above upper band → mildly bearish
            note = f"BB pos={raw:+.2f} above upper"
        elif raw < -1.5:
            score = 0.6  # Far below lower band → bullish
            note = f"BB pos={raw:+.2f} well below lower"
        elif raw < -1.0:
            score = 0.3  # Below lower band → mildly bullish
            note = f"BB pos={raw:+.2f} below lower"
        elif raw > 0.5:
            score = -0.1  # Upper half → slight bearish bias
            note = f"BB pos={raw:+.2f} upper half"
        elif raw < -0.5:
            score = 0.1  # Lower half → slight bullish bias
            note = f"BB pos={raw:+.2f} lower half"
        else:
            score = 0.0  # Near middle
            note = f"BB pos={raw:+.2f} near middle"
        
        return score, note, raw
    
    def _score_ema_trend(self, indicators):
        """
        EMA trend: EMA5 vs EMA20 crossover signal.
        EMA5 > EMA20 → bullish trend
        EMA5 < EMA20 → bearish trend
        """
        ema_trend = indicators.get('ema_trend')
        ema_5 = indicators.get('ema_5')
        ema_20 = indicators.get('ema_20')
        
        if ema_trend is not None:
            if ema_trend == 'bullish':
                # Calculate strength from EMA spread
                if ema_5 is not None and ema_20 is not None and ema_20 > 0:
                    spread_pct = (ema_5 - ema_20) / ema_20 * 100
                    score = min(0.8, max(0.1, spread_pct * 5))  # Scale spread to score
                else:
                    score = 0.3
                note = f"EMA5>EMA20 bullish trend"
                raw = 'bullish'
            elif ema_trend == 'bearish':
                if ema_5 is not None and ema_20 is not None and ema_20 > 0:
                    spread_pct = (ema_5 - ema_20) / ema_20 * 100
                    score = max(-0.8, min(-0.1, spread_pct * 5))
                else:
                    score = -0.3
                note = f"EMA5<EMA20 bearish trend"
                raw = 'bearish'
            else:
                score = 0.0
                note = "EMA neutral"
                raw = 'neutral'
            return score, note, raw
        
        # Fall back to computing from raw values
        if ema_5 is None or ema_20 is None:
            return None, None, None
        
        if ema_20 == 0:
            return None, None, None
        
        spread_pct = (ema_5 - ema_20) / ema_20 * 100
        score = math.tanh(spread_pct * 5)  # Saturates nicely
        
        if score > 0.05:
            note = f"EMA5>EMA20 ({spread_pct:+.3f}%) bullish"
        elif score < -0.05:
            note = f"EMA5<EMA20 ({spread_pct:+.3f}%) bearish"
        else:
            note = f"EMA flat ({spread_pct:+.3f}%)"
        
        return score, note, spread_pct
    
    def _score_volume(self, volume_ratio):
        """
        Volume acceleration: high volume in direction of trend = confirmation.
        This factor amplifies the existing direction rather than predicting one.
        High volume = more conviction in whatever direction we're seeing.
        We encode this as a mild positive bias (trending continuation).
        """
        if volume_ratio is None:
            return None, None, None
        
        # Volume itself doesn't predict direction, but very high volume
        # during a trend is confirmation. We use a small score that
        # gets amplified when combined with momentum.
        if volume_ratio > 3.0:
            score = 0.15  # High volume = slight bullish bias (trend continuation)
            note = f"vol={volume_ratio:.1f}x high activity"
        elif volume_ratio > 2.0:
            score = 0.05
            note = f"vol={volume_ratio:.1f}x elevated"
        elif volume_ratio < 0.3:
            score = 0.0  # Low volume = no signal
            note = f"vol={volume_ratio:.1f}x very low"
        else:
            score = 0.0
            note = f"vol={volume_ratio:.1f}x normal"
        
        return score, note, volume_ratio
    
    def _score_time_factor(self, time_remaining_sec):
        """
        Time remaining in 15-min window.
        Not a directional signal — mostly affects confidence.
        Late in window with clear momentum → higher confidence.
        """
        if time_remaining_sec is None:
            return None, None, None
        
        # No directional score from time alone
        score = 0.0
        
        if time_remaining_sec < 60:
            note = f"T-{time_remaining_sec:.0f}s very late"
        elif time_remaining_sec < 300:
            note = f"T-{time_remaining_sec:.0f}s late window"
        elif time_remaining_sec < 600:
            note = f"T-{time_remaining_sec:.0f}s mid window"
        else:
            note = f"T-{time_remaining_sec:.0f}s early window"
        
        return score, note, time_remaining_sec
    
    def _time_confidence(self, time_remaining_sec):
        """
        Time-based confidence modifier.
        Later in window = more confident (less time for reversal).
        Returns multiplier 0.5-1.0
        """
        if time_remaining_sec is None:
            return 0.7  # Default moderate confidence
        
        # Linear ramp: 900s (full window) → 0.5, 0s (settlement) → 1.0
        max_window = 900  # 15 minutes
        fraction_elapsed = 1.0 - min(time_remaining_sec, max_window) / max_window
        
        # Map to 0.5 - 1.0 range
        return 0.5 + 0.5 * fraction_elapsed


# Convenience function for quick testing
def quick_score(momentum_1m=None, momentum_5m=None, rsi=None, ema_trend=None, market='BTC'):
    """Quick scoring with minimal inputs for testing."""
    scorer = ProbabilityScorer()
    indicators = {}
    if momentum_1m is not None:
        indicators['momentum_1m'] = momentum_1m
    if momentum_5m is not None:
        indicators['momentum_5m'] = momentum_5m
    if rsi is not None:
        indicators['rsi'] = rsi
    if ema_trend is not None:
        indicators['ema_trend'] = ema_trend
    return scorer.estimate_probability(indicators, market)


if __name__ == '__main__':
    # Self-test
    scorer = ProbabilityScorer()
    
    # Test 1: Strong bullish signals
    result = scorer.estimate_probability({
        'momentum_1m': 0.20,
        'momentum_5m': 0.35,
        'momentum_15m': 0.50,
        'rsi': 45,
        'ls_ratio': 0.8,
        'ema_trend': 'bullish',
        'bb_position': -0.5,
        'volume_ratio': 2.5,
        'time_remaining_sec': 300,
    }, 'BTC')
    print(f"Bullish test: prob_up={result['prob_up']:.3f} conf={result['confidence']:.3f}")
    assert result['prob_up'] > 0.6, f"Expected >0.6, got {result['prob_up']}"
    
    # Test 2: Strong bearish signals
    result = scorer.estimate_probability({
        'momentum_1m': -0.25,
        'momentum_5m': -0.40,
        'momentum_15m': -0.60,
        'rsi': 75,
        'ls_ratio': 2.5,
        'ema_trend': 'bearish',
        'bb_position': 1.2,
        'volume_ratio': 1.0,
        'time_remaining_sec': 200,
    }, 'BTC')
    print(f"Bearish test: prob_up={result['prob_up']:.3f} conf={result['confidence']:.3f}")
    assert result['prob_up'] < 0.4, f"Expected <0.4, got {result['prob_up']}"
    
    # Test 3: Mixed/neutral signals
    result = scorer.estimate_probability({
        'momentum_1m': 0.05,
        'momentum_5m': -0.02,
        'rsi': 50,
        'ema_trend': 'neutral',
    }, 'BTC')
    print(f"Neutral test: prob_up={result['prob_up']:.3f} conf={result['confidence']:.3f}")
    assert 0.4 < result['prob_up'] < 0.6, f"Expected ~0.5, got {result['prob_up']}"
    
    # Test 4: EV calculation
    ev_result = scorer.calculate_ev(prob_up=0.65, direction='YES', kalshi_price=0.55)
    print(f"EV test: ev=${ev_result['ev']:.4f} edge={ev_result['edge']:+.3f} kelly={ev_result['kelly_fraction']:.3f}")
    assert ev_result['ev'] > 0, f"Expected positive EV, got {ev_result['ev']}"
    
    # Test 5: No data
    result = scorer.estimate_probability({}, 'BTC')
    print(f"No data test: prob_up={result['prob_up']:.3f} conf={result['confidence']:.3f}")
    assert result['prob_up'] == 0.5, f"Expected 0.5, got {result['prob_up']}"
    assert result['confidence'] == 0.0, f"Expected 0.0 confidence, got {result['confidence']}"
    
    print("\n✅ All probability_scorer tests passed!")
