#!/usr/bin/env python3
"""
Trump Speech Word Probability Model

Based on analysis of Trump's speaking patterns:
1. Historical SOTU speeches (2017-2020)
2. Rally speech patterns
3. Common Trump vocabulary

Categories:
- TIER_1_CERTAIN (95%+): Words Trump ALWAYS uses
- TIER_2_LIKELY (80-95%): Policy topics, common phrases
- TIER_3_PROBABLE (50-80%): General political terms
- TIER_4_POSSIBLE (20-50%): Specific but not guaranteed
- TIER_5_UNLIKELY (5-20%): Uncommon words
- TIER_6_RARE (<5%): Random/unusual words
"""

# Words Trump uses in almost EVERY speech (95%+)
TIER_1_CERTAIN = {
    # Self-references
    "trump", "president", "administration", "i", "we", "me", "my",
    # Superlatives (Trump signature) - HE ALWAYS USES THESE
    "great", "greatest", "best", "biggest", "tremendous", "incredible",
    "beautiful", "amazing", "fantastic", "wonderful", "hottest", "strongest",
    "worst", "terrible", "horrible", "disaster",
    # Core themes
    "america", "american", "americans", "country", "nation", "people",
    "world", "history", "future", "united states",
    # Action words
    "win", "winning", "fight", "fighting", "work", "working",
    # Common policy
    "jobs", "economy", "border", "security", "military",
    # Numbers he loves
    "million", "billion", "trillion", "percent",
}

# Current hot topics + frequently mentioned (80-95%)
TIER_2_LIKELY = {
    # Foreign policy (2025-2026 context)
    "ukraine", "russia", "china", "israel", "iran", "north korea",
    "tariff", "tariffs", "trade", "deal", "peace", "war",
    # Key phrases - VERY likely in political speeches
    "peace in the middle east", "middle east", "make america great",
    # Domestic policy
    "immigration", "illegal", "crime", "inflation", "tax", "taxes",
    "energy", "oil", "gas", "drill", "drilling", "manufacture", 
    "manufacturing", "factory", "factories",
    # Political targets
    "biden", "democrats", "radical", "left", "fake news", "media",
    "congress", "senate",
    # Positive emotions
    "love", "proud", "honor", "thank", "god", "bless",
    # Common words
    "never", "ever", "before", "first", "last", "new", "old",
    # More superlatives/intensifiers
    "very", "really", "absolutely", "totally", "completely",
}

# General political vocabulary (50-80%)
TIER_3_PROBABLE = {
    # Policy areas
    "healthcare", "education", "infrastructure", "veterans",
    "police", "law enforcement", "justice",
    # Geography
    "washington", "california", "texas", "florida", "new york",
    "mexico", "canada", "europe", "asia", "middle east",
    # Economics
    "business", "companies", "workers", "families", "money",
    "billion", "million", "trillion", "dollars",
    # Government
    "congress", "senate", "house", "supreme court", "constitution",
    # Military
    "army", "navy", "air force", "troops", "soldiers",
    # Time
    "today", "tomorrow", "yesterday", "years", "months", "days",
}

# Specific but not guaranteed (20-50%)
TIER_4_POSSIBLE = {
    # Specific policies
    "medicare", "medicaid", "social security", "obamacare",
    "regulation", "deregulation", "bureaucracy",
    # Specific countries
    "germany", "france", "japan", "saudi arabia", "venezuela",
    "afghanistan", "iraq", "syria",
    # Tech/modern
    "technology", "internet", "cyber", "ai", "artificial intelligence",
    # Less common but possible
    "beautiful", "strength", "power", "peace", "freedom", "liberty",
}

# Uncommon words (5-20%)
TIER_5_UNLIKELY = {
    # Random objects
    "car", "phone", "computer", "book",
    # Unusual for political speech
    "penguin", "dinosaur", "pizza", "coffee",
    # Entertainment
    "movie", "music", "sports", "football", "basketball",
    # Specific names (context dependent)
    "elon", "musk", "bezos", "zuckerberg",
}

# Words Trump would almost never say (<5%)
TIER_6_RARE = {
    # Random nouns
    "armada", "ballroom", "chandelier", "xylophone",
    # Unlikely topics
    "quantum", "photosynthesis", "archaeology",
    # Foreign words
    "schadenfreude", "zeitgeist",
}

def _check_phrase_match(phrase: str, word_set: set) -> bool:
    """Check if phrase or any word in it matches the set."""
    phrase_lower = phrase.lower().strip()
    
    # Direct match
    if phrase_lower in word_set:
        return True
    
    # Check individual words
    words = phrase_lower.replace("/", " ").replace("-", " ").split()
    for w in words:
        if w in word_set:
            return True
    
    return False


def get_base_probability(word: str, event_type: str = "speech") -> float:
    """
    Get base probability for a word in Trump speech.
    
    Args:
        word: The word/phrase to estimate
        event_type: 'sotu', 'rally', 'press', 'weekly'
    
    Returns:
        Probability 0-100
    """
    word_lower = word.lower().strip()
    
    # Check tiers with phrase matching
    if _check_phrase_match(word_lower, TIER_1_CERTAIN):
        base = 97
    elif _check_phrase_match(word_lower, TIER_2_LIKELY):
        base = 87
    elif _check_phrase_match(word_lower, TIER_3_PROBABLE):
        base = 65
    elif _check_phrase_match(word_lower, TIER_4_POSSIBLE):
        base = 35
    elif _check_phrase_match(word_lower, TIER_5_UNLIKELY):
        base = 12
    elif _check_phrase_match(word_lower, TIER_6_RARE):
        base = 3
    else:
        # Unknown word - need LLM classification
        base = None
    
    if base is None:
        return None
    
    # Event type modifiers
    if event_type == "sotu":
        # SOTU is longer, more comprehensive - bump up middle tiers
        if base < 50:
            base = min(base + 15, 70)
    elif event_type == "rally":
        # Rallies are more casual, less policy-heavy
        if word_lower in TIER_3_PROBABLE:
            base -= 10
    
    return base


def classify_word_tier(word: str) -> tuple:
    """
    Classify a word into a tier.
    
    Returns:
        (tier_number, tier_name, base_probability)
    """
    word_lower = word.lower().strip()
    
    if _check_phrase_match(word_lower, TIER_1_CERTAIN):
        return (1, "CERTAIN", 97)
    elif _check_phrase_match(word_lower, TIER_2_LIKELY):
        return (2, "LIKELY", 87)
    elif _check_phrase_match(word_lower, TIER_3_PROBABLE):
        return (3, "PROBABLE", 65)
    elif _check_phrase_match(word_lower, TIER_4_POSSIBLE):
        return (4, "POSSIBLE", 35)
    elif _check_phrase_match(word_lower, TIER_5_UNLIKELY):
        return (5, "UNLIKELY", 12)
    elif _check_phrase_match(word_lower, TIER_6_RARE):
        return (6, "RARE", 3)
    else:
        return (0, "UNKNOWN", None)


if __name__ == "__main__":
    # Test with words from our losses
    test_words = [
        "ukraine", "peace", "hottest", "manufacture", "hochul",
        "affordable", "ballroom", "tariff", "biden", "armada"
    ]
    
    print("Word Classification Test:")
    print("-" * 50)
    for word in test_words:
        tier, name, prob = classify_word_tier(word)
        prob_str = f"{prob}%" if prob else "UNKNOWN"
        print(f"  {word:20} → Tier {tier} ({name}) = {prob_str}")
