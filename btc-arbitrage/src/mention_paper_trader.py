#!/usr/bin/env python3
"""
Mention Market Multi-Series Paper Trading Bot
===============================================
Scans ALL major mention market series on Kalshi and Polymarket, identifies
overpriced YES (= underpriced NO) AND underpriced sure-thing YES, and
paper-trades to collect premium.

Core thesis (NO Grinder): YES is structurally overpriced on mention markets:
  - Retail loves cheap lottery-ticket YES bets
  - Emotional/wishful thinking inflates unlikely mentions
  - Most words simply don't get said → NO resolves to $1

Added thesis (Sure-Thing YES): Some words are near-certain to be said:
  - Buy YES when market price < 85¢ but our estimate > 95%
  - Small edge but very high win rate

Series covered:
  - Trump weekly/monthly/episode/nickname/event/SOTU
  - White House press briefing
  - NFL/NBA sports announcer mentions
  - Earnings calls (AMZN, META, TSLA, NVDA, Coinbase, etc.)
  - Entertainment (Green Day, MrBeast, etc.)
  - Polymarket mention events

Usage:
    python3 -u src/mention_paper_trader.py
"""

import sys
import os
import json
import time
import signal
import logging
import traceback
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import requests

# V2 Three-layer probability system
try:
    from mention_probability_v2 import (
        estimate_mention_probability, 
        record_outcome, 
        should_trade,
        get_calibration_stats
    )
    HAS_V2_PROB = True
except ImportError:
    HAS_V2_PROB = False

# Legacy dynamic probability (fallback)
try:
    from dynamic_probability import get_dynamic_probability
    HAS_DYNAMIC_PROB = True
except ImportError:
    HAS_DYNAMIC_PROB = False

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paper trading limits (upgraded for multi-series)
MAX_PER_MARKET = 50.0        # Default max per market (overridden by series limits)
MAX_TOTAL_EXPOSURE = 1500.0   # $1500 total (was $500 — more series = more diversification)
STARTING_BANKROLL = 2000.0    # Paper bankroll (was $1000)

# Edge thresholds (in cents, 1-100 scale)
MIN_EDGE_CENTS = 10           # Need 10¢ edge to trade
MIN_NO_PRICE = 60             # Don't buy NO below 60¢ (YES above 40¢ is risky)
MAX_NO_PRICE = 60             # Never buy NO above 60¢
MIN_EDGE_FRACTION = 0.10      # 10 percentage points minimum edge

# Sure-Thing YES thresholds
SURE_THING_YES_MIN_FAIR = 0.95   # Our estimate must be >95%
SURE_THING_YES_MAX_PRICE = 85    # Market price must be <85¢ (implied prob)
SURE_THING_YES_MIN_EDGE = 10     # At least 10¢ edge (our - market)

# Scan intervals (seconds)
SCAN_INTERVAL = 900           # 15 minutes
STATUS_INTERVAL = 3600        # 1 hour
SETTLEMENT_CHECK_INTERVAL = 300  # 5 minutes

# API endpoints
KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"
POLYMARKET_BASE = "https://gamma-api.polymarket.com"

# ============================================================================
# MULTI-SERIES CONFIGURATION
# ============================================================================

# All Kalshi mention series to scan
KALSHI_MENTION_SERIES = [
    # Trump speech/events
    'KXTRUMPMENTION',        # SOTU mentions (94 markets, $568K vol)
    'KXTRUMPSAY',            # Weekly (11 markets)
    'KXTRUMPSAYMONTH',       # Monthly (20 markets, $32K)
    'KXTRUMPSAYEP',          # Episode/special
    'KXTRUMPMENTIONB',       # Tomorrow's announcement (17 markets)
    'KXTRUMPSAYNICKNAME',    # Nicknames (15 markets, $88K)

    # White House
    'KXSECPRESSMENTION',     # Press briefing (25 markets, $454K)

    # Sports
    'KXNFLMENTION',          # Super Bowl (36 markets, $929K!)
    'KXNBAMENTION',          # NBA game mentions

    # Earnings
    'KXEARNINGSMENTIONAMZN',    # Amazon earnings
    'KXEARNINGSMENTIONMETA',    # Meta earnings
    'KXEARNINGSMENTIONTSLA',    # Tesla earnings
    'KXEARNINGSMENTIONNVDA',    # NVIDIA earnings
    'KXEARNINGSMENTIONCOINBASE', # Coinbase earnings
    'KXEARNINGSMENTIONEA',      # EA earnings
    'KXEARNINGSMENTIONRDDT',    # Reddit earnings
    'KXEARNINGSMENTIONNBIS',    # Nebius earnings

    # Entertainment
    'KXGREENDAYMENTION',     # Green Day at Super Bowl
    'KXMRBEASTMENTION',      # MrBeast video

    # Other events (lower volume, still worth scanning)
    'KXWOMENTION',           # Winter Olympics
    'KXNCAABMENTION',        # College basketball
    'KXFIGHTMENTION',        # Fight mentions
    'KXMAMDANIMENTION',      # Mamdani announcement
]

# Map series tickers to series types for probability models & limits
SERIES_TYPE_MAP = {
    'KXTRUMPSAY': 'trump_weekly',
    'KXTRUMPSAYEP': 'trump_weekly',         # episodes treated as weekly
    'KXTRUMPSAYMONTH': 'trump_monthly',
    'KXTRUMPMENTION': 'trump_sotu',
    'KXTRUMPMENTIONB': 'trump_event',
    'KXTRUMPSAYNICKNAME': 'trump_nickname',
    'KXSECPRESSMENTION': 'press_briefing',
    'KXNFLMENTION': 'sports_nfl',
    'KXNBAMENTION': 'sports_nba',
    'KXNCAABMENTION': 'sports_nba',         # college hoops similar
    'KXFIGHTMENTION': 'sports_nfl',         # fighting similar to sports commentary
    'KXEARNINGSMENTIONAMZN': 'earnings',
    'KXEARNINGSMENTIONMETA': 'earnings',
    'KXEARNINGSMENTIONTSLA': 'earnings',
    'KXEARNINGSMENTIONNVDA': 'earnings',
    'KXEARNINGSMENTIONCOINBASE': 'earnings',
    'KXEARNINGSMENTIONEA': 'earnings',
    'KXEARNINGSMENTIONRDDT': 'earnings',
    'KXEARNINGSMENTIONNBIS': 'earnings',
    'KXGREENDAYMENTION': 'entertainment',
    'KXMRBEASTMENTION': 'entertainment',
    'KXWOMENTION': 'entertainment',
    'KXMAMDANIMENTION': 'entertainment',
}

# Position limits per series type
SERIES_LIMITS = {
    'trump_weekly':    {'max_per_market': 50,  'max_series_exposure': 200},
    'trump_monthly':   {'max_per_market': 50,  'max_series_exposure': 200},
    'trump_sotu':      {'max_per_market': 100, 'max_series_exposure': 500},
    'trump_event':     {'max_per_market': 50,  'max_series_exposure': 150},
    'trump_nickname':  {'max_per_market': 50,  'max_series_exposure': 200},
    'press_briefing':  {'max_per_market': 75,  'max_series_exposure': 300},
    'sports_nfl':      {'max_per_market': 100, 'max_series_exposure': 400},
    'sports_nba':      {'max_per_market': 30,  'max_series_exposure': 100},
    'earnings':        {'max_per_market': 50,  'max_series_exposure': 200},
    'entertainment':   {'max_per_market': 50,  'max_series_exposure': 150},
    'unknown':         {'max_per_market': 30,  'max_series_exposure': 100},
}

# Kalshi keywords for broader event discovery
KALSHI_KEYWORDS = [
    "mention", "say", "said", "word", "talk", "tweet",
    "earnings", "sotu", "state of the union", "press briefing",
    "briefing", "speech", "prayer", "nickname", "super bowl",
    "announcer", "broadcast", "nfl", "nba",
]

# Polymarket search terms
POLYMARKET_SEARCH_TERMS = [
    "trump say", "what will trump", "mention",
    "will be said", "earnings call", "press briefing",
    "state of the union",
]

# File paths
STATE_FILE = Path("/home/clawdbot/clawd/btc-arbitrage/mention_trader_state.json")
LOG_FILE = Path("/home/clawdbot/clawd/btc-arbitrage/logs/mention_trader_live.log")

# ============================================================================
# DATA-DRIVEN PROBABILITY MODEL
# ============================================================================

_FREQ_FILE = Path("/home/clawdbot/clawd/btc-arbitrage/research/mention/trump_word_frequencies.json")
_FREQ_DATA = {}
if _FREQ_FILE.exists():
    try:
        with open(_FREQ_FILE) as _f:
            _FREQ_DATA = json.load(_f)
    except Exception:
        pass


def _load_base_rates():
    """Build a flat dict of keyword → weekly probability from the calibration data."""
    rates = {}
    weekly = _FREQ_DATA.get("weekly_base_rates", {})
    for category in ["near_certain", "high", "medium", "low"]:
        cat_data = weekly.get(category, {})
        for word, prob in cat_data.items():
            if word.startswith("_"):
                continue
            rates[word.lower()] = prob
    return rates


TRUMP_WEEKLY_BASE_RATES = _load_base_rates()

# High-frequency blocklist: NEVER sell NO on these for Trump weekly/monthly
HIGH_FREQ_BLOCKLIST = set(w.lower() for w in _FREQ_DATA.get("known_high_frequency_blocklist", []))

# Event type adjustments from calibration data
EVENT_ADJUSTMENTS = _FREQ_DATA.get("event_type_multipliers", {})

# Monthly multiplier
MONTHLY_MULTIPLIER = _FREQ_DATA.get("monthly_multiplier", 1.5)

# Earnings default base rate
EARNINGS_DEFAULT_BASE_RATE = 0.15

# ============================================================================
# SPORTS PROBABILITY MODEL
# ============================================================================

# Words very likely to be said by NFL/NBA announcers during a game broadcast
SPORTS_HIGH_PROB_WORDS = {
    # NFL common commentary words
    'touchdown': 0.98, 'field goal': 0.95, 'interception': 0.75,
    'fumble': 0.70, 'penalty': 0.95, 'first down': 0.98,
    'quarterback': 0.98, 'defense': 0.98, 'offense': 0.98,
    'halftime': 0.98, 'kickoff': 0.98, 'punt': 0.90,
    'sack': 0.80, 'tackle': 0.95, 'yard': 0.99, 'yards': 0.99,
    'pass': 0.99, 'run': 0.95, 'catch': 0.95, 'throw': 0.95,
    'score': 0.99, 'play': 0.99, 'game': 0.99, 'team': 0.99,
    'coach': 0.95, 'referee': 0.60, 'challenge': 0.60,
    'timeout': 0.90, 'clock': 0.90, 'quarter': 0.98,
    'replay': 0.80, 'review': 0.70, 'safety': 0.50,
    'endzone': 0.85, 'end zone': 0.85, 'snap': 0.85,
    'huddle': 0.60, 'blitz': 0.50, 'scramble': 0.50,
    'roughing': 0.30, 'holding': 0.80, 'offside': 0.60,
    'incomplete': 0.85, 'complete': 0.90, 'reception': 0.80,
    'rush': 0.80, 'rushing': 0.80, 'passing': 0.90,
    'super bowl': 0.95, 'championship': 0.80, 'trophy': 0.60,
    'mvp': 0.60, 'record': 0.70, 'season': 0.85,
    'win': 0.95, 'loss': 0.60, 'lead': 0.90,
    'drive': 0.90, 'march': 0.50, 'red zone': 0.70,
    # NBA common commentary words
    'three-pointer': 0.95, 'dunk': 0.80, 'rebound': 0.95,
    'assist': 0.90, 'steal': 0.75, 'block': 0.80,
    'foul': 0.95, 'free throw': 0.90, 'layup': 0.80,
    'fast break': 0.60, 'alley-oop': 0.30, 'buzzer': 0.50,
    'overtime': 0.25, 'double-double': 0.40, 'triple-double': 0.15,
}

# Words very UNLIKELY to be said by sports announcers
SPORTS_LOW_PROB_WORDS = {
    'trump': 0.25, 'biden': 0.05, 'maga': 0.03,
    'tariff': 0.02, 'immigration': 0.03, 'border': 0.05,
    'election': 0.05, 'congress': 0.05, 'senate': 0.03,
    'crypto': 0.02, 'bitcoin': 0.02, 'inflation': 0.03,
    'epstein': 0.01, 'ukraine': 0.02, 'russia': 0.03,
    'iran': 0.01, 'china': 0.05, 'fentanyl': 0.01,
    'woke': 0.02, 'dei': 0.02, 'transgender': 0.02,
    'marijuana': 0.01, 'communist': 0.01,
}

# ============================================================================
# EARNINGS PROBABILITY MODEL
# ============================================================================

# Words highly likely in earnings calls, per company
EARNINGS_COMPANY_WORDS = {
    'KXEARNINGSMENTIONAMZN': {
        'high': ['aws', 'cloud', 'prime', 'alexa', 'marketplace', 'fulfillment',
                 'delivery', 'advertising', 'subscription', 'seller', 'customer',
                 'revenue', 'growth', 'profit', 'margin', 'guidance', 'quarter',
                 'operating', 'net income', 'ai', 'artificial intelligence',
                 'machine learning', 'amazon'],
        'medium': ['logistics', 'warehouse', 'drone', 'grocery', 'whole foods',
                   'streaming', 'video', 'music', 'ring', 'echo'],
    },
    'KXEARNINGSMENTIONMETA': {
        'high': ['facebook', 'instagram', 'whatsapp', 'meta', 'metaverse',
                 'reality labs', 'reels', 'engagement', 'advertising', 'ad revenue',
                 'daily active', 'monthly active', 'ai', 'llama', 'revenue',
                 'growth', 'users', 'family of apps'],
        'medium': ['threads', 'quest', 'vr', 'ar', 'ray-ban', 'creator',
                   'horizon', 'virtual reality'],
    },
    'KXEARNINGSMENTIONTSLA': {
        'high': ['tesla', 'ev', 'electric vehicle', 'model', 'delivery',
                 'production', 'gigafactory', 'battery', 'autopilot', 'fsd',
                 'full self-driving', 'margin', 'revenue', 'energy', 'solar',
                 'supercharger', 'ai', 'dojo', 'optimus', 'robot'],
        'medium': ['cybertruck', 'semi', 'powerwall', 'megapack', 'robotaxi',
                   'lidar', 'supply chain'],
    },
    'KXEARNINGSMENTIONNVDA': {
        'high': ['nvidia', 'gpu', 'data center', 'ai', 'artificial intelligence',
                 'chip', 'revenue', 'growth', 'gaming', 'cuda', 'tensor',
                 'h100', 'a100', 'hopper', 'blackwell', 'inference',
                 'training', 'cloud', 'demand'],
        'medium': ['automotive', 'omniverse', 'grace', 'dgx', 'networking',
                   'arm', 'mellanox'],
    },
    'KXEARNINGSMENTIONCOINBASE': {
        'high': ['coinbase', 'crypto', 'bitcoin', 'ethereum', 'trading',
                 'revenue', 'transaction', 'subscription', 'staking',
                 'custody', 'institutional', 'retail', 'base', 'wallet',
                 'compliance', 'sec', 'regulation'],
        'medium': ['nft', 'defi', 'blockchain', 'usdc', 'web3', 'layer 2',
                   'prime', 'cloud'],
    },
    'KXEARNINGSMENTIONEA': {
        'high': ['ea', 'electronic arts', 'fifa', 'fc', 'madden', 'apex',
                 'revenue', 'net bookings', 'live services', 'player',
                 'engagement', 'mobile', 'console'],
        'medium': ['sims', 'battlefield', 'star wars', 'sports', 'ultimate team'],
    },
    'KXEARNINGSMENTIONRDDT': {
        'high': ['reddit', 'user', 'dau', 'advertising', 'revenue', 'community',
                 'subreddit', 'engagement', 'growth', 'ai', 'data licensing',
                 'api'],
        'medium': ['moderator', 'content', 'awards', 'premium'],
    },
    'KXEARNINGSMENTIONNBIS': {
        'high': ['nebius', 'ai', 'infrastructure', 'cloud', 'gpu', 'revenue',
                 'growth', 'compute', 'training', 'inference'],
        'medium': ['data center', 'yandex', 'europe', 'customer'],
    },
}

# Words very unlikely on ANY earnings call
EARNINGS_UNLIKELY_WORDS = {
    'trump', 'biden', 'maga', 'election', 'immigration', 'border',
    'fentanyl', 'epstein', 'ukraine', 'iran', 'hoax', 'rigged',
    'communist', 'socialist', 'antifa', 'thug', 'sleepy joe',
    'fake news', 'transgender', 'woke', 'dei', 'radical left',
    'paid agitator', 'insurrection', 'windmill', 'ufc',
}

# ============================================================================
# PRESS BRIEFING PROBABILITY MODEL
# ============================================================================

# Karoline Leavitt press briefing — policy-oriented words
PRESS_BRIEFING_HIGH_PROB = {
    'president': 0.99, 'administration': 0.95, 'policy': 0.90,
    'border': 0.85, 'immigration': 0.85, 'illegal': 0.80,
    'ice': 0.80, 'tariff': 0.70, 'trade': 0.70,
    'economy': 0.75, 'jobs': 0.65, 'security': 0.75,
    'national security': 0.65, 'executive order': 0.60,
    'congress': 0.70, 'senate': 0.55, 'house': 0.65,
    'foreign policy': 0.50, 'china': 0.65, 'russia': 0.50,
    'ukraine': 0.55, 'iran': 0.45, 'israel': 0.50,
    'military': 0.55, 'defense': 0.60, 'fbi': 0.50,
    'doj': 0.45, 'justice': 0.55, 'biden': 0.60,
    'statement': 0.85, 'question': 0.95, 'reporter': 0.60,
    'media': 0.70, 'press': 0.90, 'briefing': 0.85,
    'home': 0.55, 'housing': 0.45, 'stock': 0.20,
    'kristy': 0.40, 'noem': 0.40,
}

PRESS_BRIEFING_LOW_PROB = {
    'stupid question': 0.08, 'crypto': 0.10, 'bitcoin': 0.05,
    'epstein': 0.15, 'paid agitator': 0.08, 'radical': 0.18,
    'sleepy joe': 0.05, 'maga': 0.10, 'ufc': 0.02,
    'windmill': 0.03, 'marijuana': 0.05, 'thug': 0.05,
    'pocahontas': 0.02, 'newscum': 0.03,
}

# ============================================================================
# ENTERTAINMENT PROBABILITY MODEL
# ============================================================================

ENTERTAINMENT_MODELS = {
    'KXGREENDAYMENTION': {
        'high_prob': {'maga': 0.45, 'america': 0.80, 'rock': 0.70,
                      'punk': 0.50, 'song': 0.60, 'music': 0.70,
                      'super bowl': 0.60, 'halftime': 0.50},
        'low_prob': {'trump': 0.15, 'biden': 0.05, 'tariff': 0.01,
                     'immigration': 0.02, 'crypto': 0.01},
        'default': 0.15,
    },
    'KXMRBEASTMENTION': {
        'high_prob': {'subscribe': 0.90, 'challenge': 0.80, 'money': 0.85,
                      'win': 0.80, 'million': 0.75, 'video': 0.90,
                      'youtube': 0.70, 'beast': 0.60, 'like': 0.85},
        'low_prob': {'trump': 0.10, 'biden': 0.03, 'tariff': 0.01,
                     'immigration': 0.01, 'ukraine': 0.02},
        'default': 0.20,
    },
}

# ============================================================================
# SOTU-SPECIFIC PROBABILITY ADJUSTMENTS
# ============================================================================

# SOTU is a formal prepared speech — different word distribution
SOTU_SPECIFIC_PROBS = {
    # Near-certain in formal SOTU
    'china': 0.98, 'iran': 0.92, 'border': 0.98, 'immigration': 0.95,
    'economy': 0.98, 'jobs': 0.95, 'energy': 0.90, 'military': 0.90,
    'peace': 0.85, 'israel': 0.85, 'ukraine': 0.80, 'russia': 0.80,
    'nato': 0.70, 'tax': 0.85, 'fentanyl': 0.80, 'crime': 0.75,
    'police': 0.70, 'education': 0.65, 'korea': 0.65, 'japan': 0.70,
    'trillion': 0.90, 'billion': 0.95, 'million': 0.95,
    'america': 0.99, 'country': 0.99, 'people': 0.99,
    'affordable': 0.70, 'venezuela': 0.60, 'cuba': 0.55,
    'saudi arabia': 0.55, 'middle east': 0.85, 'afghanistan': 0.50,
    'mexico': 0.75, 'canada': 0.60, 'europe': 0.55,
    'radical': 0.65, 'transgender': 0.60, 'dei': 0.45, 'woke': 0.35,
    # Moderate in SOTU
    'crypto': 0.40, 'bitcoin': 0.35, 'inflation': 0.80,
    'stock market': 0.45, 'nuclear': 0.55, 'elon': 0.30, 'musk': 0.30,
    'drill': 0.55, 'oil': 0.65, 'gas': 0.60,
    'golden dome': 0.35, 'autopen': 0.20,
    # LOW in formal SOTU (Trump insults/slang less likely in prepared speech)
    'sleepy joe': 0.25, 'fake news': 0.30, 'hoax': 0.30,
    'rigged': 0.20, 'ufc': 0.08, 'windmill': 0.15,
    'maga': 0.50, 'tremendous': 0.75, 'beautiful': 0.70,
    'epstein': 0.05, 'marijuana': 0.08, 'weed': 0.04,
    'thug': 0.10, 'antifa': 0.12, 'hellhole': 0.10,
    'pocahontas': 0.05, 'newscum': 0.03, 'paid agitator': 0.05,
    'somali': 0.40, 'somalia': 0.40, 'vaccine': 0.35,
    'trump': 0.85, 'egg': 0.15, 'iq': 0.10,
    'cookie': 0.05, 'ballroom': 0.08,
    'hottest': 0.30, 'tds': 0.08,
    # Nickname-style: very unlikely in formal SOTU
    'slopadopolous': 0.03, 'tampon tim': 0.05, 'con job': 0.08,
    'piggy': 0.02, 'biden crime family': 0.10, 'crying chuck': 0.08,
}

# SOTU blocklist: words near-certain in SOTU — don't sell NO
SOTU_BLOCKLIST = {w for w, p in SOTU_SPECIFIC_PROBS.items() if p >= 0.80}

# ============================================================================
# LOGGING SETUP
# ============================================================================

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(str(LOG_FILE)),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("mention-trader")

# ============================================================================
# SIGNAL HANDLING (Iron Rule #9)
# ============================================================================

SHUTDOWN_REQUESTED = False


def handle_signal(signum, frame):
    global SHUTDOWN_REQUESTED
    sig_name = signal.Signals(signum).name
    log.info(f"Received {sig_name} — initiating graceful shutdown")
    SHUTDOWN_REQUESTED = True


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# ============================================================================
# STATE MANAGEMENT
# ============================================================================


def load_state() -> dict:
    """Load paper trading state from disk."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
            # Migrate: ensure new fields exist
            if "series_pnl" not in state:
                state["series_pnl"] = {}
            if state.get("bankroll", 0) < STARTING_BANKROLL and state.get("total_trades", 0) == 0:
                state["bankroll"] = STARTING_BANKROLL
            return state
        except Exception as e:
            log.warning(f"Failed to load state: {e}, starting fresh")
    return {
        "bankroll": STARTING_BANKROLL,
        "positions": {},
        "settled": [],
        "trade_log": [],
        "total_pnl": 0.0,
        "total_trades": 0,
        "total_wins": 0,
        "total_losses": 0,
        "scan_count": 0,
        "series_pnl": {},       # series_type → cumulative PnL
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_scan": None,
    }


def save_state(state: dict):
    """Persist state to disk atomically."""
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, default=str)
    tmp.rename(STATE_FILE)


# ============================================================================
# SERIES TYPE DETECTION
# ============================================================================


def detect_series_type(series_ticker: str, event_title: str = "") -> str:
    """Detect series type from series ticker and event title."""
    # Direct map first
    for prefix, stype in SERIES_TYPE_MAP.items():
        if series_ticker.startswith(prefix):
            return stype

    # Fallback: detect from event title
    title_lower = event_title.lower()
    if 'sotu' in title_lower or 'state of the union' in title_lower:
        return 'trump_sotu'
    if 'press briefing' in title_lower or 'press secretary' in title_lower:
        return 'press_briefing'
    if 'nfl' in title_lower or 'super bowl' in title_lower or 'football' in title_lower:
        return 'sports_nfl'
    if 'nba' in title_lower or 'basketball' in title_lower:
        return 'sports_nba'
    if 'earnings' in title_lower:
        return 'earnings'
    if 'trump' in title_lower and 'week' in title_lower:
        return 'trump_weekly'
    if 'trump' in title_lower and 'month' in title_lower:
        return 'trump_monthly'
    if 'trump' in title_lower and 'nickname' in title_lower:
        return 'trump_nickname'
    if 'trump' in title_lower:
        return 'trump_event'

    return 'unknown'


def get_series_from_ticker(ticker: str) -> str:
    """Extract the series ticker from a market ticker.
    E.g. 'KXTRUMPSAY-26FEB09-TRAN' → 'KXTRUMPSAY'
    """
    # Try all known series (longest match first)
    sorted_series = sorted(SERIES_TYPE_MAP.keys(), key=len, reverse=True)
    for series in sorted_series:
        if ticker.startswith(series):
            return series
    # Fallback: split on first dash
    parts = ticker.split('-')
    return parts[0] if parts else ticker


# ============================================================================
# API HELPERS
# ============================================================================

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "MentionTrader/2.0 (paper-trading-bot-multi-series)",
    "Accept": "application/json",
})


def api_get(url: str, params: dict = None, timeout: int = 15) -> Optional[dict]:
    """Safe API GET with error handling."""
    try:
        resp = SESSION.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        log.warning(f"API error for {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        log.warning(f"JSON decode error for {url}: {e}")
        return None


# ============================================================================
# MARKET SCANNING — KALSHI
# ============================================================================


def scan_kalshi_mention_markets() -> list:
    """Scan Kalshi for mention/say markets across all configured series."""
    markets = []
    series_counts = {}

    # Scan each configured series
    for series in KALSHI_MENTION_SERIES:
        data = api_get(
            f"{KALSHI_BASE}/events",
            params={
                "limit": 50,
                "status": "open",
                "series_ticker": series,
                "with_nested_markets": "true",
            },
        )
        if not data:
            continue

        series_market_count = 0
        for event in data.get("events", []):
            event_title = event.get("title", "")
            event_ticker = event.get("event_ticker", "")
            series_type = detect_series_type(series, event_title)

            for m in event.get("markets", []):
                status = m.get("status", "")
                if status != "active":
                    continue

                ticker = m.get("ticker", "")
                yes_bid = m.get("yes_bid", 0)
                yes_ask = m.get("yes_ask", 0)
                no_bid = m.get("no_bid", 0)
                no_ask = m.get("no_ask", 0)
                volume = m.get("volume", 0)
                subtitle = m.get("yes_sub_title", "") or m.get("subtitle", "")
                close_time = m.get("close_time", "")

                if yes_bid == 0 and yes_ask == 0:
                    continue

                if yes_bid > 0 and yes_ask > 0 and yes_ask < 100:
                    yes_mid = (yes_bid + yes_ask) / 2
                elif yes_ask > 0 and yes_ask < 100:
                    yes_mid = yes_ask
                else:
                    continue

                no_mid = 100 - yes_mid
                no_buy_price = no_ask if no_ask > 0 else (100 - yes_bid)

                market_id = f"kalshi:{ticker}"
                markets.append({
                    "id": market_id,
                    "platform": "kalshi",
                    "ticker": ticker,
                    "event_title": event_title,
                    "event_ticker": event_ticker,
                    "series_ticker": series,
                    "series_type": series_type,
                    "subtitle": subtitle,
                    "keyword": subtitle.lower().strip(),
                    "yes_bid": yes_bid,
                    "yes_ask": yes_ask,
                    "yes_mid": yes_mid,
                    "no_bid": no_bid,
                    "no_ask": no_ask,
                    "no_mid": no_mid,
                    "no_buy_price": no_buy_price,
                    "volume": volume,
                    "close_time": close_time,
                    "description": f"{event_title}: {subtitle}",
                })
                series_market_count += 1

        series_counts[series] = series_market_count

        # Rate limit: be nice to the API
        time.sleep(0.3)

    # Also scan all open events for keyword matches (catch new series)
    data = api_get(
        f"{KALSHI_BASE}/events",
        params={"limit": 200, "status": "open"},
    )
    if data:
        seen_tickers = {m["event_ticker"] for m in markets}
        for event in data.get("events", []):
            et = event.get("event_ticker", "")
            if et in seen_tickers:
                continue
            title_lower = (event.get("title", "") + " " + et).lower()
            if any(kw in title_lower for kw in KALSHI_KEYWORDS):
                detail = api_get(
                    f"{KALSHI_BASE}/events/{et}",
                    params={"with_nested_markets": "true"},
                )
                if not detail or "event" not in detail:
                    continue
                ev = detail["event"]
                event_title = ev.get("title", "")
                series_type = detect_series_type(et, event_title)

                for m in ev.get("markets", []):
                    if m.get("status") != "active":
                        continue
                    ticker = m.get("ticker", "")
                    yes_bid = m.get("yes_bid", 0)
                    yes_ask = m.get("yes_ask", 0)
                    no_bid = m.get("no_bid", 0)
                    no_ask = m.get("no_ask", 0)
                    subtitle = m.get("yes_sub_title", "") or m.get("subtitle", "")

                    if yes_bid == 0 and yes_ask == 0:
                        continue
                    if yes_ask == 0 or yes_ask >= 100:
                        continue

                    yes_mid = (yes_bid + yes_ask) / 2 if yes_bid > 0 else yes_ask
                    no_buy_price = no_ask if no_ask > 0 else (100 - yes_bid)

                    market_id = f"kalshi:{ticker}"
                    if market_id not in {mm["id"] for mm in markets}:
                        series_ticker_guess = get_series_from_ticker(ticker)
                        markets.append({
                            "id": market_id,
                            "platform": "kalshi",
                            "ticker": ticker,
                            "event_title": event_title,
                            "event_ticker": et,
                            "series_ticker": series_ticker_guess,
                            "series_type": series_type,
                            "subtitle": subtitle,
                            "keyword": subtitle.lower().strip(),
                            "yes_bid": yes_bid,
                            "yes_ask": yes_ask,
                            "yes_mid": yes_mid,
                            "no_bid": no_bid,
                            "no_ask": no_ask,
                            "no_mid": 100 - yes_mid,
                            "no_buy_price": no_buy_price,
                            "volume": m.get("volume", 0),
                            "close_time": m.get("close_time", ""),
                            "description": f"{event_title}: {subtitle}",
                        })

                time.sleep(0.2)

    # Log series breakdown
    for series, count in sorted(series_counts.items()):
        if count > 0:
            log.info(f"   {series}: {count} markets")

    log.info(f"Kalshi scan: found {len(markets)} active mention markets across {len(series_counts)} series")
    return markets


# ============================================================================
# MARKET SCANNING — POLYMARKET
# ============================================================================


def scan_polymarket_mention_markets() -> list:
    """Scan Polymarket for mention-type events."""
    markets = []

    data = api_get(
        f"{POLYMARKET_BASE}/events",
        params={
            "limit": 100,
            "active": "true",
            "closed": "false",
            "order": "volume",
            "ascending": "false",
        },
    )
    if not data:
        return markets

    mention_event_ids = []
    for event in data:
        title = (event.get("title", "") + " " + event.get("description", "")).lower()
        if any(term in title for term in [
            "trump say", "what will trump", "mention", "will be said",
            "say during", "what will be", "earnings call", "press briefing",
            "state of the union", "sotu", "what words",
        ]):
            mention_event_ids.append(event.get("id"))

    for event_id in mention_event_ids:
        event_data = api_get(f"{POLYMARKET_BASE}/events/{event_id}")
        if not event_data:
            continue

        event_title = event_data.get("title", "")
        end_date = event_data.get("endDate", "")

        # Detect series type for Polymarket events
        series_type = detect_series_type("", event_title)
        if series_type == 'unknown':
            series_type = 'trump_weekly'  # Polymarket mention events are mostly weekly Trump

        for m in event_data.get("markets", []):
            if m.get("closed", False):
                continue

            question = m.get("question", "")
            mid = m.get("id", "")

            prices_raw = m.get("outcomePrices", "[]")
            if isinstance(prices_raw, str):
                try:
                    prices = json.loads(prices_raw)
                except:
                    continue
            else:
                prices = prices_raw

            if not prices or len(prices) < 2:
                continue

            yes_price = float(prices[0]) * 100
            no_price = float(prices[1]) * 100

            if yes_price <= 0 or yes_price >= 100:
                continue

            keyword = ""
            if '"' in question:
                parts = question.split('"')
                if len(parts) >= 2:
                    keyword = parts[1].lower().strip()
            elif "'" in question:
                parts = question.split("'")
                if len(parts) >= 2:
                    keyword = parts[1].lower().strip()

            volume = m.get("volume", 0)
            if isinstance(volume, str):
                try:
                    volume = float(volume)
                except:
                    volume = 0

            market_id = f"polymarket:{mid}"
            markets.append({
                "id": market_id,
                "platform": "polymarket",
                "ticker": mid,
                "event_title": event_title,
                "event_ticker": m.get("slug", ""),
                "series_ticker": "polymarket",
                "series_type": series_type,
                "subtitle": question,
                "keyword": keyword or question.lower()[:50],
                "yes_bid": yes_price,
                "yes_ask": yes_price,
                "yes_mid": yes_price,
                "no_bid": no_price,
                "no_ask": no_price,
                "no_mid": no_price,
                "no_buy_price": no_price,
                "volume": volume,
                "close_time": end_date,
                "description": f"{event_title}: {question}",
            })

    log.info(f"Polymarket scan: found {len(markets)} active mention markets")
    return markets


# ============================================================================
# FAIR VALUE MODEL — MULTI-SERIES
# ============================================================================


def estimate_yes_probability(market: dict) -> float:
    """
    Estimate the true probability that YES resolves.
    Returns probability in 0-100 scale (cents).

    V2: Uses three-layer probability system:
    1. Static tiered word model
    2. LLM dynamic estimation
    3. Calibration adjustment
    
    Falls back to legacy series-specific models if V2 unavailable.
    """
    keyword = market.get("keyword", "").lower().strip()
    series_type = market.get("series_type", "unknown")
    
    # =========================================================================
    # V2 THREE-LAYER SYSTEM (preferred)
    # =========================================================================
    if HAS_V2_PROB:
        # Determine speaker from series type
        if "trump" in series_type:
            speaker = "trump"
        elif "press" in series_type:
            speaker = "press_secretary"
        elif "biden" in series_type:
            speaker = "biden"
        else:
            speaker = "unknown"
        
        # Determine event type
        if "sotu" in series_type:
            event_type = "sotu"
        elif "weekly" in series_type:
            event_type = "weekly"
        elif "rally" in series_type or "event" in series_type:
            event_type = "rally"
        else:
            event_type = "speech"
        
        # Get market price for blending
        yes_bid = market.get("yes_bid", 50)
        yes_ask = market.get("yes_ask", 50)
        market_yes = (yes_bid + yes_ask) / 2
        
        prob, metadata = estimate_mention_probability(
            word=keyword,
            speaker=speaker,
            event_type=event_type,
            market_price=market_yes,
            series_type=series_type
        )
        
        if prob is not None:
            # Store metadata for later analysis
            market["_v2_metadata"] = metadata
            return prob
        else:
            # V2 couldn't estimate - skip this market
            log.info(f"V2 system skipped {keyword} (no confident estimate)")
            return None
    
    # =========================================================================
    # LEGACY FALLBACK (if V2 not available)
    # =========================================================================
    if series_type == 'trump_sotu':
        return _estimate_sotu(market, keyword)
    elif series_type in ('trump_weekly', 'trump_monthly', 'trump_event', 'trump_nickname'):
        return _estimate_trump_speech(market, keyword, series_type)
    elif series_type == 'press_briefing':
        return _estimate_press_briefing(market, keyword)
    elif series_type in ('sports_nfl', 'sports_nba'):
        return _estimate_sports(market, keyword, series_type)
    elif series_type == 'earnings':
        return _estimate_earnings(market, keyword)
    elif series_type == 'entertainment':
        return _estimate_entertainment(market, keyword)
    else:
        # Try dynamic LLM-based estimation for unknown series
        series_ticker = market.get("series_ticker", "unknown")
        volume = market.get("volume", 0)
        
        if HAS_DYNAMIC_PROB:
            log.info(f"🤖 Using legacy LLM for {series_ticker} ({keyword})")
            dynamic_prob = get_dynamic_probability(market)
            if dynamic_prob is not None:
                log.info(f"🤖 LLM estimated {keyword}: {dynamic_prob:.0f}%")
                return dynamic_prob
            else:
                log.info(f"🤖 LLM uncertain about {keyword}, skipping")
        
        # No model = don't trade
        if volume > 50000:
            log.warning(f"⚠️ HIGH VOLUME NO MODEL: {series_ticker} ({volume:,} vol)")
        return None


def _estimate_trump_speech(market: dict, keyword: str, series_type: str) -> float:
    """Estimate probability for Trump weekly/monthly/event/nickname markets."""
    event_title = market.get("event_title", "").lower()

    # Determine event context
    is_prayer = "prayer" in event_title
    is_rally = "rally" in event_title or "campaign" in event_title
    is_monthly = series_type == 'trump_monthly'
    is_nickname = series_type == 'trump_nickname'

    if is_prayer:
        event_key = "prayer_breakfast"
    elif is_rally:
        event_key = "rally"
    else:
        event_key = "weekly_default"

    event_config = EVENT_ADJUSTMENTS.get(event_key, {})
    boost_words = event_config.get("boost_words", {})
    suppress_words = event_config.get("suppress_words", {})
    default_multiplier = event_config.get("default_multiplier", 1.0)

    # Step 1: Event-specific boost/suppress
    base_rate = None
    for kw_variant in [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]:
        if kw_variant in boost_words:
            base_rate = boost_words[kw_variant]
            break
        if kw_variant in suppress_words:
            base_rate = suppress_words[kw_variant]
            break

    # Step 2: Fall back to weekly base rates
    if base_rate is None:
        for kw_variant in [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]:
            if kw_variant in TRUMP_WEEKLY_BASE_RATES:
                raw_rate = TRUMP_WEEKLY_BASE_RATES[kw_variant]
                base_rate = min(0.95, raw_rate * default_multiplier)
                break

    # Step 3: Default for unknown words
    if base_rate is None:
        if is_prayer:
            base_rate = 0.12
        elif is_nickname:
            base_rate = 0.20  # Nicknames are somewhat likely but not guaranteed
        elif series_type == 'trump_event':
            base_rate = 0.25  # Events are focused topics
        else:
            base_rate = 0.20

    # Step 4: Monthly boost
    if is_monthly:
        base_rate = min(0.95, base_rate * MONTHLY_MULTIPLIER)

    # Step 5: Nickname series gets extra time (through April)
    if is_nickname:
        # ~2 months of time → similar to monthly boost
        base_rate = min(0.95, base_rate * 1.3)

    # Step 6: Bayesian blend with market when strongly disagrees
    yes_price = market.get("yes_mid", 50)
    if yes_price > 75 and base_rate < 0.40:
        base_rate = base_rate * 0.50 + (yes_price / 100) * 0.50
    elif yes_price > 60 and base_rate < 0.30:
        base_rate = base_rate * 0.70 + (yes_price / 100) * 0.30

    return base_rate * 100


def _estimate_sotu(market: dict, keyword: str) -> float:
    """Estimate probability for SOTU mention markets."""
    # Check SOTU-specific probability table first
    for kw_variant in [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]:
        if kw_variant in SOTU_SPECIFIC_PROBS:
            base_rate = SOTU_SPECIFIC_PROBS[kw_variant]
            return base_rate * 100

    # Check if it's in the general Trump base rates with SOTU multiplier
    sotu_config = EVENT_ADJUSTMENTS.get("sotu", {})
    boost_words = sotu_config.get("boost_words", {})
    suppress_words = sotu_config.get("suppress_words", {})
    default_multiplier = sotu_config.get("default_multiplier", 1.3)

    for kw_variant in [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]:
        if kw_variant in boost_words:
            return boost_words[kw_variant] * 100
        if kw_variant in suppress_words:
            return suppress_words[kw_variant] * 100

    # Fall back to base rates with SOTU multiplier
    for kw_variant in [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]:
        if kw_variant in TRUMP_WEEKLY_BASE_RATES:
            raw_rate = TRUMP_WEEKLY_BASE_RATES[kw_variant]
            base_rate = min(0.95, raw_rate * default_multiplier)
            return base_rate * 100

    # Determine sub-category from event
    event_title = market.get("event_title", "").lower()
    is_people = "who will" in event_title or "people" in event_title
    is_places = "place" in event_title

    if is_people:
        default = 0.35
    elif is_places:
        default = 0.30
    else:
        default = 0.35

    # Bayesian blend
    yes_price = market.get("yes_mid", 50)
    if yes_price > 75 and default < 0.40:
        default = default * 0.50 + (yes_price / 100) * 0.50
    elif yes_price > 60 and default < 0.30:
        default = default * 0.70 + (yes_price / 100) * 0.30

    return default * 100


def _estimate_press_briefing(market: dict, keyword: str) -> float:
    """Estimate probability for press briefing mention markets."""
    # Check specific prob tables
    for kw_variant in [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]:
        if kw_variant in PRESS_BRIEFING_HIGH_PROB:
            return PRESS_BRIEFING_HIGH_PROB[kw_variant] * 100
        if kw_variant in PRESS_BRIEFING_LOW_PROB:
            return PRESS_BRIEFING_LOW_PROB[kw_variant] * 100

    # Fall back to Trump base rates with press conference multiplier
    pc_config = EVENT_ADJUSTMENTS.get("press_conference", {})
    default_multiplier = pc_config.get("default_multiplier", 1.0)

    for kw_variant in [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]:
        if kw_variant in TRUMP_WEEKLY_BASE_RATES:
            raw_rate = TRUMP_WEEKLY_BASE_RATES[kw_variant]
            # Press briefings are less Trump-specific → discount
            base_rate = min(0.90, raw_rate * 0.7)
            return base_rate * 100

    # Default: conservative for press briefing
    return 22.0


def _estimate_sports(market: dict, keyword: str, series_type: str) -> float:
    """Estimate probability for sports announcer mention markets."""
    # Check sports-specific word lists
    for kw_variant in [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]:
        if kw_variant in SPORTS_HIGH_PROB_WORDS:
            return SPORTS_HIGH_PROB_WORDS[kw_variant] * 100
        if kw_variant in SPORTS_LOW_PROB_WORDS:
            return SPORTS_LOW_PROB_WORDS[kw_variant] * 100

    # For NBA, slightly lower baseline than NFL (shorter broadcasts, less commentary)
    if series_type == 'sports_nba':
        default = 0.20
    else:
        default = 0.25

    # Bayesian blend for sports
    yes_price = market.get("yes_mid", 50)
    if yes_price > 70 and default < 0.35:
        default = default * 0.50 + (yes_price / 100) * 0.50

    return default * 100


def _estimate_earnings(market: dict, keyword: str) -> float:
    """Estimate probability for earnings call mention markets."""
    series_ticker = market.get("series_ticker", "")

    # Check company-specific word lists
    company_words = EARNINGS_COMPANY_WORDS.get(series_ticker, {})
    high_words = [w.lower() for w in company_words.get('high', [])]
    medium_words = [w.lower() for w in company_words.get('medium', [])]

    for kw_variant in [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]:
        if kw_variant in high_words:
            return 92.0  # Near-certain company will mention its own products
        if kw_variant in medium_words:
            return 65.0  # Likely but not certain

    # Check if it's an unlikely (political/cultural) word
    for kw_variant in [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]:
        if kw_variant in EARNINGS_UNLIKELY_WORDS:
            return 5.0  # Very unlikely on earnings call

    # Default for unknown words on earnings calls
    return EARNINGS_DEFAULT_BASE_RATE * 100


def _estimate_entertainment(market: dict, keyword: str) -> float:
    """Estimate probability for entertainment mention markets."""
    series_ticker = market.get("series_ticker", "")

    model = ENTERTAINMENT_MODELS.get(series_ticker, {})
    
    # ⚠️ NO MODEL = NO TRADE
    if not model:
        volume = market.get("volume", 0)
        if volume > 50000:
            log.warning(f"⚠️ HIGH VOLUME NO MODEL: entertainment/{series_ticker} ({volume:,} vol)")
        return None  # None = don't trade (not gambling)
    
    high_prob = model.get('high_prob', {})
    low_prob = model.get('low_prob', {})
    default = model.get('default', 0.50)  # More conservative default

    for kw_variant in [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]:
        if kw_variant in high_prob:
            return high_prob[kw_variant] * 100
        if kw_variant in low_prob:
            return low_prob[kw_variant] * 100

    return default * 100


# ============================================================================
# BLOCKLIST — SERIES-AWARE
# ============================================================================


def is_blocklisted(keyword: str, series_type: str) -> bool:
    """Check if a keyword should be blocklisted for NO trades on this series type."""
    kw_variants = [keyword, keyword.split("/")[0].strip(), keyword.split(" or ")[0].strip()]

    if series_type in ('trump_weekly', 'trump_monthly', 'trump_event', 'trump_nickname'):
        # Use the 37-word Trump high-frequency blocklist
        for kw in kw_variants:
            if kw in HIGH_FREQ_BLOCKLIST:
                return True

    elif series_type == 'trump_sotu':
        # SOTU blocklist: near-certain words in formal speech
        for kw in kw_variants:
            if kw in SOTU_BLOCKLIST:
                return True

    elif series_type in ('sports_nfl', 'sports_nba'):
        # Don't sell NO on common sports words
        for kw in kw_variants:
            if kw in SPORTS_HIGH_PROB_WORDS and SPORTS_HIGH_PROB_WORDS[kw] >= 0.80:
                return True

    elif series_type == 'press_briefing':
        # Don't sell NO on common press briefing words
        for kw in kw_variants:
            if kw in PRESS_BRIEFING_HIGH_PROB and PRESS_BRIEFING_HIGH_PROB[kw] >= 0.80:
                return True

    elif series_type == 'earnings':
        # Don't sell NO on company-specific words (they're near-certain YES)
        pass  # Handled by probability model — high prob words won't have edge

    return False


# ============================================================================
# TRADING LOGIC
# ============================================================================


def calculate_exposure(state: dict) -> float:
    """Calculate total current paper exposure."""
    total = 0.0
    for pos in state.get("positions", {}).values():
        total += pos.get("cost", 0.0)
    return total


def calculate_series_exposure(state: dict, series_type: str) -> float:
    """Calculate exposure for a specific series type."""
    total = 0.0
    for pos in state.get("positions", {}).values():
        if pos.get("series_type", "unknown") == series_type:
            total += pos.get("cost", 0.0)
    return total


def should_trade(market: dict, state: dict) -> Optional[dict]:
    """
    Determine if we should paper-trade on this market.
    Returns trade details dict or None.

    Supports two strategies:
    1. NO Grinder: Buy NO when YES overpriced (core strategy)
    2. Sure-Thing YES: Buy YES when our estimate > 95% but market < 85¢
    """
    market_id = market["id"]
    keyword = market.get("keyword", "").lower().strip()
    series_type = market.get("series_type", "unknown")

    # Skip if already have a position
    if market_id in state.get("positions", {}):
        return None

    # Get fair value estimate
    fair_yes = estimate_yes_probability(market)
    
    # ⚠️ NO MODEL = NO TRADE (not gambling)
    if fair_yes is None:
        return None
    
    fair_no = 100 - fair_yes
    yes_mid = market["yes_mid"]

    # Get series-specific limits
    limits = SERIES_LIMITS.get(series_type, SERIES_LIMITS['unknown'])
    max_per_market = limits['max_per_market']
    max_series_exp = limits['max_series_exposure']

    # Check series exposure limit
    series_exp = calculate_series_exposure(state, series_type)
    if series_exp >= max_series_exp:
        return None

    # Check total exposure limit
    current_exposure = calculate_exposure(state)
    remaining_total = MAX_TOTAL_EXPOSURE - current_exposure
    if remaining_total <= 0:
        return None

    remaining_series = max_series_exp - series_exp

    # ==========================================
    # Strategy 1: Sure-Thing YES
    # ==========================================
    if fair_yes >= SURE_THING_YES_MIN_FAIR * 100 and yes_mid < SURE_THING_YES_MAX_PRICE:
        edge_yes = fair_yes - yes_mid
        if edge_yes >= SURE_THING_YES_MIN_EDGE:
            return _build_yes_trade(
                market, state, fair_yes, edge_yes,
                max_per_market, remaining_total, remaining_series,
                series_type
            )

    # ==========================================
    # Strategy 2: NO Grinder (core)
    # ==========================================

    # Blocklist check
    if is_blocklisted(keyword, series_type):
        log.debug(f"  ⛔ BLOCKLIST [{series_type}]: '{keyword}' — skipping NO trade")
        return None

    no_buy = market["no_buy_price"]
    edge = yes_mid - fair_yes  # positive = YES overpriced → buy NO

    # Minimum edge checks
    edge_fraction = edge / 100.0
    if edge_fraction < MIN_EDGE_FRACTION:
        return None
    if edge < MIN_EDGE_CENTS:
        return None

    # Hard cap: never buy NO above 60¢
    if no_buy > MAX_NO_PRICE:
        return None
    if no_buy < MIN_NO_PRICE:
        return None

    # Kelly criterion
    p_no_wins = fair_no / 100.0
    profit_per_contract = (100 - no_buy) / 100.0
    risk_per_contract = no_buy / 100.0
    b = profit_per_contract / risk_per_contract if risk_per_contract > 0 else 0

    ev_per_contract = p_no_wins * profit_per_contract - (1 - p_no_wins) * risk_per_contract
    if ev_per_contract <= 0:
        return None

    q = 1 - p_no_wins
    kelly_fraction = (b * p_no_wins - q) / b if b > 0 else 0
    half_kelly = max(0, kelly_fraction / 2)

    # Position sizing
    budget = min(max_per_market, remaining_total, remaining_series)
    kelly_budget = budget * min(half_kelly * 4, 1.0)
    kelly_budget = max(5.0, min(kelly_budget, budget))

    if edge >= 25:
        size_factor = 1.0
    elif edge >= 15:
        size_factor = 0.7
    else:
        size_factor = 0.4

    final_budget = kelly_budget * size_factor
    final_budget = max(5.0, final_budget)

    num_contracts = int(final_budget / (no_buy / 100))
    if num_contracts <= 0:
        return None

    cost = num_contracts * (no_buy / 100)
    potential_profit = num_contracts * ((100 - no_buy) / 100)

    return {
        "market_id": market_id,
        "side": "NO",
        "strategy": "no_grinder",
        "num_contracts": num_contracts,
        "price_cents": no_buy,
        "cost": round(cost, 2),
        "potential_profit": round(potential_profit, 2),
        "edge_cents": round(edge, 1),
        "fair_yes": round(fair_yes, 1),
        "market_yes": round(yes_mid, 1),
        "ev_per_contract": round(ev_per_contract, 4),
        "kelly_fraction": round(kelly_fraction, 4),
        "p_no_wins": round(p_no_wins, 3),
        "description": market["description"],
        "keyword": market["keyword"],
        "platform": market["platform"],
        "series_ticker": market.get("series_ticker", ""),
        "series_type": series_type,
        "close_time": market["close_time"],
    }


def _build_yes_trade(market: dict, state: dict, fair_yes: float, edge: float,
                     max_per_market: float, remaining_total: float,
                     remaining_series: float, series_type: str) -> Optional[dict]:
    """Build a Sure-Thing YES trade."""
    yes_buy = market["yes_ask"]  # Buy YES at ask
    if yes_buy <= 0 or yes_buy >= 100:
        return None

    # Kelly for YES trade
    p_yes_wins = fair_yes / 100.0
    profit_per_contract = (100 - yes_buy) / 100.0
    risk_per_contract = yes_buy / 100.0
    b = profit_per_contract / risk_per_contract if risk_per_contract > 0 else 0

    ev_per_contract = p_yes_wins * profit_per_contract - (1 - p_yes_wins) * risk_per_contract
    if ev_per_contract <= 0:
        return None

    q = 1 - p_yes_wins
    kelly_fraction = (b * p_yes_wins - q) / b if b > 0 else 0
    half_kelly = max(0, kelly_fraction / 2)

    budget = min(max_per_market, remaining_total, remaining_series)
    kelly_budget = budget * min(half_kelly * 4, 1.0)
    kelly_budget = max(5.0, min(kelly_budget, budget))

    # Sure-thing YES: conservative sizing (smaller positions)
    final_budget = kelly_budget * 0.5
    final_budget = max(5.0, final_budget)

    num_contracts = int(final_budget / (yes_buy / 100))
    if num_contracts <= 0:
        return None

    cost = num_contracts * (yes_buy / 100)
    potential_profit = num_contracts * ((100 - yes_buy) / 100)

    return {
        "market_id": market["id"],
        "side": "YES",
        "strategy": "sure_thing_yes",
        "num_contracts": num_contracts,
        "price_cents": yes_buy,
        "cost": round(cost, 2),
        "potential_profit": round(potential_profit, 2),
        "edge_cents": round(edge, 1),
        "fair_yes": round(fair_yes, 1),
        "market_yes": round(market["yes_mid"], 1),
        "ev_per_contract": round(ev_per_contract, 4),
        "kelly_fraction": round(kelly_fraction, 4),
        "p_no_wins": round(1 - p_yes_wins, 3),
        "description": market["description"],
        "keyword": market["keyword"],
        "platform": market["platform"],
        "series_ticker": market.get("series_ticker", ""),
        "series_type": series_type,
        "close_time": market["close_time"],
    }


def execute_paper_trade(trade: dict, state: dict) -> bool:
    """Execute a paper trade by updating state."""
    market_id = trade["market_id"]
    cost = trade["cost"]

    if cost > state["bankroll"]:
        log.warning(f"Insufficient bankroll for {market_id}: need ${cost:.2f}, have ${state['bankroll']:.2f}")
        return False

    state["bankroll"] -= cost

    state["positions"][market_id] = {
        "side": trade["side"],
        "strategy": trade.get("strategy", "no_grinder"),
        "num_contracts": trade["num_contracts"],
        "entry_price_cents": trade["price_cents"],
        "cost": cost,
        "potential_profit": trade["potential_profit"],
        "edge_cents": trade["edge_cents"],
        "fair_yes": trade["fair_yes"],
        "market_yes_at_entry": trade["market_yes"],
        "description": trade["description"],
        "keyword": trade["keyword"],
        "platform": trade["platform"],
        "series_ticker": trade.get("series_ticker", ""),
        "series_type": trade.get("series_type", "unknown"),
        "close_time": trade["close_time"],
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }

    trade_record = {
        "action": "OPEN",
        "market_id": market_id,
        "side": trade["side"],
        "strategy": trade.get("strategy", "no_grinder"),
        "contracts": trade["num_contracts"],
        "price": trade["price_cents"],
        "cost": cost,
        "edge": trade["edge_cents"],
        "fair_yes": trade["fair_yes"],
        "market_yes": trade["market_yes"],
        "series_type": trade.get("series_type", "unknown"),
        "series_ticker": trade.get("series_ticker", ""),
        "description": trade["description"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    state["trade_log"].append(trade_record)
    state["total_trades"] += 1

    strategy_label = "🎯 SURE-THING YES" if trade["side"] == "YES" else "📈 NO GRIND"
    reasoning = (
        f"[{trade.get('series_type', '?')}] "
        f"{'YES underpriced' if trade['side'] == 'YES' else 'YES overpriced'}: "
        f"market={trade['market_yes']:.0f}¢ vs fair={trade['fair_yes']:.0f}¢ "
        f"(edge={trade['edge_cents']:.0f}¢, EV=${trade.get('ev_per_contract', 0):.3f}/contract, "
        f"Kelly={trade.get('kelly_fraction', 0):.3f}). "
        f"Bought {trade['num_contracts']} {trade['side']} @ {trade['price_cents']:.0f}¢ for ${cost:.2f}. "
        f"Potential profit: ${trade['potential_profit']:.2f}"
    )
    log.info(f"{strategy_label}: {trade['description']}")
    log.info(f"   {reasoning}")

    return True


# ============================================================================
# SETTLEMENT CHECKING
# ============================================================================


def check_kalshi_settlements(state: dict):
    """Check if any Kalshi positions have settled."""
    kalshi_positions = {
        mid: pos for mid, pos in state["positions"].items()
        if pos["platform"] == "kalshi"
    }
    if not kalshi_positions:
        return

    for market_id, pos in list(kalshi_positions.items()):
        ticker = market_id.replace("kalshi:", "")
        data = api_get(f"{KALSHI_BASE}/markets/{ticker}")
        if not data or "market" not in data:
            continue

        m = data["market"]
        status = m.get("status", "")
        result = m.get("result", "")

        if status in ("finalized", "settled") and result:
            settle_position(state, market_id, result)

        time.sleep(0.1)  # Rate limit


def check_polymarket_settlements(state: dict):
    """Check if any Polymarket positions have settled."""
    pm_positions = {
        mid: pos for mid, pos in state["positions"].items()
        if pos["platform"] == "polymarket"
    }
    if not pm_positions:
        return

    for market_id, pos in list(pm_positions.items()):
        mid = market_id.replace("polymarket:", "")
        data = api_get(f"{POLYMARKET_BASE}/markets/{mid}")
        if not data:
            continue

        if data.get("closed", False):
            prices_raw = data.get("outcomePrices", "[]")
            if isinstance(prices_raw, str):
                try:
                    prices = json.loads(prices_raw)
                except:
                    continue
            else:
                prices = prices_raw

            if prices:
                yes_price = float(prices[0])
                if yes_price >= 0.99:
                    settle_position(state, market_id, "yes")
                elif yes_price <= 0.01:
                    settle_position(state, market_id, "no")


def check_expired_positions(state: dict):
    """Check if any positions have passed their close time."""
    now = datetime.now(timezone.utc)
    for market_id, pos in list(state.get("positions", {}).items()):
        close_time_str = pos.get("close_time", "")
        if not close_time_str:
            continue
        try:
            close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
            if now > close_time + timedelta(hours=2):
                log.info(f"⏰ Position {market_id} past close time, checking settlement...")
                if pos["platform"] == "kalshi":
                    ticker = market_id.replace("kalshi:", "")
                    data = api_get(f"{KALSHI_BASE}/markets/{ticker}")
                    if data and "market" in data:
                        m = data["market"]
                        result = m.get("result", "")
                        if result:
                            settle_position(state, market_id, result)
        except (ValueError, TypeError):
            pass


def settle_position(state: dict, market_id: str, result: str):
    """Settle a position based on resolution result."""
    if market_id not in state["positions"]:
        return

    pos = state["positions"][market_id]
    cost = pos["cost"]
    contracts = pos["num_contracts"]
    side = pos.get("side", "NO")
    series_type = pos.get("series_type", "unknown")

    # Determine if we won
    if side == "NO":
        if result.lower() == "no":
            payout = contracts * 1.0
            pnl = payout - cost
            state["total_wins"] += 1
            emoji = "✅"
        else:
            payout = 0.0
            pnl = -cost
            state["total_losses"] += 1
            emoji = "❌"
    else:  # YES
        if result.lower() == "yes":
            payout = contracts * 1.0
            pnl = payout - cost
            state["total_wins"] += 1
            emoji = "✅"
        else:
            payout = 0.0
            pnl = -cost
            state["total_losses"] += 1
            emoji = "❌"

    state["bankroll"] += payout
    state["total_pnl"] += pnl

    # Update series-level P&L
    if "series_pnl" not in state:
        state["series_pnl"] = {}
    state["series_pnl"][series_type] = state["series_pnl"].get(series_type, 0.0) + pnl

    settlement = {
        "market_id": market_id,
        "description": pos["description"],
        "keyword": pos["keyword"],
        "result": result,
        "side": side,
        "strategy": pos.get("strategy", "no_grinder"),
        "series_type": series_type,
        "series_ticker": pos.get("series_ticker", ""),
        "contracts": contracts,
        "entry_price": pos["entry_price_cents"],
        "cost": cost,
        "payout": round(payout, 2),
        "pnl": round(pnl, 2),
        "edge_at_entry": pos["edge_cents"],
        "opened_at": pos["opened_at"],
        "settled_at": datetime.now(timezone.utc).isoformat(),
    }
    state["settled"].append(settlement)

    trade_record = {
        "action": "SETTLE",
        "market_id": market_id,
        "result": result,
        "side": side,
        "series_type": series_type,
        "pnl": round(pnl, 2),
        "payout": round(payout, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    state["trade_log"].append(trade_record)

    log.info(f"{emoji} SETTLED [{series_type}]: {pos['description']}")
    log.info(f"   Result={result.upper()} | Side={side} | PnL=${pnl:+.2f} | Payout=${payout:.2f} | Cost=${cost:.2f}")

    # Record for V2 calibration learning
    if HAS_V2_PROB:
        try:
            # Get our predicted probability from position metadata
            predicted = pos.get("fair_yes", 50)  # Our estimate at entry
            actual_yes = (result.lower() == "yes")
            
            # Get tier from V2 metadata if available
            v2_meta = pos.get("_v2_metadata", {})
            tier = v2_meta.get("layers", {}).get("static", {}).get("tier", 0)
            
            record_outcome(
                word=pos["keyword"],
                tier=tier,
                predicted=predicted,
                actual_yes=actual_yes,
                series_type=series_type,
                event_type=pos.get("event_type", "speech")
            )
            log.info(f"   📊 Calibration recorded: predicted={predicted:.0f}% actual={'YES' if actual_yes else 'NO'}")
        except Exception as e:
            log.warning(f"   ⚠️ Calibration recording failed: {e}")

    del state["positions"][market_id]


# ============================================================================
# STATUS REPORTING — ENHANCED
# ============================================================================


def print_status(state: dict):
    """Print comprehensive status report with series breakdown."""
    exposure = calculate_exposure(state)
    num_positions = len(state.get("positions", {}))
    num_settled = len(state.get("settled", []))

    log.info("=" * 80)
    log.info("📊 MENTION MARKET MULTI-SERIES TRADER — STATUS REPORT")
    log.info("=" * 80)
    log.info(f"  Bankroll:       ${state['bankroll']:.2f}")
    log.info(f"  Total P&L:      ${state['total_pnl']:+.2f}")
    log.info(f"  Exposure:       ${exposure:.2f} / ${MAX_TOTAL_EXPOSURE:.2f}")
    log.info(f"  Open Positions: {num_positions}")
    log.info(f"  Settled Trades: {num_settled}")
    log.info(f"  Win/Loss:       {state['total_wins']}W / {state['total_losses']}L")
    log.info(f"  Total Trades:   {state['total_trades']}")
    log.info(f"  Scans:          {state['scan_count']}")

    if state.get("total_wins", 0) + state.get("total_losses", 0) > 0:
        total = state["total_wins"] + state["total_losses"]
        win_rate = state["total_wins"] / total * 100
        log.info(f"  Win Rate:       {win_rate:.1f}%")

    # Series-level P&L breakdown
    series_pnl = state.get("series_pnl", {})
    if series_pnl:
        log.info(f"\n  📈 P&L by Series Type:")
        for stype, pnl in sorted(series_pnl.items(), key=lambda x: x[1], reverse=True):
            emoji = "🟢" if pnl >= 0 else "🔴"
            log.info(f"    {emoji} {stype:20s} ${pnl:+.2f}")

    # Series exposure breakdown
    if num_positions > 0:
        series_exposure = {}
        for mid, pos in state["positions"].items():
            stype = pos.get("series_type", "unknown")
            series_exposure[stype] = series_exposure.get(stype, 0.0) + pos.get("cost", 0.0)

        log.info(f"\n  💰 Exposure by Series Type:")
        for stype, exp in sorted(series_exposure.items(), key=lambda x: x[1], reverse=True):
            limits = SERIES_LIMITS.get(stype, SERIES_LIMITS['unknown'])
            log.info(f"    {stype:20s} ${exp:.2f} / ${limits['max_series_exposure']:.2f}")

    # Open positions with series info
    if num_positions > 0:
        log.info(f"\n  📋 Open Positions ({num_positions}):")
        for mid, pos in state["positions"].items():
            strategy_icon = "🎯" if pos.get("strategy") == "sure_thing_yes" else "📉"
            log.info(
                f"    {strategy_icon} {pos['keyword']:25s} | {pos.get('series_type', '?'):18s} | "
                f"{pos.get('side','NO')}@{pos['entry_price_cents']:.0f}¢ × {pos['num_contracts']} | "
                f"cost=${pos['cost']:.2f} | edge={pos['edge_cents']:.0f}¢ | "
                f"close={pos['close_time'][:10] if pos['close_time'] else '?'}"
            )

    # Recent settlements
    if state.get("settled"):
        recent = state["settled"][-8:]
        log.info(f"\n  📜 Recent Settlements (last {len(recent)}):")
        for s in recent:
            emoji = "✅" if s["pnl"] > 0 else "❌"
            log.info(
                f"    {emoji} {s['keyword']:25s} | {s.get('series_type', '?'):15s} | "
                f"{s.get('side', 'NO')} | {s['result']:3s} | PnL=${s['pnl']:+.2f}"
            )

    # Upcoming events countdown
    _print_upcoming_events(state)

    log.info("=" * 80)


def _print_upcoming_events(state: dict):
    """Show upcoming events with countdown."""
    now = datetime.now(timezone.utc)
    upcoming = []

    # Collect unique close times from positions
    seen_events = set()
    for mid, pos in state.get("positions", {}).items():
        close_time_str = pos.get("close_time", "")
        event_key = f"{pos.get('series_type', '')}:{close_time_str[:10]}"
        if event_key in seen_events or not close_time_str:
            continue
        seen_events.add(event_key)
        try:
            close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
            if close_time > now:
                delta = close_time - now
                upcoming.append((delta, pos.get("series_type", "?"), close_time_str[:16]))
        except (ValueError, TypeError):
            pass

    if upcoming:
        upcoming.sort()
        log.info(f"\n  ⏰ Upcoming Events:")
        for delta, stype, close_str in upcoming[:5]:
            days = delta.days
            hours = delta.seconds // 3600
            if days > 0:
                countdown = f"{days}d {hours}h"
            else:
                countdown = f"{hours}h {(delta.seconds % 3600) // 60}m"
            log.info(f"    📅 {stype:20s} closes {close_str} (in {countdown})")


# ============================================================================
# MAIN LOOP
# ============================================================================


class MentionTrader:
    """Main trader class for external access to configuration."""

    KALSHI_MENTION_SERIES = KALSHI_MENTION_SERIES
    SERIES_TYPE_MAP = SERIES_TYPE_MAP
    SERIES_LIMITS = SERIES_LIMITS

    def __init__(self):
        self.state = load_state()
        log.info(f"MentionTrader initialized with {len(self.KALSHI_MENTION_SERIES)} Kalshi series")
        log.info(f"Series types: {sorted(set(self.SERIES_TYPE_MAP.values()))}")

    def scan(self):
        """Run one scan cycle."""
        run_scan_cycle(self.state)

    def status(self):
        """Print status."""
        print_status(self.state)


def run_scan_cycle(state: dict):
    """Run one complete scan + trade cycle."""
    state["scan_count"] = state.get("scan_count", 0) + 1
    state["last_scan"] = datetime.now(timezone.utc).isoformat()

    log.info(f"🔍 Scan #{state['scan_count']} — scanning {len(KALSHI_MENTION_SERIES)} Kalshi series + Polymarket...")

    # 1. Scan both platforms
    kalshi_markets = scan_kalshi_mention_markets()
    polymarket_markets = scan_polymarket_mention_markets()
    all_markets = kalshi_markets + polymarket_markets

    # Count by series type
    type_counts = {}
    for m in all_markets:
        st = m.get("series_type", "unknown")
        type_counts[st] = type_counts.get(st, 0) + 1

    log.info(f"   Total markets: {len(all_markets)} (Kalshi={len(kalshi_markets)}, PM={len(polymarket_markets)})")
    for st, count in sorted(type_counts.items()):
        log.info(f"     {st}: {count} markets")

    # 2. Evaluate each market
    opportunities = []
    for market in all_markets:
        trade = should_trade(market, state)
        if trade:
            opportunities.append(trade)

    # 3. Sort by EV (highest first) and execute
    opportunities.sort(key=lambda x: x.get("ev_per_contract", 0), reverse=True)

    trades_executed = 0
    no_trades = 0
    yes_trades = 0
    for trade in opportunities:
        if SHUTDOWN_REQUESTED:
            break
        if execute_paper_trade(trade, state):
            trades_executed += 1
            if trade["side"] == "YES":
                yes_trades += 1
            else:
                no_trades += 1
            save_state(state)

    if trades_executed > 0:
        log.info(f"   Executed {trades_executed} trades ({no_trades} NO grind, {yes_trades} sure-thing YES)")
    else:
        if opportunities:
            log.info(f"   {len(opportunities)} opportunities found but couldn't execute (limits/bankroll)")
        else:
            log.info(f"   No new trading opportunities")

    # 4. Check settlements
    check_kalshi_settlements(state)
    check_polymarket_settlements(state)
    check_expired_positions(state)

    save_state(state)


def main():
    log.info("🚀 Mention Market Multi-Series Trader starting up...")
    log.info(f"   Series: {len(KALSHI_MENTION_SERIES)} Kalshi series + Polymarket")
    log.info(f"   Strategies: NO Grinder (edge≥{MIN_EDGE_CENTS}¢) + Sure-Thing YES (fair≥{SURE_THING_YES_MIN_FAIR*100:.0f}¢, market<{SURE_THING_YES_MAX_PRICE}¢)")
    log.info(f"   Limits: ${MAX_TOTAL_EXPOSURE} total, per-series limits active")
    log.info(f"   Series types: {sorted(set(SERIES_TYPE_MAP.values()))}")
    log.info(f"   Scan interval: {SCAN_INTERVAL}s ({SCAN_INTERVAL/60:.0f} min)")
    log.info(f"   State: {STATE_FILE}")
    log.info(f"   Log: {LOG_FILE}")

    state = load_state()
    log.info(f"   Bankroll: ${state['bankroll']:.2f} | Existing positions: {len(state.get('positions', {}))}")

    # Initial scan
    run_scan_cycle(state)
    print_status(state)

    last_scan = time.time()
    last_status = time.time()
    last_settlement_check = time.time()

    while not SHUTDOWN_REQUESTED:
        now = time.time()

        # Settlement check every 5 minutes
        if now - last_settlement_check >= SETTLEMENT_CHECK_INTERVAL:
            try:
                check_kalshi_settlements(state)
                check_polymarket_settlements(state)
                check_expired_positions(state)
                save_state(state)
            except Exception as e:
                log.error(f"Settlement check error: {e}")
                log.debug(traceback.format_exc())
            last_settlement_check = now

        # Full scan every 15 minutes
        if now - last_scan >= SCAN_INTERVAL:
            try:
                run_scan_cycle(state)
            except Exception as e:
                log.error(f"Scan cycle error: {e}")
                log.debug(traceback.format_exc())
            last_scan = now

        # Status report every hour
        if now - last_status >= STATUS_INTERVAL:
            print_status(state)
            last_status = now

        # Sleep in short intervals for signal responsiveness
        for _ in range(30):
            if SHUTDOWN_REQUESTED:
                break
            time.sleep(1)

    # Graceful shutdown
    log.info("🛑 Shutting down gracefully...")
    save_state(state)
    print_status(state)
    log.info("Goodbye!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error(f"Fatal error: {e}")
        log.error(traceback.format_exc())
        sys.exit(1)
