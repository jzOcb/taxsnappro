#!/usr/bin/env python3
"""
Cross-Platform Signal Trading Bot v3: Polymarket ↔ Kalshi
==========================================================
Uses market_matcher.py v3 engine for multi-category matching:
  - Weather (5 cities), NBA, Crypto, Trump Mentions, Soccer, Fed Rate, CPI, etc.

v3 Changes:
  - Replaced inline matching with modular MatcherEngine from market_matcher.py
  - 10+ category matchers (weather, NBA, crypto, mentions, soccer, economics...)
  - 28+ matched pairs across 5+ categories (was 3 categories / 107 dup pairs)
  - 38s scan time (was 128s)
  - Zero duplicate pairs

Data: /home/clawdbot/clawd/btc-arbitrage/data/cross_platform_prices.jsonl
State: /home/clawdbot/clawd/btc-arbitrage/crossplatform_trader_state.json
Log:   /home/clawdbot/clawd/btc-arbitrage/logs/crossplatform_trader_live.log
"""

import json
import sys
import os
import re
import time
import signal
import logging
import traceback
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import deque, defaultdict
from urllib import request as urllib_request
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError
from typing import Optional, Dict, List, Tuple, Any, Set
from dataclasses import dataclass, field, asdict

# ============================================================================
# PATHS
# ============================================================================
BASE_DIR = Path("/home/clawdbot/clawd/btc-arbitrage")
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
STATE_FILE = BASE_DIR / "crossplatform_trader_state.json"
PRICE_LOG = DATA_DIR / "cross_platform_prices.jsonl"
LOG_FILE = LOG_DIR / "crossplatform_trader_live.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# LOGGING
# ============================================================================
logger = logging.getLogger("xplat-v2")
logger.setLevel(logging.INFO)

fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

fh = logging.FileHandler(LOG_FILE)
fh.setFormatter(fmt)
logger.addHandler(fh)

sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(fmt)
logger.addHandler(sh)

# ============================================================================
# CONFIGURATION
# ============================================================================
POLL_INTERVAL = 30           # seconds between price poll cycles
RESCAN_INTERVAL = 600        # 10 minutes: re-scan for new market pairs (was 30min, Day 1)
PM_MOMENTUM_WINDOW = 300     # 5 minutes: check PM price movement
PM_MOVE_THRESHOLD = 0.03     # 3¢ move in PM triggers signal
SPREAD_ENTRY_MIN = 0.06      # minimum 6¢ spread to enter (covers 3.6% fees + margin)
SPREAD_EXIT_MAX = 0.02       # exit when spread narrows to 2¢
TRADE_MAX_SIZE = 100.0       # max $100 per paper trade (scaled from $50, Day 1)
TOTAL_MAX_EXPOSURE = 600.0   # max $600 total paper exposure (scaled from $300, Day 1)
TRADE_TIMEOUT = 3600         # 1 hour timeout for paper trades
SIGMA_THRESHOLD = 2.0        # 2σ above historical mean spread → signal
PRICE_HISTORY_MAX = 1000     # max price points per pair in memory
STATE_SAVE_INTERVAL = 60     # save state every 60 seconds
MATCH_SCORE_THRESHOLD = 80   # minimum score to accept a match

# API rate limiting
API_REQUEST_DELAY = 0.4      # seconds between API requests

# ============================================================================
# API ENDPOINTS
# ============================================================================
PM_GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
PM_GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
KALSHI_EVENTS = "https://api.elections.kalshi.com/trade-api/v2/events"
KALSHI_MARKETS = "https://api.elections.kalshi.com/trade-api/v2/markets"

# Kalshi series we're interested in
KALSHI_SERIES_OF_INTEREST = [
    "KXBTCD",       # Bitcoin daily price
    "KXETHD",       # Ethereum daily price
    "KXBTC",        # Bitcoin price range
    "KXETH",        # Ethereum price range
    "KXFED",        # Fed funds rate
    "KXFEDDECISION",# Fed decision (cut/hike/hold)
    "KXCPIYOY",     # CPI year-over-year
    "KXCPICORE",    # CPI core
    "KXCPI",        # CPI
    "KXGDP",        # GDP growth
    "KXPAYROLLS",   # Jobs/payrolls
    "KXU3",         # Unemployment
    "KXRECSSNBER",  # Recession
    "KXFEDCHAIRNOM",# Fed Chair nominee
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ParsedMarket:
    """A market parsed into structured fields for matching."""
    platform: str           # "polymarket" or "kalshi"
    market_id: str          # platform-specific identifier
    title: str              # original title
    event_title: str        # parent event title

    # Structured fields for matching
    category: str           # crypto, economics, politics
    asset_or_topic: str     # BTC, ETH, fed_rate, cpi, gdp, unemployment, recession
    direction: str          # above, below, between, increase, decrease, exact, nomination
    threshold: Optional[float]  # numeric value ($82000, 0.25, etc.)
    threshold_unit: str     # dollars, percent, bps, count
    settlement_date: Optional[datetime]  # when it resolves
    settlement_time_str: str    # human-readable time like "noon ET", "5pm EST"
    settlement_source: str  # Binance, BRTI, BLS, etc.
    person_or_entity: str   # for nomination markets: "Kevin Warsh", etc.

    # Price data
    yes_price: float = 0.0
    no_price: float = 0.0
    volume: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    extra: Dict = field(default_factory=dict)

    def match_key(self) -> str:
        """Key for grouping potentially matchable markets."""
        return f"{self.category}:{self.asset_or_topic}"


@dataclass
class MatchedPair:
    """A validated pair of PM + Kalshi markets for the same event."""
    pair_id: str
    pm_market: ParsedMarket
    kalshi_market: ParsedMarket
    match_score: int        # 0-100
    match_reasons: List[str]
    match_warnings: List[str]
    spread: float = 0.0
    pm_direction: float = 0.0
    signal_strength: float = 0.0
    last_update: float = 0.0


@dataclass
class PaperTrade:
    """A paper trade: entered based on PM signal, targeting Kalshi."""
    trade_id: str
    pair_id: str
    entry_time: float
    direction: str           # "YES" or "NO"
    entry_price: float       # Kalshi price at entry
    pm_price_at_entry: float
    spread_at_entry: float
    size_usd: float
    pm_title: str = ""
    kalshi_title: str = ""
    exit_time: Optional[float] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: float = 0.0
    status: str = "open"


# ============================================================================
# SIGNAL MANAGER: handles graceful shutdown (Iron Rule #9)
# ============================================================================

class SignalManager:
    """Handle SIGTERM/SIGINT for graceful shutdown."""

    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._handler)
        signal.signal(signal.SIGINT, self._handler)

    def _handler(self, signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info(f"⚠️ Received {sig_name} — initiating graceful shutdown...")
        self.shutdown_requested = True


# ============================================================================
# HTTP HELPERS
# ============================================================================

_last_request_time = 0.0

def http_get(url: str, params: Dict = None, timeout: int = 15) -> Optional[Any]:
    """HTTP GET with rate limiting. Returns parsed JSON or None."""
    global _last_request_time

    # Rate limiting
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < API_REQUEST_DELAY:
        time.sleep(API_REQUEST_DELAY - elapsed)
    _last_request_time = time.time()

    try:
        if params:
            query = urlencode({k: v for k, v in params.items() if v is not None})
            url = f"{url}?{query}"

        req = urllib_request.Request(url, headers={
            "User-Agent": "CrossPlatformTrader/2.0",
            "Accept": "application/json",
        })
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (URLError, HTTPError) as e:
        logger.debug(f"HTTP error for {url}: {e}")
        return None
    except Exception as e:
        logger.debug(f"Request error for {url}: {e}")
        return None


# ============================================================================
# MARKET PARSER: Extract structured fields from titles/descriptions
# ============================================================================

class MarketParser:
    """Parse market titles into structured fields for matching.

    Examples:
      PM:    "Will the price of Bitcoin be above $82,000 on February 5?"
             → category=crypto, asset=BTC, direction=above, threshold=82000,
               settlement_date=2026-02-05
      Kalshi: "Bitcoin price on Feb 5, 2026?" subtitle="$82,500 or above"
              floor_strike=82499.99, strike_type=greater
             → category=crypto, asset=BTC, direction=above, threshold=82500,
               settlement_date=2026-02-05, settlement_time="5pm EST"
    """

    # Months
    MONTHS = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    }

    # Asset patterns
    CRYPTO_ASSETS = {
        'bitcoin': 'BTC', 'btc': 'BTC',
        'ethereum': 'ETH', 'eth': 'ETH',
        'solana': 'SOL', 'sol': 'SOL',
    }

    @classmethod
    def parse_polymarket_market(cls, market: Dict, event: Dict) -> Optional[ParsedMarket]:
        """Parse a Polymarket market into structured fields."""
        try:
            question = market.get("question", "")
            event_title = event.get("title", "")
            desc = market.get("description", "")
            end_date_str = market.get("endDate", "")
            q_lower = question.lower()
            et_lower = event_title.lower()

            # Parse prices
            prices_raw = market.get("outcomePrices", "[]")
            if isinstance(prices_raw, str):
                prices = json.loads(prices_raw)
            else:
                prices = prices_raw
            yes_price = float(prices[0]) if len(prices) > 0 else 0.0
            no_price = float(prices[1]) if len(prices) > 1 else 1.0 - yes_price

            # Skip markets with zero/near-zero prices (dead markets)
            if yes_price <= 0.001 and no_price <= 0.001:
                return None

            volume = float(market.get("volume24hr", 0) or 0)
            if volume <= 0:
                volume = float(market.get("volume", 0) or 0)
            bid = float(market.get("bestBid", 0) or 0)
            ask = float(market.get("bestAsk", 0) or 0)

            mkt_id = market.get("conditionId", market.get("id", ""))

            # Determine category and parse structured fields
            category = cls._classify_category_pm(q_lower, et_lower, desc.lower())
            asset_or_topic = cls._extract_asset_pm(q_lower, et_lower, category)
            direction = cls._extract_direction_pm(q_lower)
            threshold, threshold_unit = cls._extract_threshold_pm(q_lower)
            settlement_date = cls._extract_date_pm(q_lower, end_date_str)
            settlement_time = cls._extract_resolution_time_pm(desc)
            settlement_source = cls._extract_source_pm(desc)
            person = cls._extract_person_pm(q_lower, et_lower)

            if not category or not asset_or_topic:
                return None

            return ParsedMarket(
                platform="polymarket",
                market_id=mkt_id,
                title=question[:150],
                event_title=event_title[:150],
                category=category,
                asset_or_topic=asset_or_topic,
                direction=direction,
                threshold=threshold,
                threshold_unit=threshold_unit,
                settlement_date=settlement_date,
                settlement_time_str=settlement_time,
                settlement_source=settlement_source,
                person_or_entity=person,
                yes_price=yes_price,
                no_price=no_price,
                volume=volume,
                bid=bid,
                ask=ask,
                extra={
                    "event_id": event.get("id", ""),
                    "slug": market.get("slug", ""),
                    "end_date": end_date_str,
                    "total_volume": float(market.get("volume", 0) or 0),
                },
            )
        except Exception as e:
            logger.debug(f"PM parse error: {e}")
            return None

    @classmethod
    def parse_kalshi_market(cls, market: Dict, event: Dict) -> Optional[ParsedMarket]:
        """Parse a Kalshi market into structured fields."""
        try:
            ticker = market.get("ticker", "")
            title = market.get("title", "")
            subtitle = market.get("subtitle", "")
            event_title = event.get("title", "")
            event_ticker = market.get("event_ticker", "")
            rules = market.get("rules_primary", "")
            t_lower = title.lower()
            et_lower = event_title.lower()
            series_ticker = event.get("series_ticker", "")

            # Parse prices (Kalshi in cents 0-100)
            yes_bid = market.get("yes_bid", 0) or 0
            yes_ask = market.get("yes_ask", 0) or 0
            if yes_bid > 0 and yes_ask > 0:
                yes_price = (yes_bid + yes_ask) / 2.0 / 100.0
            elif yes_bid > 0:
                yes_price = yes_bid / 100.0
            elif yes_ask > 0:
                yes_price = yes_ask / 100.0
            else:
                yes_price = 0.0
            no_price = 1.0 - yes_price

            volume = float(market.get("volume_24h", 0) or 0)
            if volume <= 0:
                volume = float(market.get("volume", 0) or 0)

            # Determine category from series or event
            category = cls._classify_category_kalshi(series_ticker, event.get("category", ""), t_lower)
            asset_or_topic = cls._extract_asset_kalshi(series_ticker, t_lower, et_lower)

            if not category or not asset_or_topic:
                return None

            # Extract structured fields
            strike_type = market.get("strike_type", "")
            floor_strike = market.get("floor_strike")
            cap_strike = market.get("cap_strike")

            direction = cls._extract_direction_kalshi(strike_type, t_lower, subtitle.lower())
            threshold, threshold_unit = cls._extract_threshold_kalshi(
                floor_strike, cap_strike, subtitle, t_lower, series_ticker)

            # Settlement date from event
            settlement_date = cls._extract_date_kalshi(event, market)
            settlement_time = cls._extract_time_kalshi(event, market)
            settlement_source = cls._extract_source_kalshi(rules, series_ticker)
            person = cls._extract_person_kalshi(t_lower, subtitle.lower(), event_ticker)

            return ParsedMarket(
                platform="kalshi",
                market_id=ticker,
                title=title[:150],
                event_title=event_title[:150],
                category=category,
                asset_or_topic=asset_or_topic,
                direction=direction,
                threshold=threshold,
                threshold_unit=threshold_unit,
                settlement_date=settlement_date,
                settlement_time_str=settlement_time,
                settlement_source=settlement_source,
                person_or_entity=person,
                yes_price=yes_price,
                no_price=no_price,
                volume=volume,
                bid=yes_bid / 100.0 if yes_bid else 0.0,
                ask=yes_ask / 100.0 if yes_ask else 0.0,
                extra={
                    "event_ticker": event_ticker,
                    "series_ticker": series_ticker,
                    "close_time": market.get("close_time", ""),
                    "expiration_time": market.get("expiration_time", ""),
                    "floor_strike": floor_strike,
                    "cap_strike": cap_strike,
                    "open_interest": market.get("open_interest", 0),
                },
            )
        except Exception as e:
            logger.debug(f"Kalshi parse error: {e}")
            return None

    # ---- Category classification ----

    @classmethod
    def _classify_category_pm(cls, q: str, et: str, desc: str) -> str:
        combined = f"{q} {et}"
        if any(k in combined for k in ['bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol', 'crypto']):
            # Check if it's a price market (not just mentioning crypto)
            if any(k in combined for k in ['price', 'above', 'below', 'reach', 'hit', 'dip']):
                return "crypto"
        if any(k in combined for k in ['fed ', 'fomc', 'federal reserve', 'interest rate']):
            return "economics"
        if any(k in combined for k in ['cpi', 'inflation', 'consumer price']):
            return "economics"
        if any(k in combined for k in ['gdp', 'gross domestic']):
            return "economics"
        if any(k in combined for k in ['jobs', 'payroll', 'nonfarm', 'unemployment']):
            return "economics"
        if 'recession' in combined:
            return "economics"
        return ""

    @classmethod
    def _classify_category_kalshi(cls, series: str, category: str, title: str) -> str:
        if series in ('KXBTCD', 'KXETHD', 'KXBTC', 'KXETH'):
            return "crypto"
        if series in ('KXFED', 'KXFEDDECISION', 'KXCPIYOY', 'KXCPICORE', 'KXCPI',
                       'KXGDP', 'KXPAYROLLS', 'KXU3', 'KXRECSSNBER'):
            return "economics"
        if series == 'KXFEDCHAIRNOM':
            return "politics"
        if category in ('Crypto',):
            return "crypto"
        if category in ('Economics',):
            return "economics"
        if category in ('Politics', 'Elections'):
            return "politics"
        return ""

    # ---- Asset/topic extraction ----

    @classmethod
    def _extract_asset_pm(cls, q: str, et: str, category: str) -> str:
        combined = f"{q} {et}"
        if category == "crypto":
            for keyword, asset in cls.CRYPTO_ASSETS.items():
                if keyword in combined:
                    return asset
        if category == "economics":
            if any(k in combined for k in ['fed chair', 'fed nominee']):
                return "fed_chair"
            if 'fed' in combined and any(k in combined for k in ['rate', 'cut', 'hike', 'decision', 'decrease', 'increase', 'no change']):
                return "fed_rate"
            if any(k in combined for k in ['cpi core', 'core cpi']):
                return "cpi_core"
            if any(k in combined for k in ['cpi', 'inflation']):
                return "cpi"
            if 'gdp' in combined:
                return "gdp"
            if any(k in combined for k in ['payroll', 'jobs', 'nonfarm']):
                return "payrolls"
            if 'unemployment' in combined:
                return "unemployment"
            if 'recession' in combined:
                return "recession"
        return ""

    @classmethod
    def _extract_asset_kalshi(cls, series: str, t: str, et: str) -> str:
        series_map = {
            'KXBTCD': 'BTC', 'KXBTC': 'BTC',
            'KXETHD': 'ETH', 'KXETH': 'ETH',
            'KXFED': 'fed_rate', 'KXFEDDECISION': 'fed_decision',
            'KXCPIYOY': 'cpi', 'KXCPICORE': 'cpi_core', 'KXCPI': 'cpi',
            'KXGDP': 'gdp', 'KXPAYROLLS': 'payrolls',
            'KXU3': 'unemployment', 'KXRECSSNBER': 'recession',
            'KXFEDCHAIRNOM': 'fed_chair',
        }
        return series_map.get(series, "")

    # ---- Direction extraction ----

    @classmethod
    def _extract_direction_pm(cls, q: str) -> str:
        if 'above' in q or 'higher than' in q or 'more than' in q:
            return "above"
        if 'below' in q or 'less than' in q or 'lower than' in q:
            return "below"
        if 'between' in q:
            return "between"
        if 'reach' in q or 'hit' in q:
            return "above"  # "Will BTC reach $100K" = above
        if 'dip to' in q or 'dip below' in q or 'fall to' in q:
            return "below"
        if 'decrease' in q or 'cut' in q:
            return "decrease"
        if 'increase' in q or 'hike' in q:
            return "increase"
        if 'no change' in q:
            return "no_change"
        if 'nominate' in q or 'nominee' in q:
            return "nomination"
        return "unknown"

    @classmethod
    def _extract_direction_kalshi(cls, strike_type: str, title: str, subtitle: str) -> str:
        combined = f"{title} {subtitle}"
        if strike_type == "greater":
            return "above"
        if strike_type == "less":
            return "below"
        if strike_type == "between":
            return "between"
        if 'above' in combined or 'or above' in combined:
            return "above"
        if 'below' in combined or 'or below' in combined:
            return "below"
        if 'between' in combined:
            return "between"
        if 'decrease' in combined or 'cut' in combined:
            return "decrease"
        if 'increase' in combined or 'hike' in combined:
            return "increase"
        if 'no change' in combined or 'hold' in combined:
            return "no_change"
        if 'nominate' in combined or 'nominee' in combined:
            return "nomination"
        return "unknown"

    # ---- Threshold extraction ----

    @classmethod
    def _extract_threshold_pm(cls, q: str) -> Tuple[Optional[float], str]:
        """Extract numeric threshold from PM question."""
        # Dollar amounts: $82,000 or $82000
        m = re.search(r'\$([0-9,]+(?:\.[0-9]+)?)', q)
        if m:
            val = float(m.group(1).replace(',', ''))
            return val, "dollars"

        # Percentage: 25 bps, 0.25%, 2.3%
        m = re.search(r'(\d+(?:\.\d+)?)\s*bps', q)
        if m:
            return float(m.group(1)), "bps"
        m = re.search(r'(\d+(?:\.\d+)?)\s*%', q)
        if m:
            return float(m.group(1)), "percent"

        # Plain number after "above" or "below"
        m = re.search(r'(?:above|below|more than|less than|reach|hit)\s+(\d+(?:,\d+)*(?:\.\d+)?)', q)
        if m:
            return float(m.group(1).replace(',', '')), "number"

        return None, ""

    @classmethod
    def _extract_threshold_kalshi(cls, floor_strike, cap_strike, subtitle: str,
                                   title: str, series: str) -> Tuple[Optional[float], str]:
        """Extract threshold from Kalshi market data."""
        # For crypto daily markets, floor_strike is the threshold
        if series in ('KXBTCD', 'KXETHD', 'KXBTC', 'KXETH'):
            if floor_strike is not None:
                try:
                    # Kalshi uses e.g. 82499.99 for "above $82,500"
                    val = float(floor_strike)
                    # Round to nearest 500 (Kalshi uses X499.99 for "above X500")
                    rounded = round((val + 0.01) / 500) * 500
                    return rounded, "dollars"
                except (ValueError, TypeError):
                    pass

        # For economics, extract from subtitle/title
        if series in ('KXFED',):
            # Fed rate: threshold is rate level like 3.25
            m = re.search(r'(\d+\.\d+)%?', subtitle + " " + title)
            if m:
                return float(m.group(1)), "percent"

        if series in ('KXFEDDECISION',):
            # Fed decision: bps change
            m = re.search(r'(\d+)\+?\s*bps', (subtitle + " " + title).lower())
            if m:
                return float(m.group(1)), "bps"

        if series in ('KXCPIYOY', 'KXCPICORE', 'KXCPI'):
            m = re.search(r'(\d+\.?\d*)%', subtitle + " " + title)
            if m:
                return float(m.group(1)), "percent"

        if series in ('KXGDP',):
            m = re.search(r'(\d+\.?\d*)%', subtitle + " " + title)
            if m:
                return float(m.group(1)), "percent"

        if series in ('KXPAYROLLS',):
            m = re.search(r'(\d+[,.]?\d*)', subtitle)
            if m:
                return float(m.group(1).replace(',', '')), "count"

        # Fallback: try to get from floor_strike
        if floor_strike is not None:
            try:
                return float(floor_strike), "number"
            except (ValueError, TypeError):
                pass

        return None, ""

    # ---- Date extraction ----

    @classmethod
    def _extract_date_pm(cls, q: str, end_date_str: str) -> Optional[datetime]:
        """Extract settlement date from PM question or endDate."""
        # Try to parse from question: "on February 5"
        for month_name, month_num in cls.MONTHS.items():
            pattern = rf'{month_name}\s+(\d{{1,2}})(?:\s*,?\s*(\d{{4}}))?'
            m = re.search(pattern, q, re.IGNORECASE)
            if m:
                day = int(m.group(1))
                year = int(m.group(2)) if m.group(2) else datetime.now().year
                try:
                    return datetime(year, month_num, day, tzinfo=timezone.utc)
                except ValueError:
                    continue

        # Try "March 2026 meeting" style
        for month_name, month_num in cls.MONTHS.items():
            m = re.search(rf'{month_name}\s+(\d{{4}})', q, re.IGNORECASE)
            if m:
                year = int(m.group(1))
                # Use 1st of month for meeting-style dates
                try:
                    return datetime(year, month_num, 1, tzinfo=timezone.utc)
                except ValueError:
                    continue

        # Fallback: endDate
        if end_date_str:
            try:
                return datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass

        return None

    @classmethod
    def _extract_date_kalshi(cls, event: Dict, market: Dict) -> Optional[datetime]:
        """Extract settlement date from Kalshi event/market."""
        # Prefer event's strike_date
        strike_date = event.get("strike_date", "")
        if strike_date:
            try:
                return datetime.fromisoformat(strike_date.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass

        # Expected expiration
        exp = market.get("expected_expiration_time", "")
        if exp:
            try:
                return datetime.fromisoformat(exp.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass

        # Close time
        close = market.get("close_time", "")
        if close:
            try:
                return datetime.fromisoformat(close.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass

        return None

    # ---- Resolution time extraction ----

    @classmethod
    def _extract_resolution_time_pm(cls, desc: str) -> str:
        """Extract specific resolution time from PM description."""
        desc_lower = desc.lower()
        # "12:00 in the ET timezone (noon)"
        if 'noon' in desc_lower or '12:00' in desc_lower:
            return "noon ET"
        # Other specific times
        m = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm)\s*(?:et|est|utc))', desc_lower)
        if m:
            return m.group(1).upper()
        return ""

    @classmethod
    def _extract_time_kalshi(cls, event: Dict, market: Dict) -> str:
        """Extract resolution time from Kalshi event."""
        sub = event.get("sub_title", "")
        # "On Feb 5, 2026 at 5pm EST"
        m = re.search(r'at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*(?:est|et|utc))', sub, re.IGNORECASE)
        if m:
            return m.group(1).upper()
        return ""

    # ---- Resolution source extraction ----

    @classmethod
    def _extract_source_pm(cls, desc: str) -> str:
        desc_lower = desc.lower()
        if 'binance' in desc_lower:
            return "Binance"
        if 'coingecko' in desc_lower:
            return "CoinGecko"
        if 'bls' in desc_lower or 'bureau of labor' in desc_lower:
            return "BLS"
        if 'bea' in desc_lower or 'bureau of economic' in desc_lower:
            return "BEA"
        return ""

    @classmethod
    def _extract_source_kalshi(cls, rules: str, series: str) -> str:
        rules_lower = rules.lower()
        if 'cf benchmarks' in rules_lower or 'brti' in rules_lower:
            return "BRTI"
        if series.startswith('KXBTC') or series.startswith('KXETH'):
            return "BRTI"  # Default for crypto
        if 'bls' in rules_lower:
            return "BLS"
        if 'bea' in rules_lower:
            return "BEA"
        return ""

    # ---- Person extraction ----

    @classmethod
    def _extract_person_pm(cls, q: str, et: str) -> str:
        """Extract person name for nomination markets."""
        # "Will Trump nominate Kevin Warsh as the next Fed chair?"
        m = re.search(r'nominate\s+(.+?)\s+(?:as|for)', q, re.IGNORECASE)
        if m:
            return m.group(1).strip().lower()
        return ""

    @classmethod
    def _extract_person_kalshi(cls, title: str, subtitle: str, event_ticker: str) -> str:
        m = re.search(r'nominate\s+(.+?)\s+(?:as|for)', title, re.IGNORECASE)
        if m:
            return m.group(1).strip().lower()
        # Subtitle often has person name
        if 'KXFEDCHAIRNOM' in event_ticker:
            # "Will Trump next nominate Judy Shelton as Fed Chair?"
            m = re.search(r'nominate\s+(.+?)\s+as', title, re.IGNORECASE)
            if m:
                return m.group(1).strip().lower()
        return ""


# ============================================================================
# MARKET FETCHERS
# ============================================================================

class PolymarketFetcher:
    """Fetch and parse all active markets from Polymarket."""

    def fetch_all_relevant_markets(self) -> List[ParsedMarket]:
        """Fetch active PM events, filter for matchable categories, parse."""
        all_parsed = []
        seen_ids = set()

        # Paginate through events
        for offset in range(0, 500, 100):
            events = http_get(PM_GAMMA_EVENTS, {
                "active": "true",
                "closed": "false",
                "limit": "100",
                "offset": str(offset),
                "order": "volume24hr",
                "ascending": "false",
            })
            if not events or not isinstance(events, list) or len(events) == 0:
                break

            for evt in events:
                evt_title = evt.get("title", "").lower()

                # Quick pre-filter: skip events that are clearly not matchable
                matchable_keywords = [
                    'bitcoin', 'btc', 'ethereum', 'eth',
                    'fed', 'fomc', 'interest rate',
                    'cpi', 'inflation', 'gdp',
                    'jobs', 'payroll', 'unemployment', 'nonfarm',
                    'recession',
                ]
                if not any(k in evt_title for k in matchable_keywords):
                    continue

                # Get markets for this event
                markets = evt.get("markets", [])

                for mkt in markets:
                    mkt_id = mkt.get("conditionId", mkt.get("id", ""))
                    if mkt_id in seen_ids:
                        continue
                    seen_ids.add(mkt_id)

                    parsed = MarketParser.parse_polymarket_market(mkt, evt)
                    if parsed:
                        all_parsed.append(parsed)

            # If we got fewer than 100, we've reached the end
            if len(events) < 100:
                break

        return all_parsed


class KalshiFetcher:
    """Fetch and parse markets from Kalshi for series of interest."""

    def fetch_all_relevant_markets(self) -> List[ParsedMarket]:
        """Fetch markets from all series of interest, parse them."""
        all_parsed = []
        seen_tickers = set()

        for series in KALSHI_SERIES_OF_INTEREST:
            # First get events for this series
            events_data = http_get(KALSHI_EVENTS, {
                "status": "open",
                "limit": "50",
                "series_ticker": series,
            })
            if not events_data or not isinstance(events_data, dict):
                continue

            events = events_data.get("events", [])
            events_by_ticker = {e["event_ticker"]: e for e in events}

            # Then get markets for each event
            for evt in events:
                event_ticker = evt["event_ticker"]

                markets_data = http_get(KALSHI_MARKETS, {
                    "status": "open",
                    "limit": "200",
                    "event_ticker": event_ticker,
                })
                if not markets_data or not isinstance(markets_data, dict):
                    continue

                for mkt in markets_data.get("markets", []):
                    ticker = mkt.get("ticker", "")
                    if ticker in seen_tickers:
                        continue
                    seen_tickers.add(ticker)

                    # Enrich event data with series_ticker
                    evt_enriched = {**evt, "series_ticker": series}
                    parsed = MarketParser.parse_kalshi_market(mkt, evt_enriched)
                    if parsed:
                        all_parsed.append(parsed)

        return all_parsed


# ============================================================================
# MATCHING ENGINE
# ============================================================================

class MatchingEngine:
    """Match Polymarket and Kalshi markets using structured field comparison.

    Algorithm:
      1. Group all markets by (category, asset_or_topic)
      2. Within each group, compare PM↔Kalshi pairs
      3. Score each potential pair on multiple dimensions
      4. Only accept pairs with score > MATCH_SCORE_THRESHOLD
    """

    @staticmethod
    def compute_match_score(pm: ParsedMarket, k: ParsedMarket) -> Tuple[int, List[str], List[str]]:
        """Compute match score (0-100) between a PM and Kalshi market.

        Returns (score, reasons, warnings).
        """
        score = 0
        reasons = []
        warnings = []

        # ---- Category match (required, 0 or 10 pts) ----
        if pm.category != k.category:
            return 0, ["category mismatch"], []
        score += 10
        reasons.append(f"category={pm.category}")

        # ---- Asset/topic match (required, 0 or 20 pts) ----
        asset_match = MatchingEngine._asset_match(pm.asset_or_topic, k.asset_or_topic)
        if not asset_match:
            return 0, [f"asset mismatch: {pm.asset_or_topic} vs {k.asset_or_topic}"], []
        score += 20
        reasons.append(f"asset={pm.asset_or_topic}")

        # ---- Direction match (required for crypto/threshold markets, 0 or 15 pts) ----
        dir_match = MatchingEngine._direction_match(pm.direction, k.direction)
        if not dir_match:
            return 0, [f"direction mismatch: {pm.direction} vs {k.direction}"], []
        score += 15
        reasons.append(f"direction={pm.direction}↔{k.direction}")

        # ---- Date match (required, 0-20 pts) ----
        date_score, date_reason = MatchingEngine._date_match(pm, k)
        if date_score == 0:
            return 0, [date_reason], []
        score += date_score
        reasons.append(date_reason)

        # ---- Threshold match (0-20 pts, required for crypto) ----
        threshold_score, threshold_reason = MatchingEngine._threshold_match(pm, k)
        if pm.category == "crypto" and threshold_score == 0:
            return 0, [threshold_reason], []
        score += threshold_score
        if threshold_reason:
            reasons.append(threshold_reason)

        # ---- Resolution time proximity (0-10 pts, bonus) ----
        time_score, time_reason = MatchingEngine._time_match(pm, k)
        score += time_score
        if time_reason:
            if time_score < 5:
                warnings.append(time_reason)
            else:
                reasons.append(time_reason)

        # ---- Resolution source match (0-5 pts, bonus) ----
        if pm.settlement_source and k.settlement_source:
            if pm.settlement_source == k.settlement_source:
                score += 5
                reasons.append(f"same source: {pm.settlement_source}")
            else:
                warnings.append(f"different sources: {pm.settlement_source} vs {k.settlement_source}")

        # ---- Person/entity match (required for nomination markets) ----
        if pm.direction == "nomination" or k.direction == "nomination":
            if pm.person_or_entity and k.person_or_entity:
                # Fuzzy match on person name
                if MatchingEngine._person_match(pm.person_or_entity, k.person_or_entity):
                    score += 10
                    reasons.append(f"person={pm.person_or_entity}")
                else:
                    return 0, [f"person mismatch: {pm.person_or_entity} vs {k.person_or_entity}"], []

        return min(score, 100), reasons, warnings

    @staticmethod
    def _asset_match(pm_asset: str, k_asset: str) -> bool:
        """Check if assets match (with fuzzy equivalences)."""
        if pm_asset == k_asset:
            return True
        # Fed rate / Fed decision are related
        if {pm_asset, k_asset} <= {'fed_rate', 'fed_decision'}:
            return True
        return False

    @staticmethod
    def _direction_match(pm_dir: str, k_dir: str) -> bool:
        """Check if directions are compatible."""
        if pm_dir == k_dir:
            return True
        # "above" matches "above", etc.
        compatible = {
            ('above', 'above'), ('below', 'below'), ('between', 'between'),
            ('increase', 'increase'), ('decrease', 'decrease'),
            ('no_change', 'no_change'), ('nomination', 'nomination'),
        }
        return (pm_dir, k_dir) in compatible

    @staticmethod
    def _date_match(pm: ParsedMarket, k: ParsedMarket) -> Tuple[int, str]:
        """Score date similarity. Returns (0-20, reason)."""
        if not pm.settlement_date or not k.settlement_date:
            return 0, "missing settlement date"

        # Normalize to date-only for comparison
        pm_date = pm.settlement_date.date()
        k_date = k.settlement_date.date()
        delta = abs((pm_date - k_date).days)

        if delta == 0:
            return 20, f"same date: {pm_date}"
        elif delta == 1:
            return 15, f"dates 1 day apart: {pm_date} vs {k_date}"
        elif delta <= 3:
            # For monthly macro events (CPI, GDP, etc.)
            if pm.category == "economics":
                return 10, f"dates {delta} days apart (macro): {pm_date} vs {k_date}"
            return 5, f"dates {delta} days apart: {pm_date} vs {k_date}"
        elif pm.category == "economics" and delta <= 30:
            # Same month for economics (Fed meeting month)
            if pm_date.month == k_date.month and pm_date.year == k_date.year:
                return 10, f"same month: {pm_date.strftime('%Y-%m')} ({delta} days apart)"
            return 0, f"different months: {pm_date} vs {k_date}"
        else:
            return 0, f"dates too far apart ({delta} days): {pm_date} vs {k_date}"

    @staticmethod
    def _threshold_match(pm: ParsedMarket, k: ParsedMarket) -> Tuple[int, str]:
        """Score threshold similarity. Returns (0-20, reason)."""
        if pm.threshold is None or k.threshold is None:
            if pm.category == "crypto":
                return 0, "missing threshold for crypto market"
            return 5, ""  # OK for non-threshold markets

        # Same unit check
        if pm.threshold_unit != k.threshold_unit and pm.threshold_unit and k.threshold_unit:
            # Allow dollars↔dollars, percent↔percent
            if not ({pm.threshold_unit, k.threshold_unit} <= {'dollars', 'number'}):
                return 0, f"unit mismatch: {pm.threshold_unit} vs {k.threshold_unit}"

        # Compare values
        if pm.threshold == 0 or k.threshold == 0:
            if pm.threshold == k.threshold:
                return 20, f"thresholds both 0"
            return 0, f"threshold has zero: {pm.threshold} vs {k.threshold}"

        # Calculate percentage difference
        avg = (abs(pm.threshold) + abs(k.threshold)) / 2
        pct_diff = abs(pm.threshold - k.threshold) / avg * 100

        if pct_diff <= 0.5:
            return 20, f"thresholds match: {pm.threshold} ≈ {k.threshold} ({pct_diff:.1f}% diff)"
        elif pct_diff <= 2:
            return 15, f"thresholds close: {pm.threshold} vs {k.threshold} ({pct_diff:.1f}% diff)"
        elif pct_diff <= 5:
            return 10, f"thresholds near: {pm.threshold} vs {k.threshold} ({pct_diff:.1f}% diff)"
        elif pct_diff <= 10:
            return 5, f"thresholds approximate: {pm.threshold} vs {k.threshold} ({pct_diff:.1f}% diff)"
        else:
            return 0, f"thresholds too different: {pm.threshold} vs {k.threshold} ({pct_diff:.1f}% diff)"

    @staticmethod
    def _time_match(pm: ParsedMarket, k: ParsedMarket) -> Tuple[int, str]:
        """Score resolution time proximity. Returns (0-10, reason)."""
        pm_time = pm.settlement_time_str.lower().strip()
        k_time = k.settlement_time_str.lower().strip()

        if not pm_time or not k_time:
            return 3, ""  # Unknown time, slight penalty

        # Parse to hours for comparison
        pm_hour = MatchingEngine._parse_hour(pm_time)
        k_hour = MatchingEngine._parse_hour(k_time)

        if pm_hour is None or k_hour is None:
            return 3, f"unparseable times: {pm_time} vs {k_time}"

        diff = abs(pm_hour - k_hour)

        if diff <= 1:
            return 10, f"resolution times close: {pm_time} vs {k_time} ({diff}h apart)"
        elif diff <= 3:
            return 6, f"resolution times {diff}h apart: {pm_time} vs {k_time}"
        elif diff <= 5:
            return 2, f"resolution times {diff}h apart: {pm_time} vs {k_time} ⚠️ risky"
        else:
            return 0, f"resolution times too far apart ({diff}h): {pm_time} vs {k_time}"

    @staticmethod
    def _parse_hour(time_str: str) -> Optional[int]:
        """Parse a time string to hour (0-23)."""
        time_str = time_str.strip().lower()

        if 'noon' in time_str:
            return 12

        m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', time_str)
        if m:
            hour = int(m.group(1))
            ampm = m.group(3)
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
            return hour

        return None

    @staticmethod
    def _person_match(p1: str, p2: str) -> bool:
        """Fuzzy person name match."""
        p1 = p1.strip().lower()
        p2 = p2.strip().lower()
        if p1 == p2:
            return True
        # Check if one contains the other (e.g., "kevin warsh" in "kevin warsh")
        if p1 in p2 or p2 in p1:
            return True
        # Check last name match
        p1_parts = p1.split()
        p2_parts = p2.split()
        if p1_parts and p2_parts:
            if p1_parts[-1] == p2_parts[-1]:
                return True
        return False

    def find_all_pairs(self, pm_markets: List[ParsedMarket],
                       kalshi_markets: List[ParsedMarket]) -> List[MatchedPair]:
        """Find all valid market pairs between PM and Kalshi."""
        # Group by match key
        pm_groups: Dict[str, List[ParsedMarket]] = defaultdict(list)
        k_groups: Dict[str, List[ParsedMarket]] = defaultdict(list)

        for m in pm_markets:
            pm_groups[m.match_key()].append(m)
        for m in kalshi_markets:
            k_groups[m.match_key()].append(m)

        # Find overlapping groups
        common_keys = set(pm_groups.keys()) & set(k_groups.keys())
        logger.info(f"  Match groups: PM has {len(pm_groups)} groups, "
                    f"Kalshi has {len(k_groups)} groups, "
                    f"{len(common_keys)} in common")
        for key in common_keys:
            logger.info(f"    Group '{key}': {len(pm_groups[key])} PM × {len(k_groups[key])} Kalshi")

        # Score all cross-platform pairs within each group
        candidates = []
        for key in common_keys:
            for pm in pm_groups[key]:
                for k in k_groups[key]:
                    score, reasons, warnings = self.compute_match_score(pm, k)

                    if score >= MATCH_SCORE_THRESHOLD:
                        pair_id = f"{pm.asset_or_topic}_{pm.market_id[:8]}_{k.market_id[:12]}"
                        mp = MatchedPair(
                            pair_id=pair_id,
                            pm_market=pm,
                            kalshi_market=k,
                            match_score=score,
                            match_reasons=reasons,
                            match_warnings=warnings,
                            spread=pm.yes_price - k.yes_price,
                            last_update=time.time(),
                        )
                        candidates.append(mp)
                        logger.info(
                            f"  ✅ MATCHED (score={score}): "
                            f"PM '{pm.title[:60]}' ↔ K '{k.title[:40]}|{k.extra.get('series_ticker','')}' "
                            f"| reasons: {', '.join(reasons)}"
                        )
                        if warnings:
                            logger.info(f"      ⚠️ warnings: {', '.join(warnings)}")
                    elif score > 40:
                        # Log near-misses for debugging
                        logger.info(
                            f"  ❌ REJECTED (score={score}): "
                            f"PM '{pm.title[:50]}' vs K '{k.title[:40]}' "
                            f"| {', '.join(reasons)}"
                        )

        # De-duplicate: for each PM market, keep only the best Kalshi match
        # and vice versa
        matched = self._deduplicate_pairs(candidates)

        return matched

    def _deduplicate_pairs(self, candidates: List[MatchedPair]) -> List[MatchedPair]:
        """Keep only the best match for each individual market."""
        if not candidates:
            return []

        # Sort by score descending
        candidates.sort(key=lambda p: p.match_score, reverse=True)

        used_pm: Set[str] = set()
        used_k: Set[str] = set()
        result = []

        for mp in candidates:
            pm_id = mp.pm_market.market_id
            k_id = mp.kalshi_market.market_id

            if pm_id in used_pm or k_id in used_k:
                continue

            used_pm.add(pm_id)
            used_k.add(k_id)
            result.append(mp)

        return result


# ============================================================================
# SIGNAL GENERATOR
# ============================================================================

class SignalGenerator:
    """Generate trading signals from matched pairs' price history."""

    def __init__(self):
        self.price_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=PRICE_HISTORY_MAX))
        self.spread_stats: Dict[str, Dict] = {}

    def record_prices(self, pair_id: str, pm_price: float, k_price: float, spread: float):
        """Record a price observation."""
        self.price_history[pair_id].append(
            (time.time(), pm_price, k_price, spread))

        spreads = [p[3] for p in self.price_history[pair_id]]
        if len(spreads) >= 10:
            self.spread_stats[pair_id] = {
                "mean": statistics.mean(spreads),
                "stdev": statistics.stdev(spreads) if len(spreads) >= 2 else 0.0,
                "count": len(spreads),
                "min": min(spreads),
                "max": max(spreads),
            }

    def check_pm_momentum(self, pair_id: str) -> Optional[Dict]:
        """Check if PM moved significantly while Kalshi is flat."""
        history = self.price_history[pair_id]
        if len(history) < 3:
            return None

        now = time.time()
        cutoff = now - PM_MOMENTUM_WINDOW
        recent = [(t, pm, k, s) for t, pm, k, s in history if t >= cutoff]
        if len(recent) < 2:
            return None

        first_pm = recent[0][1]
        last_pm = recent[-1][1]
        pm_move = last_pm - first_pm

        first_k = recent[0][2]
        last_k = recent[-1][2]
        k_move = last_k - first_k

        if abs(pm_move) >= PM_MOVE_THRESHOLD and abs(k_move) < PM_MOVE_THRESHOLD * 0.5:
            return {
                "type": "PM_MOMENTUM",
                "pair_id": pair_id,
                "pm_move": pm_move,
                "k_move": k_move,
                "direction": "YES" if pm_move > 0 else "NO",
                "current_spread": recent[-1][3],
                "strength": abs(pm_move) / PM_MOVE_THRESHOLD,
                "window_seconds": now - recent[0][0],
            }
        return None

    def check_spread_sigma(self, pair_id: str, current_spread: float) -> Optional[Dict]:
        """Check if spread exceeds historical 2σ."""
        stats = self.spread_stats.get(pair_id)
        if not stats or stats["count"] < 20 or stats["stdev"] < 0.001:
            return None

        z_score = (abs(current_spread) - abs(stats["mean"])) / stats["stdev"]
        if z_score >= SIGMA_THRESHOLD:
            return {
                "type": "SPREAD_SIGMA",
                "pair_id": pair_id,
                "current_spread": current_spread,
                "mean_spread": stats["mean"],
                "stdev": stats["stdev"],
                "z_score": z_score,
                "direction": "YES" if current_spread > 0 else "NO",
                "strength": z_score / SIGMA_THRESHOLD,
            }
        return None

    def generate_signals(self, matched_pairs: Dict[str, MatchedPair]) -> List[Dict]:
        """Generate signals from all matched pairs."""
        signals = []
        for pair_id, mp in matched_pairs.items():
            pm_price = mp.pm_market.yes_price
            k_price = mp.kalshi_market.yes_price
            spread = mp.spread

            self.record_prices(pair_id, pm_price, k_price, spread)

            momentum = self.check_pm_momentum(pair_id)
            if momentum:
                signals.append(momentum)

            sigma = self.check_spread_sigma(pair_id, spread)
            if sigma:
                signals.append(sigma)

        return signals


# ============================================================================
# PAPER TRADER
# ============================================================================

class PaperTrader:
    """Simulate trades based on signals. Track PnL."""

    def __init__(self):
        self.trades: List[PaperTrade] = []
        self.trade_counter = 0
        self.total_pnl = 0.0

    @property
    def open_trades(self) -> List[PaperTrade]:
        return [t for t in self.trades if t.status == "open"]

    @property
    def current_exposure(self) -> float:
        return sum(t.size_usd for t in self.open_trades)

    def can_enter(self, pair_id: str, spread: float) -> Tuple[bool, str]:
        if abs(spread) < SPREAD_ENTRY_MIN:
            return False, f"spread {abs(spread):.3f} < min {SPREAD_ENTRY_MIN}"
        if self.current_exposure + TRADE_MAX_SIZE > TOTAL_MAX_EXPOSURE:
            return False, f"exposure limit"
        for t in self.open_trades:
            if t.pair_id == pair_id:
                return False, f"already have open trade for {pair_id}"
        return True, "ok"

    def enter_trade(self, signal: Dict, pm_price: float, k_price: float,
                    spread: float, pm_title: str = "", k_title: str = "",
                    category: str = "") -> Optional[PaperTrade]:
        can, reason = self.can_enter(signal["pair_id"], spread)
        if not can:
            logger.info(f"  ⛔ Cannot enter: {reason}")
            return None

        self.trade_counter += 1
        trade_id = f"XP2-{self.trade_counter:04d}"

        trade = PaperTrade(
            trade_id=trade_id,
            pair_id=signal["pair_id"],
            entry_time=time.time(),
            direction=signal["direction"],
            entry_price=k_price,
            pm_price_at_entry=pm_price,
            spread_at_entry=spread,
            size_usd=TRADE_MAX_SIZE,
            pm_title=pm_title,
            kalshi_title=k_title,
        )
        self.trades.append(trade)

        # Extract category from pair_id (format: "category:asset:..." or from matched pair)
        trade_category = category or signal.get("pair_id", "").split(":")[0] if ":" in signal.get("pair_id", "") else "unknown"

        logger.info(
            f"  📈 PAPER TRADE ENTERED: {trade_id} | {signal['pair_id']} "
            f"{signal['direction']} @ K={k_price:.3f} | PM={pm_price:.3f} | "
            f"spread={spread:+.3f} | signal={signal['type']} | "
            f"category={trade_category} | size=${trade.size_usd:.0f}"
        )
        return trade

    def check_exits(self, matched_pairs: Dict[str, MatchedPair]):
        now = time.time()
        for trade in self.open_trades:
            mp = matched_pairs.get(trade.pair_id)
            if not mp:
                continue

            current_k = mp.kalshi_market.yes_price
            current_spread = mp.spread
            age = now - trade.entry_time

            exit_reason = None
            if abs(current_spread) < SPREAD_EXIT_MAX:
                exit_reason = f"spread_narrow ({abs(current_spread):.3f})"
            elif age >= TRADE_TIMEOUT:
                exit_reason = f"timeout ({age/60:.0f}min)"

            if exit_reason:
                self._close_trade(trade, current_k, exit_reason)

    def _close_trade(self, trade: PaperTrade, exit_price: float, reason: str):
        trade.exit_time = time.time()
        trade.exit_price = exit_price
        trade.exit_reason = reason
        trade.status = "closed"

        if trade.direction == "YES":
            price_change = exit_price - trade.entry_price
        else:
            price_change = trade.entry_price - exit_price

        # Fee calculation: Kalshi maker 0.3% + PM ~1.5% per side = ~1.8% per side, 3.6% round trip
        KALSHI_FEE = 0.003  # 0.3% maker
        PM_FEE = 0.015      # ~1.5% average
        ROUND_TRIP_FEE = 2 * (KALSHI_FEE + PM_FEE)  # Entry + Exit on both platforms
        
        gross_pnl = trade.size_usd * price_change
        fee_cost = trade.size_usd * ROUND_TRIP_FEE
        trade.pnl = gross_pnl - fee_cost
        self.total_pnl += trade.pnl
        duration = trade.exit_time - trade.entry_time
        emoji = "✅" if trade.pnl > 0 else "❌"

        logger.info(
            f"  {emoji} PAPER TRADE CLOSED: {trade.trade_id} | {trade.pair_id} "
            f"{trade.direction} | entry={trade.entry_price:.3f} exit={exit_price:.3f} | "
            f"gross=${gross_pnl:+.2f} fees=${fee_cost:.2f} net=${trade.pnl:+.2f} | reason={reason} | "
            f"duration={duration/60:.1f}min | cumPnL=${self.total_pnl:+.2f}"
        )

    def get_summary(self) -> Dict:
        closed = [t for t in self.trades if t.status == "closed"]
        wins = [t for t in closed if t.pnl > 0]
        return {
            "total_trades": len(self.trades),
            "open_trades": len(self.open_trades),
            "closed_trades": len(closed),
            "wins": len(wins),
            "losses": len(closed) - len(wins),
            "win_rate": len(wins) / max(len(closed), 1),
            "total_pnl": self.total_pnl,
            "current_exposure": self.current_exposure,
        }


# ============================================================================
# STATE MANAGER
# ============================================================================

class StateManager:
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.last_save = 0

    def save(self, trader: 'CrossPlatformTrader', force: bool = False):
        now = time.time()
        if not force and (now - self.last_save) < STATE_SAVE_INTERVAL:
            return
        self.last_save = now

        state = {
            "version": "2.0",
            "last_update": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": now - trader.start_time,
            "cycle_count": trader.cycle_count,
            "scan_count": trader.scan_count,
            "data_points_logged": trader.data_points_logged,
            "signals_generated": trader.signals_generated,
            "paper_trading": trader.paper_trader.get_summary(),
            "market_scan": {
                "pm_markets_found": trader.last_pm_count,
                "kalshi_markets_found": trader.last_k_count,
                "valid_pairs": len(trader.active_pairs),
                "last_scan": trader.last_scan_time,
            },
            "active_pairs": {},
            "spread_stats": {},
        }

        for pair_id, mp in trader.active_pairs.items():
            state["active_pairs"][pair_id] = {
                "pm_title": mp.pm_market.title,
                "pm_price": mp.pm_market.yes_price,
                "pm_threshold": mp.pm_market.threshold,
                "pm_settlement": str(mp.pm_market.settlement_date)[:10] if mp.pm_market.settlement_date else None,
                "kalshi_title": mp.kalshi_market.title,
                "kalshi_price": mp.kalshi_market.yes_price,
                "kalshi_threshold": mp.kalshi_market.threshold,
                "kalshi_settlement": str(mp.kalshi_market.settlement_date)[:10] if mp.kalshi_market.settlement_date else None,
                "match_score": mp.match_score,
                "match_reasons": mp.match_reasons,
                "match_warnings": mp.match_warnings,
                "spread": mp.spread,
                "last_update": mp.last_update,
            }

        state["spread_stats"] = dict(trader.signal_gen.spread_stats)

        state["open_trades"] = [
            {
                "trade_id": t.trade_id,
                "pair_id": t.pair_id,
                "direction": t.direction,
                "entry_price": t.entry_price,
                "entry_time": t.entry_time,
                "size_usd": t.size_usd,
                "pm_title": t.pm_title,
                "kalshi_title": t.kalshi_title,
                "age_min": (now - t.entry_time) / 60,
            }
            for t in trader.paper_trader.open_trades
        ]

        try:
            tmp = self.state_file.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(state, f, indent=2, default=str)
            tmp.rename(self.state_file)
        except Exception as e:
            logger.warning(f"State save error: {e}")

    def load_trade_counter(self) -> int:
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    state = json.load(f)
                return state.get("paper_trading", {}).get("total_trades", 0)
        except Exception:
            pass
        return 0


# ============================================================================
# PRICE DATA LOGGER
# ============================================================================

class PriceDataLogger:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.count = 0

    def log(self, pair_id: str, mp: MatchedPair, signals: List[Dict] = None):
        now = datetime.now(timezone.utc)
        record = {
            "ts": now.isoformat(),
            "epoch": time.time(),
            "version": "2.0",
            "pair_id": pair_id,
            "match_score": mp.match_score,
            "pm_title": mp.pm_market.title,
            "pm_price": mp.pm_market.yes_price,
            "pm_bid": mp.pm_market.bid,
            "pm_ask": mp.pm_market.ask,
            "pm_volume": mp.pm_market.volume,
            "pm_market_id": mp.pm_market.market_id,
            "pm_threshold": mp.pm_market.threshold,
            "pm_settlement_time": mp.pm_market.settlement_time_str,
            "k_title": mp.kalshi_market.title,
            "k_price": mp.kalshi_market.yes_price,
            "k_bid": mp.kalshi_market.bid,
            "k_ask": mp.kalshi_market.ask,
            "k_volume": mp.kalshi_market.volume,
            "k_market_id": mp.kalshi_market.market_id,
            "k_threshold": mp.kalshi_market.threshold,
            "k_settlement_time": mp.kalshi_market.settlement_time_str,
            "spread": mp.spread,
            "abs_spread": abs(mp.spread),
            "signals": [s.get("type") for s in (signals or []) if s.get("pair_id") == pair_id],
        }

        try:
            with open(self.filepath, "a") as f:
                f.write(json.dumps(record, default=str) + "\n")
            self.count += 1
        except Exception as e:
            logger.warning(f"JSONL write error: {e}")


# ============================================================================
# PRICE REFRESHER: Update prices for existing pairs without full re-scan
# ============================================================================

class PriceRefresher:
    """Refresh prices for existing matched pairs without doing a full scan."""

    def refresh_pm_price(self, pm: ParsedMarket) -> Optional[ParsedMarket]:
        """Refresh price for a single PM market."""
        mkt_id = pm.market_id
        data = http_get(PM_GAMMA_MARKETS, {"id": pm.extra.get("event_id", "")})
        if not data or not isinstance(data, list):
            # Try by conditionId
            data = http_get(PM_GAMMA_MARKETS, {"conditionId": mkt_id})
        if data and isinstance(data, list):
            for mkt in data:
                cid = mkt.get("conditionId", mkt.get("id", ""))
                if cid == mkt_id:
                    prices_raw = mkt.get("outcomePrices", "[]")
                    if isinstance(prices_raw, str):
                        prices = json.loads(prices_raw)
                    else:
                        prices = prices_raw
                    pm.yes_price = float(prices[0]) if len(prices) > 0 else pm.yes_price
                    pm.no_price = float(prices[1]) if len(prices) > 1 else 1.0 - pm.yes_price
                    pm.volume = float(mkt.get("volume24hr", 0) or 0)
                    pm.bid = float(mkt.get("bestBid", 0) or 0)
                    pm.ask = float(mkt.get("bestAsk", 0) or 0)
                    return pm
        return None

    def refresh_kalshi_price(self, k: ParsedMarket) -> Optional[ParsedMarket]:
        """Refresh price for a single Kalshi market."""
        ticker = k.market_id
        data = http_get(KALSHI_MARKETS, {"ticker": ticker})
        if data and isinstance(data, dict):
            markets = data.get("markets", [])
            for mkt in markets:
                if mkt.get("ticker") == ticker:
                    yes_bid = mkt.get("yes_bid", 0) or 0
                    yes_ask = mkt.get("yes_ask", 0) or 0
                    if yes_bid > 0 and yes_ask > 0:
                        k.yes_price = (yes_bid + yes_ask) / 2.0 / 100.0
                    elif yes_bid > 0:
                        k.yes_price = yes_bid / 100.0
                    elif yes_ask > 0:
                        k.yes_price = yes_ask / 100.0
                    k.no_price = 1.0 - k.yes_price
                    k.volume = float(mkt.get("volume_24h", 0) or 0)
                    k.bid = yes_bid / 100.0 if yes_bid else 0.0
                    k.ask = yes_ask / 100.0 if yes_ask else 0.0
                    return k
        return None


# ============================================================================
# MAIN TRADER
# ============================================================================

class CrossPlatformTrader:
    """Main orchestrator v2 with automated matching engine."""

    def __init__(self):
        self.sig_mgr = SignalManager()
        self.pm_fetcher = PolymarketFetcher()
        self.kalshi_fetcher = KalshiFetcher()
        self.matching_engine = MatchingEngine()
        self.signal_gen = SignalGenerator()
        self.paper_trader = PaperTrader()
        self.state_mgr = StateManager(STATE_FILE)
        self.price_logger = PriceDataLogger(PRICE_LOG)
        self.price_refresher = PriceRefresher()

        self.start_time = time.time()
        self.cycle_count = 0
        self.scan_count = 0
        self.data_points_logged = 0
        self.signals_generated = 0
        self.last_pm_count = 0
        self.last_k_count = 0
        self.last_scan_time = 0.0
        self.active_pairs: Dict[str, MatchedPair] = {}
        self.errors_consecutive = 0

    def scan_and_match(self):
        """Full scan using market_matcher.py v3 engine — multi-category matching."""
        self.scan_count += 1
        scan_start = time.time()

        logger.info("═══════════════════════════════════════════════")
        logger.info(f"🔍 V3 MARKET SCAN #{self.scan_count} — Multi-category matching...")
        logger.info("═══════════════════════════════════════════════")

        try:
            from market_matcher import MatcherEngine, convert_v3_to_legacy_pair

            if not hasattr(self, '_matcher_engine'):
                self._matcher_engine = MatcherEngine()

            v3_pairs = self._matcher_engine.find_all_pairs(force_refresh=True)
            by_cat = self._matcher_engine.get_pairs_by_category()

            # Log category breakdown
            for cat, cat_pairs in sorted(by_cat.items()):
                logger.info(f"    {cat}: {len(cat_pairs)} pairs")

            # Convert V3 pairs to legacy MatchedPair format for compatibility
            old_pair_ids = set(self.active_pairs.keys())
            new_pairs: Dict[str, MatchedPair] = {}

            for v3p in v3_pairs:
                legacy = convert_v3_to_legacy_pair(v3p)

                # Create minimal ParsedMarket objects for PM and Kalshi
                pm_parsed = ParsedMarket(
                    platform="polymarket",
                    market_id=v3p.pm_event_id or "",
                    title=v3p.pm_event_title,
                    event_title=v3p.pm_event_title,
                    category=v3p.category,
                    asset_or_topic=v3p.asset,
                    direction="above",
                    threshold=None,
                    threshold_unit="",
                    settlement_date=None,
                    settlement_time_str="",
                    settlement_source="polymarket",
                    person_or_entity="",
                    yes_price=legacy["pm_yes_price"],
                    no_price=legacy["pm_no_price"],
                    volume=0,
                    bid=legacy["pm_yes_price"],
                    ask=legacy["pm_yes_price"],
                )

                k_parsed = ParsedMarket(
                    platform="kalshi",
                    market_id=v3p.kalshi_event_ticker or "",
                    title=v3p.kalshi_event_ticker or v3p.pair_id,
                    event_title=v3p.kalshi_event_ticker or v3p.pair_id,
                    category=v3p.category,
                    asset_or_topic=v3p.asset,
                    direction="above",
                    threshold=None,
                    threshold_unit="",
                    settlement_date=None,
                    settlement_time_str="",
                    settlement_source="kalshi",
                    person_or_entity="",
                    yes_price=legacy["kalshi_yes_price"],
                    no_price=legacy["kalshi_no_price"],
                    volume=0,
                    bid=legacy["kalshi_bid"],
                    ask=legacy["kalshi_ask"],
                )

                mp = MatchedPair(
                    pair_id=v3p.pair_id,
                    pm_market=pm_parsed,
                    kalshi_market=k_parsed,
                    match_score=v3p.match_quality,
                    match_reasons=[v3p.notes],
                    match_warnings=[],
                    spread=legacy["spread"],
                )
                new_pairs[v3p.pair_id] = mp

            self.active_pairs = new_pairs
            new_pair_ids = set(new_pairs.keys())

            added = new_pair_ids - old_pair_ids
            removed = old_pair_ids - new_pair_ids

            scan_duration = time.time() - scan_start
            self.last_scan_time = time.time()

            logger.info("═══════════════════════════════════════════════")
            logger.info(
                f"📊 V3 SCAN COMPLETE in {scan_duration:.1f}s: "
                f"{len(v3_pairs)} pairs across {len(by_cat)} categories"
            )
            if added:
                logger.info(f"  ➕ New pairs: {added}")
            if removed:
                logger.info(f"  ➖ Removed pairs: {removed}")

            for pid, mp in new_pairs.items():
                logger.info(
                    f"  📌 {pid} (score={mp.match_score}) | "
                    f"PM={mp.pm_market.yes_price:.3f} K={mp.kalshi_market.yes_price:.3f} "
                    f"spread={mp.spread:+.3f}")

            if not v3_pairs:
                logger.info("  ℹ️ No valid pairs found — this is OK!")

            logger.info("═══════════════════════════════════════════════")

        except Exception as e:
            logger.error(f"V3 matcher scan failed: {e}")
            logger.error(traceback.format_exc())
            self.last_scan_time = time.time()  # Don't retry immediately

    def refresh_prices(self):
        """Quick price refresh for existing pairs (no full scan)."""
        for pair_id, mp in list(self.active_pairs.items()):
            try:
                # Refresh PM price
                pm_updated = self.price_refresher.refresh_pm_price(mp.pm_market)
                if pm_updated:
                    mp.pm_market = pm_updated

                # Refresh Kalshi price
                k_updated = self.price_refresher.refresh_kalshi_price(mp.kalshi_market)
                if k_updated:
                    mp.kalshi_market = k_updated

                # Update spread
                mp.spread = mp.pm_market.yes_price - mp.kalshi_market.yes_price
                mp.last_update = time.time()

            except Exception as e:
                logger.debug(f"Price refresh error for {pair_id}: {e}")

    def run_cycle(self):
        """Execute one poll-signal-trade cycle."""
        self.cycle_count += 1
        cycle_start = time.time()

        # Check if we need a full re-scan
        time_since_scan = time.time() - self.last_scan_time
        if self.last_scan_time == 0 or time_since_scan >= RESCAN_INTERVAL:
            self.scan_and_match()
        else:
            # Quick price refresh
            self.refresh_prices()

        if not self.active_pairs:
            if self.cycle_count % 10 == 1:  # Log periodically, not every cycle
                logger.info(
                    f"  Cycle {self.cycle_count}: No active pairs. "
                    f"Next scan in {max(0, RESCAN_INTERVAL - time_since_scan):.0f}s"
                )
            return

        logger.info(f"═══ Cycle {self.cycle_count} ({len(self.active_pairs)} pairs) ═══")

        # Log prices
        for pair_id, mp in self.active_pairs.items():
            self.price_logger.log(pair_id, mp)
            self.data_points_logged += 1

        # Generate signals
        signals = self.signal_gen.generate_signals(self.active_pairs)

        if signals:
            self.signals_generated += len(signals)
            for sig in signals:
                logger.info(
                    f"  🚨 SIGNAL: {sig['type']} | {sig['pair_id']} | "
                    f"direction={sig['direction']} | strength={sig.get('strength', 0):.2f}"
                )

                mp = self.active_pairs.get(sig["pair_id"])
                if mp:
                    # Log signal event
                    self.price_logger.log(sig["pair_id"], mp, signals=[sig])

                    # Paper trade (log category for profitability tracking)
                    self.paper_trader.enter_trade(
                        sig,
                        pm_price=mp.pm_market.yes_price,
                        k_price=mp.kalshi_market.yes_price,
                        spread=mp.spread,
                        pm_title=mp.pm_market.title,
                        k_title=mp.kalshi_market.title,
                        category=mp.pm_market.category,
                    )

        # Check exits
        self.paper_trader.check_exits(self.active_pairs)

        # Summary
        elapsed = time.time() - cycle_start
        summary = self.paper_trader.get_summary()

        stats_str = ""
        for pid, stats in self.signal_gen.spread_stats.items():
            if stats["count"] >= 5:
                stats_str += f" {pid[:20]}:μ={stats['mean']:+.3f}σ={stats['stdev']:.3f}(n={stats['count']})"

        logger.info(
            f"  📊 Cycle {self.cycle_count} done in {elapsed:.1f}s | "
            f"pairs={len(self.active_pairs)} | dp={self.data_points_logged} | "
            f"signals={self.signals_generated} | "
            f"trades={summary['total_trades']}(open={summary['open_trades']}) | "
            f"PnL=${summary['total_pnl']:+.2f}"
        )
        if stats_str:
            logger.info(f"  📈 Spread stats:{stats_str}")

        # Save state
        self.state_mgr.save(self, force=(self.cycle_count % 5 == 0))

        self.errors_consecutive = 0

    def run(self):
        """Main loop."""
        logger.info("=" * 70)
        logger.info("🚀 CROSS-PLATFORM SIGNAL TRADER v2 starting")
        logger.info(f"   Strategy: Automated Structured Matching + PM→Kalshi signals")
        logger.info(f"   Match threshold: {MATCH_SCORE_THRESHOLD}/100")
        logger.info(f"   Poll interval: {POLL_INTERVAL}s")
        logger.info(f"   Rescan interval: {RESCAN_INTERVAL}s ({RESCAN_INTERVAL//60}min)")
        logger.info(f"   PM momentum window: {PM_MOMENTUM_WINDOW}s")
        logger.info(f"   PM move threshold: {PM_MOVE_THRESHOLD}")
        logger.info(f"   Spread entry min: {SPREAD_ENTRY_MIN}")
        logger.info(f"   Max trade size: ${TRADE_MAX_SIZE}")
        logger.info(f"   Max exposure: ${TOTAL_MAX_EXPOSURE}")
        logger.info(f"   Kalshi series tracked: {KALSHI_SERIES_OF_INTEREST}")
        logger.info(f"   JSONL output: {PRICE_LOG}")
        logger.info(f"   State file: {STATE_FILE}")
        logger.info(f"   KEY: 0 matches is OK — better than false matches!")
        logger.info("=" * 70)

        while not self.sig_mgr.shutdown_requested:
            try:
                self.run_cycle()
            except Exception as e:
                self.errors_consecutive += 1
                logger.error(f"Cycle error ({self.errors_consecutive}): {e}")
                logger.error(traceback.format_exc())

                if self.errors_consecutive >= 10:
                    logger.error("10 consecutive errors — pausing 5 minutes")
                    time.sleep(300)
                    self.errors_consecutive = 0

            if not self.sig_mgr.shutdown_requested:
                time.sleep(POLL_INTERVAL)

        # Graceful shutdown
        logger.info("🛑 Shutting down gracefully...")
        self.state_mgr.save(self, force=True)

        summary = self.paper_trader.get_summary()
        logger.info(
            f"📊 FINAL SUMMARY: "
            f"cycles={self.cycle_count} | scans={self.scan_count} | "
            f"data_points={self.data_points_logged} | "
            f"signals={self.signals_generated} | "
            f"trades={summary['total_trades']} | "
            f"PnL=${summary['total_pnl']:+.2f} | "
            f"uptime={((time.time()-self.start_time)/3600):.1f}h"
        )
        logger.info("👋 Cross-platform trader v2 stopped.")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    trader = CrossPlatformTrader()
    trader.run()
