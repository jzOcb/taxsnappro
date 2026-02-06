#!/usr/bin/env python3
"""
Weather Paper Trader for Kalshi Temperature Markets
====================================================
Multi-source ensemble forecast → Normal distribution fair value → Paper trade when edge > threshold.

Settlement: NWS Climatological Report (CLI) from specific airport stations.
Strategy: Fetch forecasts from NWS + Open-Meteo, weight by accuracy,
          model temperature as Normal(μ, σ²), calculate bracket probabilities,
          paper trade when |fair_value - market_price| > min_edge.

Usage:
    python3 -u src/weather_paper_trader.py [duration_minutes]
"""

import sys
import os
import json
import time
import math
import logging
import signal
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

# scipy for normal distribution
from scipy.stats import norm

import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

# Minimum edge (cents) to trigger a paper trade. Must cover fees (~4¢) + spread (~2¢)
MIN_EDGE_CENTS = 8

# Maximum position per city per day ($)
MAX_POSITION_PER_CITY = 50.0

# Paper trading bankroll
STARTING_BANKROLL = 1000.0

# Forecast polling interval (seconds)
FORECAST_INTERVAL = 1800  # 30 minutes

# Kalshi price polling interval (seconds)
KALSHI_INTERVAL = 300  # 5 minutes

# Fee per contract per side (cents)
FEE_PER_SIDE = 2  # ~2¢ per side, 4¢ round trip

# Minimum volume to trade
MIN_VOLUME = 100

# Maximum spread (cents) to trade
MAX_SPREAD = 5

# Default sigma (°F) for forecast uncertainty when we only have one source
DEFAULT_SIGMA = 3.0

# Minimum sigma floor - never trust forecast more than this
MIN_SIGMA = 1.5

# ============================================================================
# CITY DATA — Airport coordinates + NWS grid points + station IDs
# ============================================================================

CITIES = {
    "LAX": {
        "name": "Los Angeles",
        "series": "KXHIGHLAX",
        "lat": 33.9425, "lon": -118.4081,  # LAX airport
        "nws_wfo": "LOX", "nws_grid_x": 149, "nws_grid_y": 48,
        "station": "KLAX",
        "cli_wfo": "LOX", "cli_station": "LAX",
        "historical_mae": 2.5,
        "timezone_offset": -8,  # PST
        "predictability": "high",
    },
    "NYC": {
        "name": "New York",
        "series": "KXHIGHNY",
        "lat": 40.7831, "lon": -73.9712,  # Central Park (NOT airport!)
        "nws_wfo": "OKX", "nws_grid_x": 33, "nws_grid_y": 37,
        "station": "KNYC",  # Central Park
        "cli_wfo": "OKX", "cli_station": "NYC",
        "historical_mae": 2.8,
        "timezone_offset": -5,  # EST
        "predictability": "moderate",
    },
    "CHI": {
        "name": "Chicago",
        "series": "KXHIGHCHI",
        "lat": 41.7868, "lon": -87.7522,  # Midway
        "nws_wfo": "LOT", "nws_grid_x": 76, "nws_grid_y": 73,
        "station": "KMDW",
        "cli_wfo": "LOT", "cli_station": "MDW",
        "historical_mae": 3.0,
        "timezone_offset": -6,  # CST
        "predictability": "moderate",
    },
    "PHI": {
        "name": "Philadelphia",
        "series": "KXHIGHPHIL",
        "lat": 39.8744, "lon": -75.2424,  # PHL airport
        "nws_wfo": "PHI", "nws_grid_x": 57, "nws_grid_y": 78,
        "station": "KPHL",
        "cli_wfo": "PHI", "cli_station": "PHL",
        "historical_mae": 2.8,
        "timezone_offset": -5,
        "predictability": "moderate",
    },
    "BOS": {
        "name": "Boston",
        "series": "KXHIGHTBOS",
        "lat": 42.3656, "lon": -71.0096,  # Logan Airport
        "nws_wfo": "BOX", "nws_grid_x": 71, "nws_grid_y": 90,
        "station": "KBOS",
        "cli_wfo": "BOX", "cli_station": "BOS",
        "historical_mae": 2.8,
        "timezone_offset": -5,
        "predictability": "moderate",
    },
    "DEN": {
        "name": "Denver",
        "series": "KXHIGHDEN",
        "lat": 39.8561, "lon": -104.6737,  # DIA
        "nws_wfo": "BOU", "nws_grid_x": 62, "nws_grid_y": 60,
        "station": "KDEN",
        "cli_wfo": "BOU", "cli_station": "DEN",
        "historical_mae": 4.0,  # Denver is unpredictable
        "timezone_offset": -7,
        "predictability": "low",
    },
    "MIA": {
        "name": "Miami",
        "series": "KXHIGHMIA",
        "lat": 25.7959, "lon": -80.2870,  # MIA airport
        "nws_wfo": "MFL", "nws_grid_x": 76, "nws_grid_y": 50,
        "station": "KMIA",
        "cli_wfo": "MFL", "cli_station": "MIA",
        "historical_mae": 2.2,
        "timezone_offset": -5,
        "predictability": "high",
    },
    "SFO": {
        "name": "San Francisco",
        "series": "KXHIGHTSFO",
        "lat": 37.6213, "lon": -122.3790,  # SFO airport
        "nws_wfo": "MTR", "nws_grid_x": 88, "nws_grid_y": 105,
        "station": "KSFO",
        "cli_wfo": "MTR", "cli_station": "SFO",
        "historical_mae": 3.0,
        "timezone_offset": -8,
        "predictability": "moderate",
    },
    "DC": {
        "name": "Washington DC",
        "series": "KXHIGHTDC",
        "lat": 38.8512, "lon": -77.0402,  # DCA (Reagan National)
        "nws_wfo": "LWX", "nws_grid_x": 96, "nws_grid_y": 70,
        "station": "KDCA",
        "cli_wfo": "LWX", "cli_station": "DCA",
        "historical_mae": 2.8,
        "timezone_offset": -5,
        "predictability": "moderate",
    },
    "AUS": {
        "name": "Austin",
        "series": "KXHIGHAUS",
        "lat": 30.1975, "lon": -97.6664,  # AUS airport
        "nws_wfo": "EWX", "nws_grid_x": 156, "nws_grid_y": 91,
        "station": "KAUS",
        "cli_wfo": "EWX", "cli_station": "AUS",
        "historical_mae": 2.5,
        "timezone_offset": -6,
        "predictability": "moderate",
    },
    "SEA": {
        "name": "Seattle",
        "series": "KXHIGHTSEA",
        "lat": 47.4502, "lon": -122.3088,  # SeaTac
        "nws_wfo": "SEW", "nws_grid_x": 124, "nws_grid_y": 67,
        "station": "KSEA",
        "cli_wfo": "SEW", "cli_station": "SEA",
        "historical_mae": 3.0,
        "timezone_offset": -8,
        "predictability": "moderate",
    },
    "LV": {
        "name": "Las Vegas",
        "series": "KXHIGHTLV",
        "lat": 36.0840, "lon": -115.1537,  # Harry Reid (LAS)
        "nws_wfo": "VEF", "nws_grid_x": 122, "nws_grid_y": 99,
        "station": "KLAS",
        "cli_wfo": "VEF", "cli_station": "LAS",
        "historical_mae": 2.5,
        "timezone_offset": -8,
        "predictability": "high",
    },
    "NOLA": {
        "name": "New Orleans",
        "series": "KXHIGHTNOLA",
        "lat": 29.9934, "lon": -90.2580,  # MSY airport
        "nws_wfo": "LIX", "nws_grid_x": 68, "nws_grid_y": 56,
        "station": "KMSY",
        "cli_wfo": "LIX", "cli_station": "MSY",
        "historical_mae": 2.5,
        "timezone_offset": -6,
        "predictability": "moderate",
    },
    "PHX": {
        "name": "Phoenix",
        "series": "KXHIGHTPHX",
        "lat": 33.4373, "lon": -112.0078,  # Sky Harbor
        "nws_wfo": "PSR", "nws_grid_x": 159, "nws_grid_y": 56,
        "station": "KPHX",
        "cli_wfo": "PSR", "cli_station": "PHX",
        "historical_mae": 2.0,
        "timezone_offset": -7,  # MST (no DST)
        "predictability": "high",
    },
    "ATL": {
        "name": "Atlanta",
        "series": "KXHIGHTATL",
        "lat": 33.6407, "lon": -84.4277,  # Hartsfield
        "nws_wfo": "FFC", "nws_grid_x": 52, "nws_grid_y": 88,
        "station": "KATL",
        "cli_wfo": "FFC", "cli_station": "ATL",
        "historical_mae": 2.8,
        "timezone_offset": -5,
        "predictability": "moderate",
    },
    "MIN": {
        "name": "Minneapolis",
        "series": "KXHIGHTMIN",
        "lat": 44.8848, "lon": -93.2223,  # MSP airport
        "nws_wfo": "MPX", "nws_grid_x": 107, "nws_grid_y": 71,
        "station": "KMSP",
        "cli_wfo": "MPX", "cli_station": "MSP",
        "historical_mae": 4.0,
        "timezone_offset": -6,
        "predictability": "low",
    },
}

# ============================================================================
# LOGGING
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / "weather_paper_trader.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("weather_trader")

# ============================================================================
# STATE FILE
# ============================================================================

STATE_FILE = BASE_DIR / "weather_trader_state.json"

def load_state():
    """Load paper trading state from disk."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
    return {
        "bankroll": STARTING_BANKROLL,
        "total_pnl": 0.0,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "positions": [],  # active positions
        "settled_trades": [],  # historical
        "daily_exposure": {},  # city -> $ deployed today
        "forecasts": {},  # city -> latest forecast data
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_update": datetime.now(timezone.utc).isoformat(),
    }

def save_state(state):
    """Persist state to disk."""
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

# ============================================================================
# WEATHER DATA FETCHING
# ============================================================================

def fetch_nws_forecast(city_key):
    """Fetch NWS grid forecast for a city. Returns predicted high temp (°F) or None."""
    city = CITIES[city_key]
    wfo = city["nws_wfo"]
    gx, gy = city["nws_grid_x"], city["nws_grid_y"]
    
    url = f"https://api.weather.gov/gridpoints/{wfo}/{gx},{gy}/forecast"
    headers = {"User-Agent": "KalshiWeatherTrader/1.0 (research@example.com)"}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            logger.warning(f"NWS {city_key}: HTTP {r.status_code}")
            return None
        
        data = r.json()
        periods = data.get("properties", {}).get("periods", [])
        
        if not periods:
            return None
        
        # Find today's daytime forecast (isDaytime=True, first one)
        now_utc = datetime.now(timezone.utc)
        today_str = (now_utc + timedelta(hours=city["timezone_offset"])).strftime("%Y-%m-%d")
        
        for p in periods:
            start = p.get("startTime", "")[:10]
            if p.get("isDaytime") and start == today_str:
                temp = p.get("temperature")
                if temp is not None:
                    return float(temp)
        
        # Fallback: if we're past daytime, look at tomorrow
        tomorrow_str = (now_utc + timedelta(hours=city["timezone_offset"]) + timedelta(days=1)).strftime("%Y-%m-%d")
        for p in periods:
            start = p.get("startTime", "")[:10]
            if p.get("isDaytime") and start == tomorrow_str:
                temp = p.get("temperature")
                if temp is not None:
                    return float(temp)
        
        # Last resort: use the hourly forecast to find today's max
        return fetch_nws_hourly_max(city_key, today_str, tomorrow_str)
        
    except Exception as e:
        logger.warning(f"NWS {city_key} error: {e}")
        return None


def fetch_nws_hourly_max(city_key, today_str, tomorrow_str):
    """Fetch NWS hourly forecast and find max temp for today."""
    city = CITIES[city_key]
    wfo = city["nws_wfo"]
    gx, gy = city["nws_grid_x"], city["nws_grid_y"]
    
    url = f"https://api.weather.gov/gridpoints/{wfo}/{gx},{gy}/forecast/hourly"
    headers = {"User-Agent": "KalshiWeatherTrader/1.0 (research@example.com)"}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None
        
        data = r.json()
        periods = data.get("properties", {}).get("periods", [])
        
        # For overnight runs, we might want tomorrow's data
        target_date = today_str
        temps = []
        for p in periods:
            start = p.get("startTime", "")[:10]
            if start == target_date:
                temp = p.get("temperature")
                if temp is not None:
                    temps.append(float(temp))
        
        if not temps:
            # Try tomorrow
            for p in periods:
                start = p.get("startTime", "")[:10]
                if start == tomorrow_str:
                    temp = p.get("temperature")
                    if temp is not None:
                        temps.append(float(temp))
        
        return max(temps) if temps else None
        
    except Exception as e:
        logger.warning(f"NWS hourly {city_key} error: {e}")
        return None


def fetch_openmeteo_forecast(city_key):
    """Fetch Open-Meteo forecast for a city. Returns predicted high temp (°F) or None."""
    city = CITIES[city_key]
    lat, lon = city["lat"], city["lon"]
    
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min"
        f"&temperature_unit=fahrenheit"
        f"&timezone=America/New_York"
        f"&forecast_days=3"
    )
    
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            logger.warning(f"Open-Meteo {city_key}: HTTP {r.status_code}")
            return None
        
        data = r.json()
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        highs = daily.get("temperature_2m_max", [])
        
        if not dates or not highs:
            return None
        
        # Find today's and tomorrow's forecast
        now_utc = datetime.now(timezone.utc)
        # Use ET for date matching since Kalshi uses ET
        today_et = (now_utc + timedelta(hours=-5)).strftime("%Y-%m-%d")
        tomorrow_et = (now_utc + timedelta(hours=-5) + timedelta(days=1)).strftime("%Y-%m-%d")
        
        result = {}
        for i, d in enumerate(dates):
            if d == today_et and i < len(highs) and highs[i] is not None:
                result["today"] = round(highs[i], 1)
            elif d == tomorrow_et and i < len(highs) and highs[i] is not None:
                result["tomorrow"] = round(highs[i], 1)
        
        # Return today if available and it's before settlement, otherwise tomorrow
        # Settlement is checked at end of day, so during overnight we want tomorrow
        hour_et = (now_utc + timedelta(hours=-5)).hour
        if hour_et >= 20:  # After 8pm ET, focus on tomorrow's markets
            return result.get("tomorrow", result.get("today"))
        else:
            return result.get("today", result.get("tomorrow"))
        
    except Exception as e:
        logger.warning(f"Open-Meteo {city_key} error: {e}")
        return None


def fetch_all_forecasts():
    """Fetch forecasts from all sources for all cities."""
    forecasts = {}
    
    for city_key in CITIES:
        nws = fetch_nws_forecast(city_key)
        om = fetch_openmeteo_forecast(city_key)
        
        sources = {}
        if nws is not None:
            sources["nws"] = nws
        if om is not None:
            sources["openmeteo"] = om
        
        if not sources:
            logger.warning(f"⚠️ {city_key}: No forecast data available")
            forecasts[city_key] = None
            continue
        
        # Calculate ensemble: inverse-MAE² weighted average
        city = CITIES[city_key]
        hist_mae = city["historical_mae"]
        
        # Simple average if only one source; weighted if multiple
        temps = list(sources.values())
        if len(temps) == 1:
            mu = temps[0]
            sigma = max(hist_mae, MIN_SIGMA)
        else:
            # Weight by assumed accuracy (NWS slightly better for US)
            # NWS weight: 1/2.5² = 0.16, OM weight: 1/3.0² = 0.11
            nws_w = 1.0 / (2.5 ** 2) if "nws" in sources else 0
            om_w = 1.0 / (3.0 ** 2) if "openmeteo" in sources else 0
            total_w = nws_w + om_w
            
            mu = 0
            if nws_w > 0:
                mu += (nws_w / total_w) * sources["nws"]
            if om_w > 0:
                mu += (om_w / total_w) * sources["openmeteo"]
            
            # Sigma: max of source spread and historical MAE
            source_spread = max(temps) - min(temps)
            sigma = max(source_spread, hist_mae, MIN_SIGMA)
        
        forecasts[city_key] = {
            "mu": round(mu, 1),
            "sigma": round(sigma, 1),
            "sources": sources,
            "source_count": len(sources),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.info(
            f"🌡️ {city_key}: μ={mu:.1f}°F σ={sigma:.1f}°F "
            f"(NWS={sources.get('nws', '?')} OM={sources.get('openmeteo', '?')})"
        )
    
    return forecasts

# ============================================================================
# KALSHI MARKET DATA
# ============================================================================

def fetch_kalshi_markets(city_key):
    """Fetch open Kalshi weather markets for a city."""
    city = CITIES[city_key]
    series = city["series"]
    
    url = "https://api.elections.kalshi.com/trade-api/v2/markets"
    params = {"series_ticker": series, "status": "open", "limit": 20}
    headers = {"accept": "application/json"}
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code != 200:
            logger.warning(f"Kalshi {city_key}: HTTP {r.status_code}")
            return []
        
        markets = r.json().get("markets", [])
        
        # Parse each market into a structured format
        parsed = []
        for m in markets:
            ticker = m.get("ticker", "")
            title = m.get("title", "")
            yes_bid = m.get("yes_bid", 0)  # cents
            yes_ask = m.get("yes_ask", 0)  # cents
            volume = m.get("volume", 0)
            close_time = m.get("close_time", "")
            
            # Parse bracket from ticker
            # Format: KXHIGHLAX-26FEB05-T84 (above 84), KXHIGHLAX-26FEB05-B81.5 (between 81-82)
            bracket = parse_bracket(ticker, title)
            if bracket is None:
                continue
            
            # Parse date from ticker
            market_date = parse_market_date(ticker)
            
            parsed.append({
                "ticker": ticker,
                "title": title,
                "yes_bid": yes_bid,
                "yes_ask": yes_ask,
                "no_bid": 100 - yes_ask if yes_ask > 0 else 0,
                "no_ask": 100 - yes_bid if yes_bid > 0 else 0,
                "volume": volume,
                "close_time": close_time,
                "market_date": market_date,
                "bracket_type": bracket["type"],
                "bracket_low": bracket.get("low"),
                "bracket_high": bracket.get("high"),
                "bracket_threshold": bracket.get("threshold"),
                "spread": yes_ask - yes_bid if yes_ask > 0 and yes_bid > 0 else 99,
            })
        
        return parsed
        
    except Exception as e:
        logger.warning(f"Kalshi {city_key} error: {e}")
        return []


def parse_bracket(ticker, title):
    """Parse bracket info from ticker and title.
    
    Formats:
        KXHIGHLAX-26FEB05-T84    → above 84 (threshold)
        KXHIGHLAX-26FEB05-T77    → below 77 (if title says 'below' or '<')
        KXHIGHLAX-26FEB05-B81.5  → between 81-82 (bracket, .5 = midpoint)
    """
    title_lower = title.lower()
    
    parts = ticker.split("-")
    if len(parts) < 3:
        return None
    
    code = parts[-1]  # T84 or B81.5
    
    if code.startswith("T"):
        # Threshold market: above or below
        try:
            threshold = float(code[1:])
        except ValueError:
            return None
        
        if "<" in title_lower or "below" in title_lower:
            return {"type": "below", "threshold": threshold}
        else:
            return {"type": "above", "threshold": threshold}
    
    elif code.startswith("B"):
        # Bracket market: between X and X+2
        try:
            midpoint = float(code[1:])
            low = midpoint - 0.5
            high = midpoint + 0.5
            # Brackets are actually 2°F wide: e.g., B29.5 = 29-30
            # Actually the .5 IS the midpoint of 2°F bracket
            low = math.floor(midpoint)
            high = math.ceil(midpoint) + 1  # e.g., B29.5 → 29 to 31? No...
            # Let me re-examine. B31.5 = "31-32°F"
            # So: low = int(midpoint - 0.5) = 31, high = int(midpoint + 0.5) = 32
            low = int(midpoint - 0.5)
            high = int(midpoint + 0.5)
            return {"type": "between", "low": low, "high": high}
        except ValueError:
            return None
    
    return None


def parse_market_date(ticker):
    """Parse date from ticker. E.g., KXHIGHNY-26FEB05-T36 → 2026-02-05."""
    parts = ticker.split("-")
    if len(parts) < 2:
        return None
    
    date_part = parts[1]  # 26FEB05
    try:
        # Format: YYMMMDD
        year = 2000 + int(date_part[:2])
        month_str = date_part[2:5].upper()
        day = int(date_part[5:])
        months = {
            "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
            "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
        }
        month = months.get(month_str)
        if month:
            return f"{year}-{month:02d}-{day:02d}"
    except (ValueError, IndexError):
        pass
    return None


# ============================================================================
# FAIR VALUE CALCULATION
# ============================================================================

def calculate_fair_values(forecast, markets):
    """Calculate fair value for each market bracket using Normal distribution.
    
    Args:
        forecast: dict with "mu" and "sigma"
        markets: list of parsed Kalshi markets
    
    Returns:
        list of dicts with fair_value and edge added
    """
    if forecast is None:
        return []
    
    mu = forecast["mu"]
    sigma = forecast["sigma"]
    
    results = []
    for m in markets:
        bt = m["bracket_type"]
        
        if bt == "between":
            low = m["bracket_low"]
            high = m["bracket_high"]
            # P(low <= T <= high) — BUT Kalshi uses inclusive
            # For the Normal model: P(low-0.5 < T < high+0.5) to handle integer boundaries
            # Actually the bracket "29-30" means temp >= 29 AND <= 30
            # So fair_value = P(29 <= T <= 30) = Phi((30-mu)/sigma) - Phi((29-mu)/sigma)
            # But temp is recorded as integer in CLI, so this is correct
            fair_p = norm.cdf(high + 0.5, mu, sigma) - norm.cdf(low - 0.5, mu, sigma)
            
        elif bt == "above":
            threshold = m["bracket_threshold"]
            # P(T > threshold) = 1 - Phi(threshold / sigma)
            fair_p = 1 - norm.cdf(threshold + 0.5, mu, sigma)
            
        elif bt == "below":
            threshold = m["bracket_threshold"]
            # P(T < threshold) = Phi((threshold-0.5) / sigma)
            fair_p = norm.cdf(threshold - 0.5, mu, sigma)
        else:
            continue
        
        fair_cents = round(fair_p * 100, 1)
        
        # Calculate edge for both YES and NO sides
        # YES edge: we buy YES at yes_ask, fair value = fair_cents
        yes_edge = fair_cents - m["yes_ask"] if m["yes_ask"] > 0 else -999
        
        # NO edge: we buy NO at no_ask (= 100 - yes_bid), fair NO value = 100 - fair_cents
        no_fair = 100 - fair_cents
        no_edge = no_fair - m["no_ask"] if m["no_ask"] > 0 else -999
        
        m_copy = dict(m)
        m_copy["fair_value_yes"] = round(fair_cents, 1)
        m_copy["fair_value_no"] = round(no_fair, 1)
        m_copy["yes_edge"] = round(yes_edge, 1)
        m_copy["no_edge"] = round(no_edge, 1)
        m_copy["best_edge"] = round(max(yes_edge, no_edge), 1)
        m_copy["best_side"] = "YES" if yes_edge > no_edge else "NO"
        m_copy["forecast_mu"] = mu
        m_copy["forecast_sigma"] = sigma
        results.append(m_copy)
    
    return results


# ============================================================================
# PAPER TRADING ENGINE
# ============================================================================

def evaluate_trades(state, all_opportunities):
    """Evaluate and execute paper trades based on edge."""
    now = datetime.now(timezone.utc)
    today_str = (now + timedelta(hours=-5)).strftime("%Y-%m-%d")
    
    trades_made = 0
    
    for city_key, opps in all_opportunities.items():
        city = CITIES[city_key]
        city_exposure_key = f"{city_key}_{today_str}"
        current_exposure = state.get("daily_exposure", {}).get(city_exposure_key, 0)
        
        for opp in opps:
            # Filter: minimum edge
            if opp["best_edge"] < MIN_EDGE_CENTS:
                continue
            
            # Filter: spread too wide
            if opp["spread"] > MAX_SPREAD:
                logger.debug(f"Skip {opp['ticker']}: spread {opp['spread']}¢ > {MAX_SPREAD}¢")
                continue
            
            # Filter: volume too low
            if opp["volume"] < MIN_VOLUME:
                logger.debug(f"Skip {opp['ticker']}: volume {opp['volume']} < {MIN_VOLUME}")
                continue
            
            # Filter: already at max exposure for this city
            if current_exposure >= MAX_POSITION_PER_CITY:
                logger.debug(f"Skip {city_key}: max exposure ${MAX_POSITION_PER_CITY}")
                continue
            
            # Filter: check if we already have a position in this market
            existing = [p for p in state["positions"] if p["ticker"] == opp["ticker"]]
            if existing:
                continue
            
            # Determine trade details
            side = opp["best_side"]
            if side == "YES":
                entry_price = opp["yes_ask"]  # we buy at the ask
                fair_value = opp["fair_value_yes"]
                edge = opp["yes_edge"]
            else:
                entry_price = opp["no_ask"]  # we buy NO at 100-yes_bid
                fair_value = opp["fair_value_no"]
                edge = opp["no_edge"]
            
            if entry_price <= 0 or entry_price >= 100:
                continue
            
            # Calculate position size: scale by edge, max $50/city/day
            remaining_budget = MAX_POSITION_PER_CITY - current_exposure
            # Size: edge-weighted, base $20 per trade
            base_size = min(20.0, remaining_budget)
            edge_multiplier = min(edge / MIN_EDGE_CENTS, 3.0)  # max 3x for very high edge
            position_dollars = min(base_size * edge_multiplier, remaining_budget)
            position_dollars = round(position_dollars, 2)
            
            if position_dollars < 1.0:
                continue
            
            # Calculate contracts
            contracts = int(position_dollars / (entry_price / 100))
            if contracts < 1:
                continue
            
            actual_cost = contracts * (entry_price / 100)
            fee = contracts * FEE_PER_SIDE / 100  # entry fee
            
            # Create position
            position = {
                "id": f"W{state['total_trades'] + 1:04d}",
                "city": city_key,
                "ticker": opp["ticker"],
                "title": opp["title"],
                "side": side,
                "contracts": contracts,
                "entry_price": entry_price,
                "entry_cost": round(actual_cost, 2),
                "entry_fee": round(fee, 4),
                "fair_value": round(fair_value, 1),
                "edge": round(edge, 1),
                "forecast_mu": opp["forecast_mu"],
                "forecast_sigma": opp["forecast_sigma"],
                "bracket_type": opp["bracket_type"],
                "bracket_low": opp.get("bracket_low"),
                "bracket_high": opp.get("bracket_high"),
                "bracket_threshold": opp.get("bracket_threshold"),
                "market_date": opp.get("market_date"),
                "entered_at": now.isoformat(),
                "status": "open",
            }
            
            state["positions"].append(position)
            state["total_trades"] += 1
            current_exposure += actual_cost
            
            # Update daily exposure
            if "daily_exposure" not in state:
                state["daily_exposure"] = {}
            state["daily_exposure"][city_exposure_key] = round(current_exposure, 2)
            
            trades_made += 1
            
            # Log the trade
            bracket_str = ""
            if opp["bracket_type"] == "between":
                bracket_str = f"{opp['bracket_low']}-{opp['bracket_high']}°F"
            elif opp["bracket_type"] == "above":
                bracket_str = f">{opp['bracket_threshold']}°F"
            elif opp["bracket_type"] == "below":
                bracket_str = f"<{opp['bracket_threshold']}°F"
            
            logger.info(
                f"📝 PAPER TRADE {position['id']}: {city_key} {bracket_str} "
                f"{side} @ {entry_price}¢ × {contracts} contracts "
                f"(cost=${actual_cost:.2f}, fair={fair_value:.0f}¢, edge={edge:+.0f}¢, "
                f"μ={opp['forecast_mu']:.0f}°F σ={opp['forecast_sigma']:.1f})"
            )
    
    return trades_made


def check_settlements(state):
    """Check if any positions can be settled using NWS CLI data."""
    now = datetime.now(timezone.utc)
    settled = 0
    
    for pos in state["positions"]:
        if pos["status"] != "open":
            continue
        
        market_date = pos.get("market_date")
        if not market_date:
            continue
        
        # Settlement happens the morning after market_date
        # Check if we're past 8 AM ET on the day after
        settle_date = datetime.strptime(market_date, "%Y-%m-%d") + timedelta(days=1)
        settle_time = settle_date.replace(hour=13, minute=0)  # 8 AM ET = 13 UTC
        settle_time = settle_time.replace(tzinfo=timezone.utc)
        
        if now < settle_time:
            continue
        
        # Try to fetch NWS CLI data
        city = CITIES.get(pos["city"])
        if not city:
            continue
        
        actual_high = fetch_nws_cli_high(city, market_date)
        
        if actual_high is None:
            # CLI not yet available, skip
            logger.debug(f"CLI not yet available for {pos['city']} {market_date}")
            continue
        
        # Determine if position won or lost
        won = False
        if pos["bracket_type"] == "between":
            actual_in_bracket = pos["bracket_low"] <= actual_high <= pos["bracket_high"]
            if pos["side"] == "YES":
                won = actual_in_bracket
            else:
                won = not actual_in_bracket
        elif pos["bracket_type"] == "above":
            actual_above = actual_high > pos["bracket_threshold"]
            if pos["side"] == "YES":
                won = actual_above
            else:
                won = not actual_above
        elif pos["bracket_type"] == "below":
            actual_below = actual_high < pos["bracket_threshold"]
            if pos["side"] == "YES":
                won = actual_below
            else:
                won = not actual_below
        
        # Calculate P&L
        if won:
            payout = pos["contracts"] * 1.00  # $1 per contract
            settle_fee = pos["contracts"] * FEE_PER_SIDE / 100
            pnl = payout - pos["entry_cost"] - pos["entry_fee"] - settle_fee
            state["wins"] += 1
        else:
            pnl = -pos["entry_cost"] - pos["entry_fee"]
            state["losses"] += 1
        
        pos["status"] = "settled"
        pos["actual_high"] = actual_high
        pos["won"] = won
        pos["pnl"] = round(pnl, 2)
        pos["settled_at"] = now.isoformat()
        
        state["total_pnl"] += pnl
        state["bankroll"] += pnl
        
        # Move to settled trades
        state["settled_trades"].append(dict(pos))
        
        settled += 1
        
        emoji = "✅" if won else "❌"
        logger.info(
            f"{emoji} SETTLED {pos['id']}: {pos['city']} "
            f"actual={actual_high}°F {'WON' if won else 'LOST'} "
            f"P&L=${pnl:+.2f} (total: ${state['total_pnl']:+.2f})"
        )
    
    # Remove settled positions
    state["positions"] = [p for p in state["positions"] if p["status"] == "open"]
    
    return settled


def fetch_nws_cli_high(city, date_str):
    """Fetch actual high temperature from NWS CLI product.
    
    The CLI is released the morning after the observation day.
    """
    wfo = city["cli_wfo"]
    station = city["cli_station"]
    
    url = f"https://forecast.weather.gov/product.php?site={wfo}&product=CLI&issuedby={station}"
    
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return None
        
        text = r.text
        
        # Parse the CLI text for MAXIMUM temperature
        # Format varies but typically:
        # TEMPERATURE (F)
        #   MAXIMUM    32
        # or
        # MAX TEMPERATURE    32
        
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "MAXIMUM" in line.upper() and "TEMPERATURE" not in line.upper():
                # Look for a number on this line or nearby
                parts = line.split()
                for p in parts:
                    try:
                        val = int(p)
                        if -50 < val < 150:  # reasonable temp range
                            return val
                    except ValueError:
                        continue
            # Also check for "MAXIMUM TEMPERATURE" pattern
            if "MAXIMUM TEMPERATURE" in line.upper() or "MAX TEMPERATURE" in line.upper():
                parts = line.split()
                for p in parts:
                    try:
                        val = int(p)
                        if -50 < val < 150:
                            return val
                    except ValueError:
                        continue
        
        return None
        
    except Exception as e:
        logger.warning(f"CLI fetch error for {station}: {e}")
        return None


# ============================================================================
# POSITION MONITORING (update current market value)
# ============================================================================

def update_position_values(state, all_markets):
    """Update current market value for all open positions."""
    for pos in state["positions"]:
        city_key = pos["city"]
        if city_key not in all_markets:
            continue
        
        for m in all_markets[city_key]:
            if m["ticker"] == pos["ticker"]:
                if pos["side"] == "YES":
                    pos["current_bid"] = m["yes_bid"]
                    pos["current_ask"] = m["yes_ask"]
                    pos["current_value"] = pos["contracts"] * m["yes_bid"] / 100
                else:
                    pos["current_bid"] = m["no_bid"]
                    pos["current_ask"] = m["no_ask"]
                    pos["current_value"] = pos["contracts"] * m["no_bid"] / 100
                
                pos["unrealized_pnl"] = round(
                    pos["current_value"] - pos["entry_cost"] - pos["entry_fee"], 2
                )
                break


# ============================================================================
# REPORTING
# ============================================================================

def print_status(state, all_opportunities):
    """Print a comprehensive status report."""
    now = datetime.now(timezone.utc)
    
    logger.info("=" * 80)
    logger.info(f"🌡️ WEATHER PAPER TRADER STATUS — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info("=" * 80)
    
    # Bankroll & P&L
    logger.info(
        f"💰 Bankroll: ${state['bankroll']:.2f} | "
        f"P&L: ${state['total_pnl']:+.2f} | "
        f"Trades: {state['total_trades']} | "
        f"W/L: {state['wins']}/{state['losses']}"
    )
    
    # Open positions
    if state["positions"]:
        logger.info(f"\n📊 Open Positions ({len(state['positions'])}):")
        for pos in state["positions"]:
            bracket_str = ""
            if pos["bracket_type"] == "between":
                bracket_str = f"{pos['bracket_low']}-{pos['bracket_high']}°F"
            elif pos["bracket_type"] == "above":
                bracket_str = f">{pos['bracket_threshold']}°F"
            elif pos["bracket_type"] == "below":
                bracket_str = f"<{pos['bracket_threshold']}°F"
            
            upnl = pos.get("unrealized_pnl", 0)
            logger.info(
                f"  {pos['id']} {pos['city']} {bracket_str} {pos['side']} "
                f"@ {pos['entry_price']}¢ × {pos['contracts']} "
                f"(cost=${pos['entry_cost']:.2f}, uPnL=${upnl:+.2f}, "
                f"fair={pos['fair_value']:.0f}¢ edge={pos['edge']:+.0f}¢)"
            )
    
    # Top opportunities
    all_opps = []
    for city_key, opps in all_opportunities.items():
        for opp in opps:
            opp["city_key"] = city_key
            all_opps.append(opp)
    
    top_opps = sorted(all_opps, key=lambda x: -x["best_edge"])[:10]
    
    if top_opps:
        logger.info(f"\n🎯 Top 10 Edges:")
        for opp in top_opps:
            bracket_str = ""
            if opp["bracket_type"] == "between":
                bracket_str = f"{opp['bracket_low']}-{opp['bracket_high']}°F"
            elif opp["bracket_type"] == "above":
                bracket_str = f">{opp['bracket_threshold']}°F"
            elif opp["bracket_type"] == "below":
                bracket_str = f"<{opp['bracket_threshold']}°F"
            
            tradeable = "✅" if (opp["best_edge"] >= MIN_EDGE_CENTS and 
                                opp["spread"] <= MAX_SPREAD and 
                                opp["volume"] >= MIN_VOLUME) else "⬜"
            
            logger.info(
                f"  {tradeable} {opp['city_key']} {bracket_str} "
                f"{opp['best_side']} edge={opp['best_edge']:+.0f}¢ "
                f"(fair={opp['fair_value_yes']:.0f}¢ mkt={opp['yes_ask']}¢ "
                f"spread={opp['spread']}¢ vol={opp['volume']:,})"
            )
    
    logger.info("=" * 80)


# ============================================================================
# MAIN LOOP
# ============================================================================

shutdown = False

def signal_handler(sig, frame):
    global shutdown
    logger.info("🛑 Shutdown signal received, finishing current cycle...")
    shutdown = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    global shutdown
    
    # Parse duration
    duration_min = int(sys.argv[1]) if len(sys.argv) > 1 else 480  # default 8 hours
    end_time = time.time() + duration_min * 60
    
    logger.info("🌡️ ===== WEATHER PAPER TRADER STARTING =====")
    logger.info(f"Duration: {duration_min} minutes")
    logger.info(f"Cities: {len(CITIES)} ({', '.join(CITIES.keys())})")
    logger.info(f"Min edge: {MIN_EDGE_CENTS}¢ | Max position/city: ${MAX_POSITION_PER_CITY}")
    logger.info(f"Forecast interval: {FORECAST_INTERVAL}s | Kalshi interval: {KALSHI_INTERVAL}s")
    
    state = load_state()
    logger.info(f"State loaded: bankroll=${state['bankroll']:.2f}, trades={state['total_trades']}")
    
    last_forecast_time = 0
    last_kalshi_time = 0
    last_status_time = 0
    cycle = 0
    
    forecasts = {}
    
    while time.time() < end_time and not shutdown:
        cycle += 1
        now = time.time()
        
        try:
            # Fetch forecasts periodically
            if now - last_forecast_time >= FORECAST_INTERVAL or cycle == 1:
                logger.info("📡 Fetching weather forecasts...")
                forecasts = fetch_all_forecasts()
                state["forecasts"] = forecasts
                last_forecast_time = now
            
            # Fetch Kalshi prices more frequently
            if now - last_kalshi_time >= KALSHI_INTERVAL or cycle == 1:
                logger.info("📊 Fetching Kalshi markets...")
                all_markets = {}
                all_opportunities = {}
                
                for city_key in CITIES:
                    markets = fetch_kalshi_markets(city_key)
                    all_markets[city_key] = markets
                    
                    # Calculate fair values if we have forecast
                    forecast = forecasts.get(city_key)
                    if forecast and markets:
                        opportunities = calculate_fair_values(forecast, markets)
                        all_opportunities[city_key] = opportunities
                    else:
                        all_opportunities[city_key] = []
                    
                    # Rate limit: small delay between Kalshi calls
                    time.sleep(0.2)
                
                # Update position values
                update_position_values(state, all_markets)
                
                # Evaluate and execute paper trades
                new_trades = evaluate_trades(state, all_opportunities)
                if new_trades > 0:
                    logger.info(f"📝 Made {new_trades} new paper trades this cycle")
                
                # Check settlements
                settled = check_settlements(state)
                if settled > 0:
                    logger.info(f"🏁 Settled {settled} positions")
                
                last_kalshi_time = now
            
            # Print status every 15 minutes
            if now - last_status_time >= 900 or cycle == 1:
                print_status(state, all_opportunities if 'all_opportunities' in dir() else {})
                last_status_time = now
            
            # Save state every cycle
            save_state(state)
            
            # Sleep until next check
            sleep_time = min(KALSHI_INTERVAL, 60)
            for _ in range(int(sleep_time)):
                if shutdown or time.time() >= end_time:
                    break
                time.sleep(1)
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            logger.error(traceback.format_exc())
            time.sleep(30)
    
    # Final save
    save_state(state)
    
    # Final report
    logger.info("\n" + "=" * 80)
    logger.info("🏁 WEATHER PAPER TRADER FINAL REPORT")
    logger.info("=" * 80)
    logger.info(f"Runtime: {duration_min} minutes")
    logger.info(f"Bankroll: ${state['bankroll']:.2f}")
    logger.info(f"Total P&L: ${state['total_pnl']:+.2f}")
    logger.info(f"Total trades: {state['total_trades']}")
    logger.info(f"Win/Loss: {state['wins']}/{state['losses']}")
    if state['wins'] + state['losses'] > 0:
        logger.info(f"Win rate: {state['wins']/(state['wins']+state['losses'])*100:.1f}%")
    logger.info(f"Open positions: {len(state['positions'])}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
