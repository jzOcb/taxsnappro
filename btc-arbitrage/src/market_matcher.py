#!/usr/bin/env python3
"""
Cross-Platform Market Matcher v3
=================================
Modular matching engine for Polymarket ↔ Kalshi overlapping markets.

Categories supported:
  - Weather (daily high temperatures): 5 overlapping cities
  - Crypto (BTC/ETH daily): above/below thresholds
  - NBA games: moneyline matchups
  - Trump mentions/say: weekly word markets
  - Elon tweets: tweet count brackets
  - Fed rate: FOMC decisions
  - CPI: inflation data
  - Rotten Tomatoes: movie scores
  - Soccer/FIFA: World Cup, Premier League
  - Economics (GDP, payrolls, unemployment)

Architecture:
  - Each category has its own matcher class with:
    - identify_pm() — find PM events for this category
    - identify_kalshi() — find Kalshi events for this category
    - match() — produce matched pairs
  - Central MatcherEngine orchestrates all category matchers
  - Caching layer for API responses
  - Deduplication at output level

Usage:
    from market_matcher import MatcherEngine
    engine = MatcherEngine()
    pairs = engine.find_all_pairs()
"""

import json
import re
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple, Any, Set
from collections import defaultdict
from urllib import request as urllib_request
from urllib.parse import urlencode, quote
from urllib.error import URLError, HTTPError
from dataclasses import dataclass, field

logger = logging.getLogger("market-matcher")

# ============================================================================
# API ENDPOINTS
# ============================================================================
PM_GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
PM_GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_EVENTS = f"{KALSHI_API_BASE}/events"
KALSHI_MARKETS = f"{KALSHI_API_BASE}/markets"

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MatchedPairV3:
    """A matched pair across platforms."""
    pair_id: str
    category: str
    asset: str
    date: str  # YYYY-MM-DD or YYYY-MM or "weekly:YYYY-MM-DD"
    pm_event_id: str
    pm_event_title: str
    pm_event_slug: str
    pm_tokens: List[Dict]  # [{token_id, question, outcome, yes_price, no_price}, ...]
    kalshi_event_ticker: str
    kalshi_series_ticker: str
    kalshi_markets: List[Dict]  # [{ticker, title, yes_price, no_price, yes_bid, yes_ask}, ...]
    match_quality: int  # 0-100
    notes: str = ""
    last_update: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "pair_id": self.pair_id,
            "category": self.category,
            "asset": self.asset,
            "date": self.date,
            "pm_event_id": self.pm_event_id,
            "pm_event_title": self.pm_event_title,
            "pm_event_slug": self.pm_event_slug,
            "pm_tokens": self.pm_tokens,
            "kalshi_event_ticker": self.kalshi_event_ticker,
            "kalshi_series_ticker": self.kalshi_series_ticker,
            "kalshi_markets": self.kalshi_markets,
            "match_quality": self.match_quality,
            "notes": self.notes,
            "last_update": self.last_update,
        }


# ============================================================================
# HTTP / CACHING LAYER
# ============================================================================

class APICache:
    """Simple TTL cache for API responses."""

    def __init__(self, default_ttl: int = 120):
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self.default_ttl = default_ttl
        self.stats = {"hits": 0, "misses": 0, "errors": 0}
        self._last_request_time = 0.0
        self._min_delay = 0.35  # seconds between API calls

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_delay:
            time.sleep(self._min_delay - elapsed)
        self._last_request_time = time.time()

    def get(self, url: str, params: Dict = None, ttl: int = None, timeout: int = 15) -> Optional[Any]:
        """Fetch URL with caching."""
        cache_key = url
        if params:
            cache_key += "?" + urlencode({k: v for k, v in sorted(params.items()) if v is not None})

        # Check cache
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if time.time() - ts < (ttl or self.default_ttl):
                self.stats["hits"] += 1
                return data

        # Fetch
        self._rate_limit()
        self.stats["misses"] += 1

        try:
            full_url = url
            if params:
                query = urlencode({k: v for k, v in params.items() if v is not None})
                full_url = f"{url}?{query}"

            req = urllib_request.Request(full_url, headers={
                "User-Agent": "MarketMatcher/3.0",
                "Accept": "application/json",
            })
            with urllib_request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            self._cache[cache_key] = (time.time(), data)
            return data
        except HTTPError as e:
            if e.code == 429:
                logger.warning(f"Rate limited on {url}, backing off...")
                time.sleep(2)
                self.stats["errors"] += 1
            else:
                logger.debug(f"HTTP {e.code} for {url}")
                self.stats["errors"] += 1
            return None
        except Exception as e:
            logger.debug(f"Request error for {url}: {e}")
            self.stats["errors"] += 1
            return None

    def invalidate(self, pattern: str = None):
        """Clear cache, optionally matching a pattern."""
        if pattern:
            keys_to_del = [k for k in self._cache if pattern in k]
            for k in keys_to_del:
                del self._cache[k]
        else:
            self._cache.clear()


# Global cache instance
_api_cache = APICache(default_ttl=120)


def get_api_cache() -> APICache:
    return _api_cache


# ============================================================================
# POLYMARKET HELPERS
# ============================================================================

def pm_fetch_events_paginated(cache: APICache, max_pages: int = 5) -> List[Dict]:
    """Fetch all active PM events (paginated by volume)."""
    all_events = []
    seen_ids = set()
    for offset in range(0, max_pages * 100, 100):
        data = cache.get(PM_GAMMA_EVENTS, {
            "active": "true",
            "closed": "false",
            "limit": "100",
            "offset": str(offset),
            "order": "volume24hr",
            "ascending": "false",
        }, ttl=180)
        if not data or not isinstance(data, list) or len(data) == 0:
            break
        for evt in data:
            eid = evt.get("id", "")
            if eid not in seen_ids:
                seen_ids.add(eid)
                all_events.append(evt)
        if len(data) < 100:
            break
    return all_events


def pm_fetch_event_by_slug(cache: APICache, slug: str) -> Optional[Dict]:
    """Fetch a single PM event by slug."""
    data = cache.get(PM_GAMMA_EVENTS, {"slug": slug}, ttl=300)
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    return None


def pm_parse_token_prices(market: Dict) -> Tuple[float, float]:
    """Parse yes/no prices from PM market."""
    prices_raw = market.get("outcomePrices", "[]")
    if isinstance(prices_raw, str):
        try:
            prices = json.loads(prices_raw)
        except:
            return 0.0, 0.0
    else:
        prices = prices_raw
    yes_price = float(prices[0]) if len(prices) > 0 else 0.0
    no_price = float(prices[1]) if len(prices) > 1 else 1.0 - yes_price
    return yes_price, no_price


# ============================================================================
# KALSHI HELPERS
# ============================================================================

def kalshi_fetch_events_for_series(cache: APICache, series: str, limit: int = 20) -> List[Dict]:
    """Fetch open events for a Kalshi series."""
    data = cache.get(KALSHI_EVENTS, {
        "status": "open",
        "limit": str(limit),
        "series_ticker": series,
    }, ttl=180)
    if data and isinstance(data, dict):
        return data.get("events", [])
    return []


def kalshi_fetch_markets_for_event(cache: APICache, event_ticker: str, limit: int = 200) -> List[Dict]:
    """Fetch open markets for a Kalshi event."""
    data = cache.get(KALSHI_MARKETS, {
        "status": "open",
        "limit": str(limit),
        "event_ticker": event_ticker,
    }, ttl=120)
    if data and isinstance(data, dict):
        return data.get("markets", [])
    return []


def kalshi_parse_prices(market: Dict) -> Tuple[float, float, float, float]:
    """Parse yes_price, no_price, bid, ask from Kalshi market (cents → dollars)."""
    yes_bid = (market.get("yes_bid") or 0)
    yes_ask = (market.get("yes_ask") or 0)
    if yes_bid > 0 and yes_ask > 0:
        yes_price = (yes_bid + yes_ask) / 2.0 / 100.0
    elif yes_bid > 0:
        yes_price = yes_bid / 100.0
    elif yes_ask > 0:
        yes_price = yes_ask / 100.0
    else:
        yes_price = 0.0
    no_price = 1.0 - yes_price
    return yes_price, no_price, yes_bid / 100.0, yes_ask / 100.0


# ============================================================================
# DATE HELPERS
# ============================================================================

MONTHS = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}


def parse_date_from_slug(slug: str) -> Optional[str]:
    """Extract date from PM slug like 'bitcoin-above-on-february-5' → '2026-02-05'."""
    for month_name, month_num in MONTHS.items():
        # slug pattern: ...-{month}-{day}... or ...-{month}-{day}-{year}
        pattern = rf'{month_name}-(\d{{1,2}})(?:-(\d{{4}}))?'
        m = re.search(pattern, slug, re.IGNORECASE)
        if m:
            day = int(m.group(1))
            year = int(m.group(2)) if m.group(2) else datetime.now().year
            try:
                return f"{year:04d}-{month_num:02d}-{day:02d}"
            except:
                continue
    return None


def parse_date_from_text(text: str) -> Optional[str]:
    """Extract date from text like 'February 5' or 'Feb 6, 2026'."""
    text_lower = text.lower()
    for month_name, month_num in MONTHS.items():
        pattern = rf'{month_name}\s+(\d{{1,2}})(?:\s*,?\s*(\d{{4}}))?'
        m = re.search(pattern, text_lower, re.IGNORECASE)
        if m:
            day = int(m.group(1))
            year = int(m.group(2)) if m.group(2) else datetime.now().year
            try:
                return f"{year:04d}-{month_num:02d}-{day:02d}"
            except:
                continue
    return None


def parse_date_from_kalshi_ticker(ticker: str) -> Optional[str]:
    """Extract date from Kalshi event ticker like 'KXBTCD-26FEB0517' → '2026-02-05'."""
    # Pattern: XX{YYMMMDD}... e.g. KXHIGHNY-26FEB06 or KXBTCD-26FEB0517
    m = re.search(r'-(\d{2})([A-Z]{3})(\d{2})', ticker)
    if m:
        year = 2000 + int(m.group(1))
        month_abbr = m.group(2).lower()
        day = int(m.group(3))
        month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                     'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
        month_num = month_map.get(month_abbr)
        if month_num:
            try:
                return f"{year:04d}-{month_num:02d}-{day:02d}"
            except:
                pass
    return None


def parse_month_from_kalshi_ticker(ticker: str) -> Optional[str]:
    """Extract month from Kalshi ticker like 'KXCPI-26FEB' → '2026-02'."""
    m = re.search(r'-(\d{2})([A-Z]{3})$', ticker)
    if m:
        year = 2000 + int(m.group(1))
        month_abbr = m.group(2).lower()
        month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                     'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
        month_num = month_map.get(month_abbr)
        if month_num:
            return f"{year:04d}-{month_num:02d}"
    return None


def extract_week_end_date(text: str) -> Optional[str]:
    """Extract week-ending date from 'this week (February 8)' → '2026-02-08'."""
    return parse_date_from_text(text)


# ============================================================================
# CATEGORY MATCHERS
# ============================================================================

class BaseMatcher:
    """Base class for category matchers."""

    category: str = ""

    def find_pairs(self, cache: APICache, pm_events: List[Dict]) -> List[MatchedPairV3]:
        raise NotImplementedError


class WeatherMatcher(BaseMatcher):
    """Match weather (daily high temperature) markets.

    PM: Events with slug pattern 'highest-temperature-in-{city}-on-{month}-{day}-{year}'
        Each event has 7 bracket markets (e.g. "23°F or below", "24-25°F", etc.)
    Kalshi: Series KXHIGHNY, KXHIGHMIA, KXHIGHCHI, KXHIGHTSEA, KXHIGHTATL
        Each event has ~6 binary markets (above X°, below X°, between X-Y°)
    """

    category = "weather"

    # PM city name in slug → Kalshi series ticker
    CITY_MAP = {
        "nyc": "KXHIGHNY",
        "miami": "KXHIGHMIA",
        "chicago": "KXHIGHCHI",
        "seattle": "KXHIGHTSEA",
        "atlanta": "KXHIGHTATL",
    }

    # Kalshi series → PM city slug
    SERIES_TO_CITY = {v: k for k, v in CITY_MAP.items()}

    # City display names
    CITY_DISPLAY = {
        "nyc": "NYC", "miami": "Miami", "chicago": "Chicago",
        "seattle": "Seattle", "atlanta": "Atlanta",
    }

    def find_pairs(self, cache: APICache, pm_events: List[Dict]) -> List[MatchedPairV3]:
        pairs = []
        now = time.time()

        # Step 1: Collect PM weather events from the pre-fetched events list
        pm_weather = {}  # key: (city, date) → event
        for evt in pm_events:
            slug = evt.get("slug", "").lower()
            if not slug.startswith("highest-temperature-in-"):
                continue
            # Parse city and date from slug
            city, date_str = self._parse_pm_weather_slug(slug)
            if city and date_str and city in self.CITY_MAP:
                pm_weather[(city, date_str)] = evt

        # Step 2: Also proactively fetch PM weather for known cities & upcoming dates
        today = datetime.now(timezone.utc).date()
        for city_slug in self.CITY_MAP:
            for delta in range(0, 3):  # today, tomorrow, day after
                d = today + timedelta(days=delta)
                date_str = d.strftime("%Y-%m-%d")
                month_name = d.strftime("%B").lower()
                day_num = d.day
                pm_slug = f"highest-temperature-in-{city_slug}-on-{month_name}-{day_num}-{d.year}"

                if (city_slug, date_str) in pm_weather:
                    continue  # Already found

                evt = pm_fetch_event_by_slug(cache, pm_slug)
                if evt:
                    pm_weather[(city_slug, date_str)] = evt

        logger.info(f"  Weather: Found {len(pm_weather)} PM weather events")

        # Step 3: Fetch Kalshi weather events
        kalshi_weather = {}  # key: (city, date) → (event, markets)
        for series, city_slug in self.SERIES_TO_CITY.items():
            events = kalshi_fetch_events_for_series(cache, series, limit=5)
            for evt in events:
                ticker = evt.get("event_ticker", "")
                date_str = parse_date_from_kalshi_ticker(ticker)
                if date_str:
                    markets = kalshi_fetch_markets_for_event(cache, ticker)
                    if markets:
                        kalshi_weather[(city_slug, date_str)] = (evt, markets)

        logger.info(f"  Weather: Found {len(kalshi_weather)} Kalshi weather events")

        # Step 4: Match PM ↔ Kalshi by (city, date) — strict same-date
        common_keys = set(pm_weather.keys()) & set(kalshi_weather.keys())
        for key in common_keys:
            city_slug, date_str = key
            pm_evt = pm_weather[key]
            k_evt, k_markets = kalshi_weather[key]

            # Build PM tokens
            pm_tokens = []
            for mkt in pm_evt.get("markets", []):
                yes_p, no_p = pm_parse_token_prices(mkt)
                pm_tokens.append({
                    "token_id": mkt.get("conditionId", mkt.get("id", "")),
                    "question": mkt.get("question", ""),
                    "outcomes": mkt.get("outcomes", []),
                    "yes_price": yes_p,
                    "no_price": no_p,
                })

            # Build Kalshi markets
            k_market_list = []
            for mkt in k_markets:
                yp, np, yb, ya = kalshi_parse_prices(mkt)
                k_market_list.append({
                    "ticker": mkt.get("ticker", ""),
                    "title": mkt.get("title", ""),
                    "subtitle": mkt.get("subtitle", ""),
                    "yes_price": yp,
                    "no_price": np,
                    "yes_bid": yb,
                    "yes_ask": ya,
                    "floor_strike": mkt.get("floor_strike"),
                    "cap_strike": mkt.get("cap_strike"),
                    "strike_type": mkt.get("strike_type", ""),
                })

            city_display = self.CITY_DISPLAY.get(city_slug, city_slug.upper())
            pair = MatchedPairV3(
                pair_id=f"weather:{city_display}:{date_str}",
                category="weather",
                asset=city_display,
                date=date_str,
                pm_event_id=pm_evt.get("id", ""),
                pm_event_title=pm_evt.get("title", ""),
                pm_event_slug=pm_evt.get("slug", ""),
                pm_tokens=pm_tokens,
                kalshi_event_ticker=k_evt.get("event_ticker", ""),
                kalshi_series_ticker=self.CITY_MAP.get(city_slug, ""),
                kalshi_markets=k_market_list,
                match_quality=95,
                notes=f"PM={len(pm_tokens)}-bracket, K={len(k_market_list)} binary. Same city+date.",
                last_update=now,
            )
            pairs.append(pair)

        return pairs

    def _parse_pm_weather_slug(self, slug: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse 'highest-temperature-in-{city}-on-{month}-{day}-{year}' slug."""
        # Remove the prefix
        rest = slug.replace("highest-temperature-in-", "")
        # Split on '-on-'
        parts = rest.split("-on-")
        if len(parts) != 2:
            return None, None
        city = parts[0].strip("-")
        date_part = parts[1]
        date_str = parse_date_from_slug(date_part)
        return city, date_str


class CryptoMatcher(BaseMatcher):
    """Match crypto daily price markets (BTC, ETH).

    PM: Events like 'Bitcoin above ___ on February 5?' with 11 threshold markets
    Kalshi: Series KXBTCD, KXETHD with binary above/below markets
    """

    category = "crypto"

    ASSETS = {
        "BTC": {
            "pm_slug_patterns": ["bitcoin-above-on-", "bitcoin-price-on-"],
            "pm_title_patterns": ["bitcoin above", "bitcoin price on", "price of bitcoin"],
            "kalshi_series": ["KXBTCD"],
        },
        "ETH": {
            "pm_slug_patterns": ["ethereum-above-on-", "ethereum-price-on-"],
            "pm_title_patterns": ["ethereum above", "ethereum price on", "price of ethereum"],
            "kalshi_series": ["KXETHD"],
        },
    }

    def find_pairs(self, cache: APICache, pm_events: List[Dict]) -> List[MatchedPairV3]:
        pairs = []
        now = time.time()

        for asset, config in self.ASSETS.items():
            # Find PM events for this asset
            pm_daily = {}  # date → event
            for evt in pm_events:
                slug = evt.get("slug", "").lower()
                title = evt.get("title", "").lower()

                matched = False
                for pat in config["pm_slug_patterns"]:
                    if pat in slug:
                        matched = True
                        break
                if not matched:
                    for pat in config["pm_title_patterns"]:
                        if pat in title:
                            matched = True
                            break
                if not matched:
                    continue

                # Extract date
                date_str = parse_date_from_slug(slug)
                if not date_str:
                    date_str = parse_date_from_text(evt.get("title", ""))
                if date_str:
                    # Prefer "above" events over "price" events (above has direct comparisons)
                    if "above" in slug or date_str not in pm_daily:
                        pm_daily[date_str] = evt

            # Find Kalshi events for this asset
            kalshi_daily = {}  # date → (event, markets)
            for series in config["kalshi_series"]:
                events = kalshi_fetch_events_for_series(cache, series, limit=10)
                for evt in events:
                    ticker = evt.get("event_ticker", "")
                    date_str = parse_date_from_kalshi_ticker(ticker)
                    if date_str:
                        markets = kalshi_fetch_markets_for_event(cache, ticker)
                        if markets:
                            # Note: Kalshi may have 12pm and 5pm events for same date
                            # The ticker distinguishes them: KXBTCD-26FEB0512 vs KXBTCD-26FEB0517
                            # Store by date+time to avoid clobbering
                            time_suffix = ""
                            m = re.search(r'(\d{2})$', ticker)
                            if m:
                                time_suffix = m.group(1)
                            key = f"{date_str}:{time_suffix}" if time_suffix else date_str
                            kalshi_daily[key] = (evt, markets)

            logger.info(f"  Crypto {asset}: {len(pm_daily)} PM dates, {len(kalshi_daily)} Kalshi events")

            # Match by date — strict same-date
            for pm_date, pm_evt in pm_daily.items():
                # Find best Kalshi match for this date
                best_k = None
                best_k_key = None
                for k_key, (k_evt, k_mkts) in kalshi_daily.items():
                    k_date = k_key.split(":")[0]
                    if k_date == pm_date:
                        if best_k is None:
                            best_k = (k_evt, k_mkts)
                            best_k_key = k_key

                if not best_k:
                    continue

                k_evt, k_markets = best_k

                # Build PM tokens (deduplicate: one entry per threshold)
                pm_tokens = []
                seen_questions = set()
                for mkt in pm_evt.get("markets", []):
                    q = mkt.get("question", "")
                    if q in seen_questions:
                        continue
                    seen_questions.add(q)
                    yes_p, no_p = pm_parse_token_prices(mkt)
                    threshold = self._extract_threshold(q)
                    pm_tokens.append({
                        "token_id": mkt.get("conditionId", mkt.get("id", "")),
                        "question": q,
                        "threshold": threshold,
                        "yes_price": yes_p,
                        "no_price": no_p,
                    })

                # Build Kalshi markets
                k_market_list = []
                for mkt in k_markets:
                    yp, np, yb, ya = kalshi_parse_prices(mkt)
                    k_market_list.append({
                        "ticker": mkt.get("ticker", ""),
                        "title": mkt.get("title", ""),
                        "subtitle": mkt.get("subtitle", ""),
                        "yes_price": yp,
                        "no_price": np,
                        "yes_bid": yb,
                        "yes_ask": ya,
                        "floor_strike": mkt.get("floor_strike"),
                        "cap_strike": mkt.get("cap_strike"),
                        "strike_type": mkt.get("strike_type", ""),
                    })

                # Determine resolution time difference
                k_title = k_evt.get("title", "")
                pm_desc = ""
                for mkt in pm_evt.get("markets", []):
                    pm_desc = mkt.get("description", "")
                    if pm_desc:
                        break

                time_note = ""
                if "noon" in pm_desc.lower() or "12:00" in pm_desc.lower():
                    time_note = "PM=noon ET"
                if "5pm" in k_title.lower() or "5pm" in k_title:
                    time_note += (", " if time_note else "") + "K=5pm EST"
                elif "12pm" in k_title.lower():
                    time_note += (", " if time_note else "") + "K=12pm EST"

                quality = 90
                if "noon" in pm_desc.lower() and "12pm" in k_title.lower():
                    quality = 95  # Same resolution time

                pair = MatchedPairV3(
                    pair_id=f"crypto:{asset}:{pm_date}",
                    category="crypto",
                    asset=asset,
                    date=pm_date,
                    pm_event_id=pm_evt.get("id", ""),
                    pm_event_title=pm_evt.get("title", ""),
                    pm_event_slug=pm_evt.get("slug", ""),
                    pm_tokens=pm_tokens,
                    kalshi_event_ticker=k_evt.get("event_ticker", ""),
                    kalshi_series_ticker=config["kalshi_series"][0],
                    kalshi_markets=k_market_list,
                    match_quality=quality,
                    notes=f"PM={len(pm_tokens)} thresholds, K={len(k_market_list)} markets. {time_note}",
                    last_update=now,
                )
                pairs.append(pair)

        return pairs

    @staticmethod
    def _extract_threshold(question: str) -> Optional[float]:
        m = re.search(r'\$([0-9,]+(?:\.\d+)?)', question)
        if m:
            return float(m.group(1).replace(',', ''))
        return None


class NBAMatcher(BaseMatcher):
    """Match NBA game markets.

    PM: Events with slug pattern 'nba-{away}-{home}-{date}'
        Single market per event, outcomes = [Team1, Team2]
    Kalshi: Series KXNBAGAME, events like KXNBAGAME-26FEB05CHAHOU
        Two markets per event (one per team winner)
    """

    category = "nba"

    # Kalshi team abbr → PM slug abbr (lowercase)
    # Kalshi uses: ATL, BOS, BKN, CHA, CHI, CLE, DAL, DEN, DET, GSW, HOU, IND,
    #              LAC, LAL, MEM, MIA, MIL, MIN, NOP, NYK, OKC, ORL, PHI, PHX,
    #              POR, SAC, SAS, TOR, UTA, WAS
    # PM slugs use lowercase 3-letter codes
    KALSHI_TO_PM = {
        "ATL": "atl", "BOS": "bos", "BKN": "bkn", "CHA": "cha",
        "CHI": "chi", "CLE": "cle", "DAL": "dal", "DEN": "den",
        "DET": "det", "GSW": "gsw", "HOU": "hou", "IND": "ind",
        "LAC": "lac", "LAL": "lal", "MEM": "mem", "MIA": "mia",
        "MIL": "mil", "MIN": "min", "NOP": "nop", "NYK": "nyk",
        "OKC": "okc", "ORL": "orl", "PHI": "phi", "PHX": "phx",
        "POR": "por", "SAC": "sac", "SAS": "sas", "TOR": "tor",
        "UTA": "uta", "WAS": "was",
    }

    # PM slug → Kalshi abbr
    PM_TO_KALSHI = {v: k for k, v in KALSHI_TO_PM.items()}

    def find_pairs(self, cache: APICache, pm_events: List[Dict]) -> List[MatchedPairV3]:
        pairs = []
        now = time.time()

        # Step 1: Find PM NBA game events
        pm_games = {}  # key: (away_pm, home_pm, date) → event
        for evt in pm_events:
            slug = evt.get("slug", "").lower()
            if not slug.startswith("nba-"):
                continue
            # Parse: nba-{away}-{home}-{YYYY}-{MM}-{DD}
            m = re.match(r'nba-([a-z]+)-([a-z]+)-(\d{4})-(\d{2})-(\d{2})', slug)
            if m:
                away = m.group(1)
                home = m.group(2)
                date_str = f"{m.group(3)}-{m.group(4)}-{m.group(5)}"
                pm_games[(away, home, date_str)] = evt

        # Step 2: Fetch Kalshi NBA game events
        kalshi_games = {}  # key: (away_kalshi, home_kalshi, date) → (event, markets)
        events = kalshi_fetch_events_for_series(cache, "KXNBAGAME", limit=30)
        for evt in events:
            ticker = evt.get("event_ticker", "")
            # Parse: KXNBAGAME-26FEB05CHAHOU
            m = re.match(r'KXNBAGAME-(\d{2})([A-Z]{3})(\d{2})([A-Z]+)([A-Z]{3})$', ticker)
            if m:
                year = 2000 + int(m.group(1))
                month_abbr = m.group(2).lower()
                day = int(m.group(3))
                month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                             'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                month_num = month_map.get(month_abbr)
                if not month_num:
                    continue

                # The team codes in the ticker: chars after the day digits
                teams_str = m.group(4) + m.group(5)
                # Need to split into away + home. Kalshi uses 3-letter codes
                # but the regex captured them as 4th+5th groups. Let me re-parse
                pass

            # Better parsing: after the date, remaining chars are team codes
            m2 = re.match(r'KXNBAGAME-\d{2}[A-Z]{3}\d{2}(.+)', ticker)
            if m2:
                teams_part = m2.group(1)
                date_str = parse_date_from_kalshi_ticker(ticker)
                if not date_str:
                    continue

                # Team codes are 3 letters each, concatenated: CHAHOU = CHA + HOU
                if len(teams_part) == 6:
                    away_k = teams_part[:3]
                    home_k = teams_part[3:]
                elif len(teams_part) == 7:
                    # Handle irregular codes (e.g. "LACSAC" is LAC+SAC)
                    # Try 3+4 and 4+3
                    if teams_part[:3] in self.KALSHI_TO_PM:
                        away_k = teams_part[:3]
                        home_k = teams_part[3:]
                    elif teams_part[:4] in self.KALSHI_TO_PM:
                        away_k = teams_part[:4]
                        home_k = teams_part[4:]
                    else:
                        continue
                else:
                    continue

                markets = kalshi_fetch_markets_for_event(cache, ticker)
                if markets:
                    kalshi_games[(away_k, home_k, date_str)] = (evt, markets)

        logger.info(f"  NBA: {len(pm_games)} PM games, {len(kalshi_games)} Kalshi games")

        # Step 3: Match by team pair + date
        for (away_k, home_k, k_date), (k_evt, k_markets) in kalshi_games.items():
            # Convert Kalshi team codes to PM codes
            away_pm = self.KALSHI_TO_PM.get(away_k, away_k.lower())
            home_pm = self.KALSHI_TO_PM.get(home_k, home_k.lower())

            # Look for PM match (away_pm, home_pm, date) — PM uses same away/home convention
            pm_evt = pm_games.get((away_pm, home_pm, k_date))
            if not pm_evt:
                # Try reversed (sometimes PM might list differently)
                pm_evt = pm_games.get((home_pm, away_pm, k_date))

            if not pm_evt:
                continue

            # Build PM tokens — filter to MONEYLINE only (exclude spread, O/U, props)
            pm_tokens = []
            for mkt in pm_evt.get("markets", []):
                q = mkt.get("question", "").lower()
                # Skip spread, over/under, half-time, prop markets
                if any(k in q for k in ['spread', 'o/u', 'over/under',
                                          '1h ', '1q ', '2h ', '3q ', '4q ',
                                          'points', 'rebounds', 'assists',
                                          'three', '3-pointer', 'total']):
                    continue
                # Keep the main moneyline market
                yes_p, no_p = pm_parse_token_prices(mkt)
                outcomes = mkt.get("outcomes", [])
                pm_tokens.append({
                    "token_id": mkt.get("conditionId", mkt.get("id", "")),
                    "question": mkt.get("question", ""),
                    "outcomes": outcomes,
                    "yes_price": yes_p,
                    "no_price": no_p,
                })

            if not pm_tokens:
                continue  # No moneyline market found

            # Build Kalshi markets
            k_market_list = []
            for mkt in k_markets:
                yp, np, yb, ya = kalshi_parse_prices(mkt)
                k_market_list.append({
                    "ticker": mkt.get("ticker", ""),
                    "title": mkt.get("title", ""),
                    "yes_sub_title": mkt.get("yes_sub_title", ""),
                    "no_sub_title": mkt.get("no_sub_title", ""),
                    "yes_price": yp,
                    "no_price": np,
                    "yes_bid": yb,
                    "yes_ask": ya,
                })

            game_label = f"{away_k}@{home_k}"
            pair = MatchedPairV3(
                pair_id=f"nba:{game_label}:{k_date}",
                category="nba",
                asset=game_label,
                date=k_date,
                pm_event_id=pm_evt.get("id", ""),
                pm_event_title=pm_evt.get("title", ""),
                pm_event_slug=pm_evt.get("slug", ""),
                pm_tokens=pm_tokens,
                kalshi_event_ticker=k_evt.get("event_ticker", ""),
                kalshi_series_ticker="KXNBAGAME",
                kalshi_markets=k_market_list,
                match_quality=92,
                notes=f"PM=moneyline, K=moneyline. {pm_evt.get('title', '')}",
                last_update=now,
            )
            pairs.append(pair)

        return pairs


class TrumpMentionMatcher(BaseMatcher):
    """Match Trump 'say' / mention markets.

    PM: Events like 'What will Trump say this week (February 8)?'
        Multiple word/phrase markets within one event
    Kalshi: Series KXTRUMPSAY with weekly events like KXTRUMPSAY-26FEB09
        Each market is a word/phrase
    """

    category = "trump_mentions"

    def find_pairs(self, cache: APICache, pm_events: List[Dict]) -> List[MatchedPairV3]:
        pairs = []
        now = time.time()

        # Find PM Trump say events
        pm_trump = {}  # week_end_date → event
        for evt in pm_events:
            slug = evt.get("slug", "").lower()
            title = evt.get("title", "").lower()
            if "trump" in title and ("say" in title or "mention" in title) and "week" in title:
                # Extract week-ending date from title
                week_date = extract_week_end_date(evt.get("title", ""))
                if week_date:
                    pm_trump[week_date] = evt

        # Find Kalshi Trump say events
        kalshi_trump = {}  # date → (event, markets)
        for series in ["KXTRUMPSAY"]:
            events = kalshi_fetch_events_for_series(cache, series, limit=5)
            for evt in events:
                ticker = evt.get("event_ticker", "")
                date_str = parse_date_from_kalshi_ticker(ticker)
                if date_str:
                    markets = kalshi_fetch_markets_for_event(cache, ticker, limit=100)
                    if markets:
                        kalshi_trump[date_str] = (evt, markets)

        logger.info(f"  Trump mentions: {len(pm_trump)} PM events, {len(kalshi_trump)} Kalshi events")

        # Match: PM week-end date should match Kalshi date (both use week-ending)
        # Kalshi: KXTRUMPSAY-26FEB09 = "before Feb 9"
        # PM: "this week (February 8)" - week ending Feb 8
        # Allow ±1 day matching for week boundaries
        for pm_date, pm_evt in pm_trump.items():
            for k_date, (k_evt, k_markets) in kalshi_trump.items():
                pm_d = datetime.strptime(pm_date, "%Y-%m-%d").date()
                k_d = datetime.strptime(k_date, "%Y-%m-%d").date()
                if abs((pm_d - k_d).days) <= 1:
                    # Match! Build the pair
                    pm_tokens = []
                    for mkt in pm_evt.get("markets", []):
                        yes_p, no_p = pm_parse_token_prices(mkt)
                        pm_tokens.append({
                            "token_id": mkt.get("conditionId", mkt.get("id", "")),
                            "question": mkt.get("question", ""),
                            "yes_price": yes_p,
                            "no_price": no_p,
                        })

                    k_market_list = []
                    for mkt in k_markets:
                        yp, np, yb, ya = kalshi_parse_prices(mkt)
                        k_market_list.append({
                            "ticker": mkt.get("ticker", ""),
                            "title": mkt.get("title", ""),
                            "yes_price": yp,
                            "no_price": np,
                            "yes_bid": yb,
                            "yes_ask": ya,
                        })

                    # Try to find word-level matches between PM and Kalshi
                    word_matches = self._find_word_matches(pm_tokens, k_market_list)

                    pair = MatchedPairV3(
                        pair_id=f"trump_say:weekly:{pm_date}",
                        category="trump_mentions",
                        asset="trump_say",
                        date=f"weekly:{pm_date}",
                        pm_event_id=pm_evt.get("id", ""),
                        pm_event_title=pm_evt.get("title", ""),
                        pm_event_slug=pm_evt.get("slug", ""),
                        pm_tokens=pm_tokens,
                        kalshi_event_ticker=k_evt.get("event_ticker", ""),
                        kalshi_series_ticker="KXTRUMPSAY",
                        kalshi_markets=k_market_list,
                        match_quality=88,
                        notes=f"PM={len(pm_tokens)} words, K={len(k_market_list)} words. "
                              f"{len(word_matches)} exact word matches.",
                        last_update=now,
                    )
                    pairs.append(pair)

        return pairs

    @staticmethod
    def _find_word_matches(pm_tokens: List[Dict], k_markets: List[Dict]) -> List[Tuple[str, str]]:
        """Find matching word/phrase markets between PM and Kalshi."""
        matches = []
        for pm_tok in pm_tokens:
            pm_words = TrumpMentionMatcher._extract_words(pm_tok.get("question", ""))
            for k_mkt in k_markets:
                k_words = TrumpMentionMatcher._extract_words(k_mkt.get("title", ""))
                if pm_words and k_words and pm_words & k_words:
                    matches.append((pm_tok.get("question", "")[:50], k_mkt.get("title", "")[:50]))
                    break
        return matches

    @staticmethod
    def _extract_words(text: str) -> Set[str]:
        """Extract the key word/phrase being bet on from a question."""
        text = text.lower()
        # PM: 'Will Trump say "MAGA" or "Make America Great Again" this week?'
        # Kalshi: 'Will Trump say "Thug" before Feb 9, 2026?'
        words = set()
        for m in re.finditer(r'"([^"]+)"', text):
            words.add(m.group(1).lower().strip())
        return words


class ElonTweetsMatcher(BaseMatcher):
    """Match Elon Musk tweet count markets.

    PM: Events like 'Elon Musk # tweets February 3 - February 10, 2026?'
        Multiple bracket markets (0-19, 20-39, etc.)
    Kalshi: If KXELONTWEET series exists (may not always)
    """

    category = "elon_tweets"

    def find_pairs(self, cache: APICache, pm_events: List[Dict]) -> List[MatchedPairV3]:
        pairs = []
        now = time.time()

        # Find PM Elon tweet events
        pm_elon = {}  # (start_date, end_date) → event
        for evt in pm_events:
            slug = evt.get("slug", "").lower()
            title = evt.get("title", "").lower()
            if "elon" in title and "tweet" in title:
                # Parse date range from title
                dates = self._parse_date_range(evt.get("title", ""))
                if dates:
                    pm_elon[dates] = evt

        # Check Kalshi for Elon tweet series
        kalshi_elon = {}
        for series in ["KXELONTWEET", "KXELONTWEETS", "KXELON"]:
            events = kalshi_fetch_events_for_series(cache, series, limit=5)
            for evt in events:
                ticker = evt.get("event_ticker", "")
                date_str = parse_date_from_kalshi_ticker(ticker)
                if date_str:
                    markets = kalshi_fetch_markets_for_event(cache, ticker)
                    if markets:
                        kalshi_elon[date_str] = (evt, markets)

        logger.info(f"  Elon tweets: {len(pm_elon)} PM events, {len(kalshi_elon)} Kalshi events")

        # If Kalshi has matching events, create pairs
        # (Kalshi may not have Elon tweet markets currently)
        if not kalshi_elon and pm_elon:
            logger.info(f"  Elon tweets: PM has events but no Kalshi match found")

        return pairs

    @staticmethod
    def _parse_date_range(title: str) -> Optional[Tuple[str, str]]:
        """Parse date range from 'Elon Musk # tweets February 3 - February 10, 2026?'"""
        # Find all dates in the title
        dates = []
        title_lower = title.lower()
        for month_name, month_num in MONTHS.items():
            for m in re.finditer(rf'{month_name}\s+(\d{{1,2}})(?:\s*,?\s*(\d{{4}}))?', title_lower):
                day = int(m.group(1))
                year = int(m.group(2)) if m.group(2) else datetime.now().year
                try:
                    dates.append(f"{year:04d}-{month_num:02d}-{day:02d}")
                except:
                    pass
        if len(dates) >= 2:
            return (dates[0], dates[1])
        return None


class FedRateMatcher(BaseMatcher):
    """Match Fed rate / FOMC decision markets.

    PM: Events about Fed rate cuts/hikes, FOMC decisions
    Kalshi: Series KXFEDDECISION (monthly FOMC meetings)
    """

    category = "fed_rate"

    def find_pairs(self, cache: APICache, pm_events: List[Dict]) -> List[MatchedPairV3]:
        pairs = []
        now = time.time()

        # Find PM Fed rate events — separate monthly decisions from annual counts
        pm_fed_monthly = {}  # month_key → event (e.g. "Fed Decision in June?")
        pm_fed_annual = {}   # year → event (e.g. "How many Fed rate cuts in 2026?")
        for evt in pm_events:
            title = evt.get("title", "").lower()
            slug = evt.get("slug", "").lower()
            if not any(k in title for k in ['fed rate', 'federal reserve', 'fomc',
                                             'rate cut', 'rate hike', 'fed decision']):
                continue

            # Classify: is this about a specific meeting or annual count?
            is_annual = any(k in title for k in ['how many', 'total', 'in 2026', 'in 2027', 'this year'])

            if is_annual:
                # "How many Fed rate cuts in 2026?" — annual count, don't match to monthly
                m = re.search(r'(20\d{2})', title)
                year = m.group(1) if m else str(datetime.now().year)
                pm_fed_annual[year] = evt
            else:
                # Monthly decision: "Fed Decision in March?"
                date_str = parse_date_from_text(evt.get("title", ""))
                if date_str:
                    month_key = date_str[:7]
                    pm_fed_monthly[month_key] = evt
                else:
                    # Try month name extraction
                    for month_name, month_num in MONTHS.items():
                        if month_name in title:
                            m = re.search(r'(20\d{2})', title)
                            year = int(m.group(1)) if m else datetime.now().year
                            month_key = f"{year:04d}-{month_num:02d}"
                            pm_fed_monthly[month_key] = evt
                            break

        # Find Kalshi Fed decision events (monthly FOMC meetings)
        kalshi_fed = {}
        for series in ["KXFEDDECISION"]:
            events = kalshi_fetch_events_for_series(cache, series, limit=10)
            for evt in events:
                ticker = evt.get("event_ticker", "")
                month_str = parse_month_from_kalshi_ticker(ticker)
                if month_str:
                    markets = kalshi_fetch_markets_for_event(cache, ticker)
                    if markets:
                        kalshi_fed[month_str] = (evt, markets)

        logger.info(f"  Fed rate: {len(pm_fed_monthly)} PM monthly + {len(pm_fed_annual)} annual, "
                     f"{len(kalshi_fed)} Kalshi events")

        # Match monthly PM events to monthly Kalshi events — same month only
        for pm_month, pm_evt in pm_fed_monthly.items():
            for k_month, (k_evt, k_markets) in kalshi_fed.items():
                if pm_month == k_month:
                    self._build_pair(pairs, pm_evt, k_evt, k_markets, pm_month, now)

        # Note: We do NOT match annual PM events ("how many cuts in 2026?") to monthly
        # Kalshi FOMC events — they're fundamentally different questions.

        return pairs

    def _build_pair(self, pairs, pm_evt, k_evt, k_markets, date_key, now):
        pm_tokens = []
        for mkt in pm_evt.get("markets", []):
            yes_p, no_p = pm_parse_token_prices(mkt)
            pm_tokens.append({
                "token_id": mkt.get("conditionId", mkt.get("id", "")),
                "question": mkt.get("question", ""),
                "yes_price": yes_p,
                "no_price": no_p,
            })

        k_market_list = []
        for mkt in k_markets:
            yp, np, yb, ya = kalshi_parse_prices(mkt)
            k_market_list.append({
                "ticker": mkt.get("ticker", ""),
                "title": mkt.get("title", ""),
                "subtitle": mkt.get("subtitle", ""),
                "yes_price": yp,
                "no_price": np,
                "yes_bid": yb,
                "yes_ask": ya,
            })

        pair = MatchedPairV3(
            pair_id=f"fed:{date_key}",
            category="fed_rate",
            asset="fed_decision",
            date=date_key,
            pm_event_id=pm_evt.get("id", ""),
            pm_event_title=pm_evt.get("title", ""),
            pm_event_slug=pm_evt.get("slug", ""),
            pm_tokens=pm_tokens,
            kalshi_event_ticker=k_evt.get("event_ticker", ""),
            kalshi_series_ticker="KXFEDDECISION",
            kalshi_markets=k_market_list,
            match_quality=85,
            notes=f"PM={len(pm_tokens)} outcomes, K={len(k_market_list)} markets.",
            last_update=now,
        )
        pairs.append(pair)


class CPIMatcher(BaseMatcher):
    """Match CPI / inflation data markets.

    PM: Events about CPI data releases
    Kalshi: Series KXCPI (monthly)
    """

    category = "cpi"

    def find_pairs(self, cache: APICache, pm_events: List[Dict]) -> List[MatchedPairV3]:
        pairs = []
        now = time.time()

        # Find PM CPI events
        pm_cpi = {}
        for evt in pm_events:
            title = evt.get("title", "").lower()
            if any(k in title for k in ['cpi', 'consumer price', 'inflation data']):
                # Extract month
                date_str = parse_date_from_text(evt.get("title", ""))
                if date_str:
                    month_key = date_str[:7]
                else:
                    m = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{4})?', title)
                    if m:
                        month_num = MONTHS.get(m.group(1))
                        year = int(m.group(2)) if m.group(2) else datetime.now().year
                        if month_num:
                            month_key = f"{year:04d}-{month_num:02d}"
                        else:
                            continue
                    else:
                        continue
                pm_cpi[month_key] = evt

        # Find Kalshi CPI events
        kalshi_cpi = {}
        for series in ["KXCPI", "KXCPIYOY", "KXCPICORE"]:
            events = kalshi_fetch_events_for_series(cache, series, limit=5)
            for evt in events:
                ticker = evt.get("event_ticker", "")
                month_str = parse_month_from_kalshi_ticker(ticker)
                if month_str:
                    markets = kalshi_fetch_markets_for_event(cache, ticker)
                    if markets:
                        kalshi_cpi[f"{series}:{month_str}"] = (evt, markets, series)

        logger.info(f"  CPI: {len(pm_cpi)} PM events, {len(kalshi_cpi)} Kalshi events")

        # Match by month
        for pm_month, pm_evt in pm_cpi.items():
            for k_key, (k_evt, k_markets, k_series) in kalshi_cpi.items():
                k_month = k_key.split(":")[1]
                if pm_month == k_month:
                    pm_tokens = []
                    for mkt in pm_evt.get("markets", []):
                        yes_p, no_p = pm_parse_token_prices(mkt)
                        pm_tokens.append({
                            "token_id": mkt.get("conditionId", mkt.get("id", "")),
                            "question": mkt.get("question", ""),
                            "yes_price": yes_p,
                            "no_price": no_p,
                        })

                    k_market_list = []
                    for mkt in k_markets:
                        yp, np, yb, ya = kalshi_parse_prices(mkt)
                        k_market_list.append({
                            "ticker": mkt.get("ticker", ""),
                            "title": mkt.get("title", ""),
                            "subtitle": mkt.get("subtitle", ""),
                            "yes_price": yp,
                            "no_price": np,
                            "yes_bid": yb,
                            "yes_ask": ya,
                        })

                    pair = MatchedPairV3(
                        pair_id=f"cpi:{k_series}:{pm_month}",
                        category="cpi",
                        asset="cpi",
                        date=pm_month,
                        pm_event_id=pm_evt.get("id", ""),
                        pm_event_title=pm_evt.get("title", ""),
                        pm_event_slug=pm_evt.get("slug", ""),
                        pm_tokens=pm_tokens,
                        kalshi_event_ticker=k_evt.get("event_ticker", ""),
                        kalshi_series_ticker=k_series,
                        kalshi_markets=k_market_list,
                        match_quality=85,
                        notes=f"PM={len(pm_tokens)} brackets, K={len(k_market_list)} markets.",
                        last_update=now,
                    )
                    pairs.append(pair)

        return pairs


class MovieRTMatcher(BaseMatcher):
    """Match Rotten Tomatoes movie score markets.

    PM: May have events about movie ratings
    Kalshi: Series KXRT with specific movie events
    """

    category = "movies"

    def find_pairs(self, cache: APICache, pm_events: List[Dict]) -> List[MatchedPairV3]:
        pairs = []
        now = time.time()

        # Find PM movie/RT events
        pm_movies = {}
        for evt in pm_events:
            title = evt.get("title", "").lower()
            if any(k in title for k in ['rotten tomato', 'rt score', 'movie rating']):
                # Extract movie name
                movie_name = self._extract_movie_name(evt.get("title", ""))
                if movie_name:
                    pm_movies[movie_name.lower()] = evt

        # Find Kalshi RT events
        kalshi_movies = {}
        events = kalshi_fetch_events_for_series(cache, "KXRT", limit=20)
        for evt in events:
            ticker = evt.get("event_ticker", "")
            title = evt.get("title", "")
            movie_name = self._extract_movie_name(title)
            if movie_name:
                markets = kalshi_fetch_markets_for_event(cache, ticker)
                if markets:
                    kalshi_movies[movie_name.lower()] = (evt, markets)

        logger.info(f"  Movies: {len(pm_movies)} PM events, {len(kalshi_movies)} Kalshi events")

        # Match by movie name (fuzzy)
        for k_movie, (k_evt, k_markets) in kalshi_movies.items():
            pm_evt = pm_movies.get(k_movie)
            if not pm_evt:
                # Try fuzzy match
                for pm_movie, pm_e in pm_movies.items():
                    if pm_movie in k_movie or k_movie in pm_movie:
                        pm_evt = pm_e
                        break

            if not pm_evt:
                continue

            pm_tokens = []
            for mkt in pm_evt.get("markets", []):
                yes_p, no_p = pm_parse_token_prices(mkt)
                pm_tokens.append({
                    "token_id": mkt.get("conditionId", mkt.get("id", "")),
                    "question": mkt.get("question", ""),
                    "yes_price": yes_p,
                    "no_price": no_p,
                })

            k_market_list = []
            for mkt in k_markets:
                yp, np, yb, ya = kalshi_parse_prices(mkt)
                k_market_list.append({
                    "ticker": mkt.get("ticker", ""),
                    "title": mkt.get("title", ""),
                    "subtitle": mkt.get("subtitle", ""),
                    "yes_price": yp,
                    "no_price": np,
                    "yes_bid": yb,
                    "yes_ask": ya,
                })

            pair = MatchedPairV3(
                pair_id=f"movie:{k_movie.replace(' ', '_')}",
                category="movies",
                asset=k_movie,
                date="ongoing",
                pm_event_id=pm_evt.get("id", ""),
                pm_event_title=pm_evt.get("title", ""),
                pm_event_slug=pm_evt.get("slug", ""),
                pm_tokens=pm_tokens,
                kalshi_event_ticker=k_evt.get("event_ticker", ""),
                kalshi_series_ticker="KXRT",
                kalshi_markets=k_market_list,
                match_quality=80,
                notes=f"Movie: {k_movie}",
                last_update=now,
            )
            pairs.append(pair)

        return pairs

    @staticmethod
    def _extract_movie_name(title: str) -> Optional[str]:
        # "\"Scream 7\" Rotten Tomatoes score?" → "Scream 7"
        m = re.search(r'"([^"]+)"', title)
        if m:
            return m.group(1)
        m = re.search(r'"([^"]+)"', title)
        if m:
            return m.group(1)
        return None


class SoccerMatcher(BaseMatcher):
    """Match soccer/football markets.

    PM: FIFA World Cup, Premier League events
    Kalshi: KXWCGAME (World Cup games), KXPREMIERLEAGUE
    """

    category = "soccer"

    def find_pairs(self, cache: APICache, pm_events: List[Dict]) -> List[MatchedPairV3]:
        pairs = []
        now = time.time()

        # Find PM soccer events
        pm_soccer = {}
        for evt in pm_events:
            title = evt.get("title", "").lower()
            slug = evt.get("slug", "").lower()
            if any(k in title for k in ['world cup', 'premier league', 'fifa',
                                         'champions league', 'la liga', 'bundesliga']):
                # Categorize: tournament winner vs specific game
                if 'winner' in title or 'champion' in title:
                    pm_soccer[f"winner:{slug}"] = evt
                elif 'vs' in title or 'vs.' in title:
                    pm_soccer[f"game:{slug}"] = evt

        # Find Kalshi soccer events
        kalshi_soccer = {}
        for series in ["KXWCGAME", "KXPREMIERLEAGUE", "KXCHAMPIONSLEAGUE"]:
            events = kalshi_fetch_events_for_series(cache, series, limit=20)
            for evt in events:
                ticker = evt.get("event_ticker", "")
                title = evt.get("title", "").lower()
                markets = kalshi_fetch_markets_for_event(cache, ticker)
                if markets:
                    if 'winner' in title:
                        kalshi_soccer[f"winner:{series}"] = (evt, markets, series)
                    else:
                        kalshi_soccer[f"game:{ticker}"] = (evt, markets, series)

        logger.info(f"  Soccer: {len(pm_soccer)} PM events, {len(kalshi_soccer)} Kalshi events")

        # Match tournament winners (Premier League, World Cup)
        for pm_key, pm_evt in pm_soccer.items():
            pm_type = pm_key.split(":")[0]
            pm_title = pm_evt.get("title", "").lower()

            for k_key, (k_evt, k_markets, k_series) in kalshi_soccer.items():
                k_type = k_key.split(":")[0]
                k_title = k_evt.get("title", "").lower()

                if pm_type != k_type:
                    continue

                # Check if they're about the same tournament
                if pm_type == "winner":
                    if ("premier league" in pm_title and k_series == "KXPREMIERLEAGUE") or \
                       ("world cup" in pm_title and k_series in ["KXWCGAME", "KXFIFA"]):

                        pm_tokens = []
                        for mkt in pm_evt.get("markets", []):
                            yes_p, no_p = pm_parse_token_prices(mkt)
                            pm_tokens.append({
                                "token_id": mkt.get("conditionId", mkt.get("id", "")),
                                "question": mkt.get("question", ""),
                                "outcomes": mkt.get("outcomes", []),
                                "yes_price": yes_p,
                                "no_price": no_p,
                            })

                        k_market_list = []
                        for mkt in k_markets:
                            yp, np, yb, ya = kalshi_parse_prices(mkt)
                            k_market_list.append({
                                "ticker": mkt.get("ticker", ""),
                                "title": mkt.get("title", ""),
                                "yes_price": yp,
                                "no_price": np,
                                "yes_bid": yb,
                                "yes_ask": ya,
                            })

                        tournament = "premier_league" if "premier" in pm_title else "world_cup"
                        pair = MatchedPairV3(
                            pair_id=f"soccer:{tournament}:winner",
                            category="soccer",
                            asset=tournament,
                            date="season",
                            pm_event_id=pm_evt.get("id", ""),
                            pm_event_title=pm_evt.get("title", ""),
                            pm_event_slug=pm_evt.get("slug", ""),
                            pm_tokens=pm_tokens,
                            kalshi_event_ticker=k_evt.get("event_ticker", ""),
                            kalshi_series_ticker=k_series,
                            kalshi_markets=k_market_list,
                            match_quality=82,
                            notes=f"Tournament winner market. PM={len(pm_tokens)}, K={len(k_market_list)}.",
                            last_update=now,
                        )
                        pairs.append(pair)

        return pairs


# ============================================================================
# MAIN MATCHING ENGINE
# ============================================================================

class MatcherEngine:
    """Central orchestrator for all category matchers."""

    def __init__(self):
        self.cache = get_api_cache()
        self.matchers: List[BaseMatcher] = [
            WeatherMatcher(),
            CryptoMatcher(),
            NBAMatcher(),
            TrumpMentionMatcher(),
            ElonTweetsMatcher(),
            FedRateMatcher(),
            CPIMatcher(),
            MovieRTMatcher(),
            SoccerMatcher(),
        ]
        self.last_scan_time = 0.0
        self.last_pairs: List[MatchedPairV3] = []

    def find_all_pairs(self, force_refresh: bool = False) -> List[MatchedPairV3]:
        """Find all cross-platform matched pairs across all categories.

        Returns deduplicated list of MatchedPairV3.
        """
        start_time = time.time()

        if force_refresh:
            self.cache.invalidate()

        logger.info("=" * 60)
        logger.info("🔍 MARKET MATCHER v3 — Starting full scan")
        logger.info("=" * 60)

        # Step 1: Fetch all PM events (shared across matchers)
        logger.info("📡 Fetching Polymarket events...")
        pm_events = pm_fetch_events_paginated(self.cache, max_pages=5)
        logger.info(f"  → {len(pm_events)} PM events fetched")

        # Step 2: Run each category matcher
        all_pairs = []
        for matcher in self.matchers:
            try:
                logger.info(f"\n🔗 Running {matcher.category} matcher...")
                cat_pairs = matcher.find_pairs(self.cache, pm_events)
                all_pairs.extend(cat_pairs)
                if cat_pairs:
                    logger.info(f"  ✅ {matcher.category}: {len(cat_pairs)} pairs found")
                else:
                    logger.info(f"  ⬚ {matcher.category}: 0 pairs (OK if no overlap exists)")
            except Exception as e:
                logger.error(f"  ❌ {matcher.category} matcher error: {e}")
                import traceback
                logger.debug(traceback.format_exc())

        # Step 3: Deduplicate (by pair_id)
        seen_ids = set()
        deduped = []
        for pair in all_pairs:
            if pair.pair_id not in seen_ids:
                seen_ids.add(pair.pair_id)
                deduped.append(pair)

        elapsed = time.time() - start_time
        self.last_scan_time = time.time()
        self.last_pairs = deduped

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 SCAN COMPLETE in {elapsed:.1f}s — {len(deduped)} total pairs")
        by_cat = defaultdict(int)
        for p in deduped:
            by_cat[p.category] += 1
        for cat, count in sorted(by_cat.items()):
            logger.info(f"  {cat}: {count} pairs")
        logger.info(f"  Cache stats: {self.cache.stats}")
        logger.info("=" * 60)

        return deduped

    def get_pairs_by_category(self) -> Dict[str, List[MatchedPairV3]]:
        """Return last scan results grouped by category."""
        result = defaultdict(list)
        for p in self.last_pairs:
            result[p.category].append(p)
        return dict(result)

    def refresh_prices(self, pairs: List[MatchedPairV3] = None) -> List[MatchedPairV3]:
        """Quick price refresh for existing pairs (no full re-scan).

        Re-fetches PM and Kalshi prices for the given pairs.
        """
        if pairs is None:
            pairs = self.last_pairs

        for pair in pairs:
            try:
                # Refresh PM prices
                if pair.pm_event_slug:
                    evt = pm_fetch_event_by_slug(self.cache, pair.pm_event_slug)
                    if evt:
                        new_tokens = []
                        for mkt in evt.get("markets", []):
                            yes_p, no_p = pm_parse_token_prices(mkt)
                            token_id = mkt.get("conditionId", mkt.get("id", ""))
                            # Find matching existing token
                            existing = None
                            for t in pair.pm_tokens:
                                if t.get("token_id") == token_id:
                                    existing = t
                                    break
                            if existing:
                                existing["yes_price"] = yes_p
                                existing["no_price"] = no_p

                # Refresh Kalshi prices
                if pair.kalshi_event_ticker:
                    markets = kalshi_fetch_markets_for_event(
                        self.cache, pair.kalshi_event_ticker)
                    if markets:
                        for mkt in markets:
                            ticker = mkt.get("ticker", "")
                            yp, np, yb, ya = kalshi_parse_prices(mkt)
                            for km in pair.kalshi_markets:
                                if km.get("ticker") == ticker:
                                    km["yes_price"] = yp
                                    km["no_price"] = np
                                    km["yes_bid"] = yb
                                    km["yes_ask"] = ya

                pair.last_update = time.time()

            except Exception as e:
                logger.debug(f"Price refresh error for {pair.pair_id}: {e}")

        return pairs


# ============================================================================
# BACKWARD COMPATIBILITY LAYER
# ============================================================================
# These adapters let the existing CrossPlatformTrader use the new matcher
# without changing its signal generation and trade execution code.

def convert_v3_to_legacy_pair(pair: MatchedPairV3) -> Dict:
    """Convert MatchedPairV3 to a format compatible with the legacy MatchedPair structure.

    For spread calculation:
    - Crypto/weather: use the first PM token's yes_price vs first K market's yes_price
    - NBA: use the moneyline yes_price from PM vs the first K market
    - Others: use first token/market prices
    """
    # Default: use first PM token and first K market
    pm_yes = 0.0
    pm_no = 0.0
    k_yes = 0.0
    k_no = 0.0
    k_bid = 0.0
    k_ask = 0.0

    if pair.pm_tokens:
        tok = pair.pm_tokens[0]
        pm_yes = tok.get("yes_price", 0)
        pm_no = tok.get("no_price", 1.0 - pm_yes)

    if pair.kalshi_markets:
        km = pair.kalshi_markets[0]
        k_yes = km.get("yes_price", 0)
        k_no = km.get("no_price", 1.0 - k_yes)
        k_bid = km.get("yes_bid", 0)
        k_ask = km.get("yes_ask", 0)

    return {
        "pair_id": pair.pair_id,
        "pm_yes_price": pm_yes,
        "pm_no_price": pm_no,
        "kalshi_yes_price": k_yes,
        "kalshi_no_price": k_no,
        "kalshi_bid": k_bid,
        "kalshi_ask": k_ask,
        "spread": pm_yes - k_yes,
        "match_score": pair.match_quality,
        "category": pair.category,
        "asset": pair.asset,
        "date": pair.date,
        "pm_title": pair.pm_event_title,
        "kalshi_title": pair.kalshi_event_ticker,
        "notes": pair.notes,
    }


# ============================================================================
# STANDALONE ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Setup logging for standalone use
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    engine = MatcherEngine()
    pairs = engine.find_all_pairs()

    print("\n" + "=" * 70)
    print(f"MATCHED PAIRS SUMMARY: {len(pairs)} total")
    print("=" * 70)

    by_cat = engine.get_pairs_by_category()
    for cat, cat_pairs in sorted(by_cat.items()):
        print(f"\n{'─' * 50}")
        print(f"📂 {cat.upper()} ({len(cat_pairs)} pairs)")
        print(f"{'─' * 50}")
        for p in cat_pairs:
            print(f"  {p.pair_id}")
            print(f"    PM: {p.pm_event_title[:70]}")
            print(f"    K:  {p.kalshi_event_ticker}")
            print(f"    Quality: {p.match_quality} | {p.notes[:80]}")
            if p.pm_tokens:
                tok = p.pm_tokens[0]
                print(f"    PM sample: {tok.get('question','')[:60]} → yes={tok.get('yes_price',0):.3f}")
            if p.kalshi_markets:
                km = p.kalshi_markets[0]
                print(f"    K sample:  {km.get('title','')[:60]} → yes={km.get('yes_price',0):.3f}")
