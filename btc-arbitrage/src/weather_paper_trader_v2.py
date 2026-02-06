#!/usr/bin/env python3
"""
Weather Paper Trader V2 — Calibrated Model
============================================
Multi-source ensemble forecast → Normal distribution fair value → Paper trade when edge > threshold.

V2 Changes (from Day 1 results analysis):
  1. Station-specific bias corrections from calibration_v1.json
  2. Wider σ floors per city tier (was 1.5, now 3.0–8.0)
  3. City tiers: Tier 1 (reliable), Tier 2 (moderate), Tier 3 (skip)
  4. Kelly-inspired position sizing (tail bets get more, safety bets get less)
  5. METAR observation data for morning temp constraints
  6. Robust CLI settlement parser with manual overrides
  7. Fixed process lifetime (main loop properly tracks time)
  8. Forecast tracking for ongoing calibration

Settlement: NWS Climatological Report (CLI) from specific airport stations.
Strategy: Fetch forecasts from NWS + Open-Meteo + METAR, weight by accuracy,
          model temperature as Normal(μ, σ²), calculate bracket probabilities,
          paper trade when |fair_value - market_price| > min_edge.

Usage:
    python3 -u src/weather_paper_trader_v2.py [duration_minutes]
"""

import sys
import os
import json
import time
import math
import re
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

# ============================================================================
# V2: CALIBRATION DATA — Station-specific bias corrections
# ============================================================================
# Bias = (forecast - actual). Positive bias means forecast was too HIGH.
# Correction: adjusted = raw - bias  (subtract the bias to correct)
# NOTE: We ADD these corrections to move toward actual. If nws_bias=+9 for LAX,
# NWS was 9°F too HIGH → subtract 9 from NWS forecast.

CALIBRATION = {
    "LAX": {"nws_bias": 9, "om_bias": 3},
    "NYC": {"nws_bias": 3, "om_bias": 5},
    "CHI": {"nws_bias": -3, "om_bias": -4},
    "PHI": {"nws_bias": 7, "om_bias": 7},
    "BOS": {"nws_bias": 3, "om_bias": 3},
    "DEN": {"nws_bias": -12, "om_bias": -10},
    "MIA": {"nws_bias": 3, "om_bias": 0},
    "SFO": {"nws_bias": -1, "om_bias": -5},
    "DC":  {"nws_bias": 7, "om_bias": 8},
    "AUS": {"nws_bias": -5, "om_bias": -4},
    "SEA": {"nws_bias": 3, "om_bias": 0},
    "LV":  {"nws_bias": 1, "om_bias": -1},
    "NOLA": {"nws_bias": 7, "om_bias": 9},
    "PHX": {"nws_bias": 4, "om_bias": 2},
    "ATL": {"nws_bias": 11, "om_bias": 13},
    "MIN": {"nws_bias": -11, "om_bias": -9},
}

# ============================================================================
# V2: CITY TIERS — Controls which cities we trade and sizing limits
# ============================================================================
# Tier 1: Reliable forecasts (avg error ≤4°F) → full confidence
# Tier 2: Moderate forecasts (4-7°F) → reduced size
# Tier 3: Unreliable forecasts (>7°F) → SKIP (don't trade)

TIER_1_CITIES = {"BOS", "CHI", "LV", "MIA", "NYC", "PHX", "SEA", "SFO"}
TIER_2_CITIES = {"AUS", "LAX", "PHI"}
TIER_3_CITIES = {"ATL", "DC", "DEN", "MIN", "NOLA"}

CITY_TIER = {}
for c in TIER_1_CITIES:
    CITY_TIER[c] = 1
for c in TIER_2_CITIES:
    CITY_TIER[c] = 2
for c in TIER_3_CITIES:
    CITY_TIER[c] = 3

# Max position per city per day ($) by tier
MAX_POSITION_PER_CITY = {
    1: 60.0,   # Tier 1: up to $60
    2: 30.0,   # Tier 2: up to $30
    3: 0.0,    # Tier 3: don't trade
}

# ============================================================================
# V2: SIGMA FLOORS by tier
# ============================================================================
# Day 1 had MIN_SIGMA=1.5, only 25% within 1σ (should be 68%). Fix:

SIGMA_FLOOR = {
    1: 4.0,   # Reliable cities (was 3.0 — Day 1 showed 4-8°F forecast errors)
    2: 6.0,   # Moderate cities (was 5.0)
    3: 8.0,   # Unreliable cities (not traded, but for reference)
}

# ============================================================================
# V2: METAR STATION MAP — Airport ICAO codes for METAR lookups
# ============================================================================

METAR_STATIONS = {
    "LAX": "KLAX", "NYC": "KJFK", "CHI": "KORD", "PHI": "KPHL",
    "BOS": "KBOS", "DEN": "KDEN", "MIA": "KMIA", "SFO": "KSFO",
    "DC": "KDCA", "AUS": "KAUS", "SEA": "KSEA", "LV": "KLAS",
    "NOLA": "KMSY", "PHX": "KPHX", "ATL": "KATL", "MIN": "KMSP",
}

# ============================================================================
# V2: MANUAL SETTLEMENT OVERRIDES
# ============================================================================
# When CLI parsing fails, use these. Format: {"YYYY-MM-DD": {"CITY": temp}}

SETTLEMENT_OVERRIDES = {
    # Example: "2026-02-04": {"DEN": 52, "ATL": 61}
}

# ============================================================================
# CITY DATA — Airport coordinates + NWS grid points + station IDs
# ============================================================================

CITIES = {
    "LAX": {
        "name": "Los Angeles",
        "series": "KXHIGHLAX",
        "lat": 33.9425, "lon": -118.4081,
        "nws_wfo": "LOX", "nws_grid_x": 149, "nws_grid_y": 48,
        "station": "KLAX",
        "cli_wfo": "LOX", "cli_station": "LAX",
        "historical_mae": 2.5,
        "timezone_offset": -8,
        "predictability": "high",
    },
    "NYC": {
        "name": "New York",
        "series": "KXHIGHNY",
        "lat": 40.7831, "lon": -73.9712,
        "nws_wfo": "OKX", "nws_grid_x": 33, "nws_grid_y": 37,
        "station": "KNYC",
        "cli_wfo": "OKX", "cli_station": "NYC",
        "historical_mae": 2.8,
        "timezone_offset": -5,
        "predictability": "moderate",
    },
    "CHI": {
        "name": "Chicago",
        "series": "KXHIGHCHI",
        "lat": 41.7868, "lon": -87.7522,
        "nws_wfo": "LOT", "nws_grid_x": 76, "nws_grid_y": 73,
        "station": "KMDW",
        "cli_wfo": "LOT", "cli_station": "MDW",
        "historical_mae": 3.0,
        "timezone_offset": -6,
        "predictability": "moderate",
    },
    "PHI": {
        "name": "Philadelphia",
        "series": "KXHIGHPHIL",
        "lat": 39.8744, "lon": -75.2424,
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
        "lat": 42.3656, "lon": -71.0096,
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
        "lat": 39.8561, "lon": -104.6737,
        "nws_wfo": "BOU", "nws_grid_x": 62, "nws_grid_y": 60,
        "station": "KDEN",
        "cli_wfo": "BOU", "cli_station": "DEN",
        "historical_mae": 4.0,
        "timezone_offset": -7,
        "predictability": "low",
    },
    "MIA": {
        "name": "Miami",
        "series": "KXHIGHMIA",
        "lat": 25.7959, "lon": -80.2870,
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
        "lat": 37.6213, "lon": -122.3790,
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
        "lat": 38.8512, "lon": -77.0402,
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
        "lat": 30.1975, "lon": -97.6664,
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
        "lat": 47.4502, "lon": -122.3088,
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
        "lat": 36.0840, "lon": -115.1537,
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
        "lat": 29.9934, "lon": -90.2580,
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
        "lat": 33.4373, "lon": -112.0078,
        "nws_wfo": "PSR", "nws_grid_x": 159, "nws_grid_y": 56,
        "station": "KPHX",
        "cli_wfo": "PSR", "cli_station": "PHX",
        "historical_mae": 2.0,
        "timezone_offset": -7,
        "predictability": "high",
    },
    "ATL": {
        "name": "Atlanta",
        "series": "KXHIGHTATL",
        "lat": 33.6407, "lon": -84.4277,
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
        "lat": 44.8848, "lon": -93.2223,
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
RESEARCH_DIR = BASE_DIR / "research" / "weather"
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / "weather_paper_trader_v2.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("weather_trader_v2")

# ============================================================================
# STATE FILE
# ============================================================================

STATE_FILE = BASE_DIR / "weather_trader_v2_state.json"

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
        "positions": [],
        "settled_trades": [],
        "daily_exposure": {},
        "forecasts": {},
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_update": datetime.now(timezone.utc).isoformat(),
    }

def save_state(state):
    """Persist state to disk."""
    state["last_update"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

# ============================================================================
# V2: FORECAST HISTORY TRACKING
# ============================================================================

FORECAST_HISTORY_FILE = RESEARCH_DIR / "forecast_history.json"

def load_forecast_history():
    """Load accumulated forecast history."""
    if FORECAST_HISTORY_FILE.exists():
        try:
            with open(FORECAST_HISTORY_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"entries": []}

def save_forecast_entry(city_key, forecast_mu, forecast_sigma, sources, actual_high=None):
    """Log a forecast entry for ongoing calibration."""
    history = load_forecast_history()
    now = datetime.now(timezone.utc)
    today_et = (now + timedelta(hours=-5)).strftime("%Y-%m-%d")

    entry = {
        "city": city_key,
        "date": today_et,
        "forecast_mu": forecast_mu,
        "forecast_sigma": forecast_sigma,
        "sources": sources,
        "actual_high": actual_high,
        "timestamp": now.isoformat(),
    }

    # Avoid duplicate entries for same city+date (update instead)
    updated = False
    for i, e in enumerate(history["entries"]):
        if e["city"] == city_key and e["date"] == today_et:
            # Update with latest forecast (and actual if we have it)
            if actual_high is not None:
                entry["actual_high"] = actual_high
            elif e.get("actual_high") is not None:
                entry["actual_high"] = e["actual_high"]
            history["entries"][i] = entry
            updated = True
            break

    if not updated:
        history["entries"].append(entry)

    # Keep last 90 days of data (~1440 entries for 16 cities)
    if len(history["entries"]) > 1500:
        history["entries"] = history["entries"][-1500:]

    with open(FORECAST_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def update_forecast_actual(city_key, date_str, actual_high):
    """Update a forecast entry with the actual observed high."""
    history = load_forecast_history()
    for entry in history["entries"]:
        if entry["city"] == city_key and entry["date"] == date_str:
            entry["actual_high"] = actual_high
            break
    with open(FORECAST_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# ============================================================================
# V2: METAR OBSERVATION DATA
# ============================================================================

def fetch_metar_temp(city_key):
    """Fetch current temperature from METAR observation.

    Returns current temp in °F or None if unavailable.
    """
    station = METAR_STATIONS.get(city_key)
    if not station:
        return None

    url = f"https://aviationweather.gov/api/data/metar?ids={station}&format=json"

    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()
        if not data or not isinstance(data, list):
            return None

        # Get the most recent METAR observation
        obs = data[0]
        temp_c = obs.get("temp")
        if temp_c is None:
            # Try parsing from raw text
            raw = obs.get("rawOb", "")
            match = re.search(r'\b(M?\d{2})/(M?\d{2})\b', raw)
            if match:
                t = match.group(1)
                t = t.replace("M", "-")
                temp_c = float(t)
            else:
                return None

        temp_f = temp_c * 9 / 5 + 32
        return round(temp_f, 1)

    except Exception as e:
        logger.debug(f"METAR {city_key} error: {e}")
        return None

# ============================================================================
# WEATHER DATA FETCHING
# ============================================================================

def fetch_nws_forecast(city_key):
    """Fetch NWS grid forecast for a city. Returns predicted high temp (°F) or None."""
    city = CITIES[city_key]
    wfo = city["nws_wfo"]
    gx, gy = city["nws_grid_x"], city["nws_grid_y"]

    url = f"https://api.weather.gov/gridpoints/{wfo}/{gx},{gy}/forecast"
    headers = {"User-Agent": "KalshiWeatherTrader/2.0 (research@example.com)"}

    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            logger.warning(f"NWS {city_key}: HTTP {r.status_code}")
            return None

        data = r.json()
        periods = data.get("properties", {}).get("periods", [])

        if not periods:
            return None

        now_utc = datetime.now(timezone.utc)
        today_str = (now_utc + timedelta(hours=city["timezone_offset"])).strftime("%Y-%m-%d")

        for p in periods:
            start = p.get("startTime", "")[:10]
            if p.get("isDaytime") and start == today_str:
                temp = p.get("temperature")
                if temp is not None:
                    return float(temp)

        # Fallback: tomorrow
        tomorrow_str = (now_utc + timedelta(hours=city["timezone_offset"]) + timedelta(days=1)).strftime("%Y-%m-%d")
        for p in periods:
            start = p.get("startTime", "")[:10]
            if p.get("isDaytime") and start == tomorrow_str:
                temp = p.get("temperature")
                if temp is not None:
                    return float(temp)

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
    headers = {"User-Agent": "KalshiWeatherTrader/2.0 (research@example.com)"}

    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None

        data = r.json()
        periods = data.get("properties", {}).get("periods", [])

        target_date = today_str
        temps = []
        for p in periods:
            start = p.get("startTime", "")[:10]
            if start == target_date:
                temp = p.get("temperature")
                if temp is not None:
                    temps.append(float(temp))

        if not temps:
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

        now_utc = datetime.now(timezone.utc)
        today_et = (now_utc + timedelta(hours=-5)).strftime("%Y-%m-%d")
        tomorrow_et = (now_utc + timedelta(hours=-5) + timedelta(days=1)).strftime("%Y-%m-%d")

        result = {}
        for i, d in enumerate(dates):
            if d == today_et and i < len(highs) and highs[i] is not None:
                result["today"] = round(highs[i], 1)
            elif d == tomorrow_et and i < len(highs) and highs[i] is not None:
                result["tomorrow"] = round(highs[i], 1)

        hour_et = (now_utc + timedelta(hours=-5)).hour
        if hour_et >= 20:
            return result.get("tomorrow", result.get("today"))
        else:
            return result.get("today", result.get("tomorrow"))

    except Exception as e:
        logger.warning(f"Open-Meteo {city_key} error: {e}")
        return None


def fetch_all_forecasts():
    """Fetch forecasts from all sources for all cities.

    V2 improvements:
    - Apply station-specific bias corrections
    - Use tier-based sigma floors
    - Incorporate METAR morning temps as constraints
    - Skip Tier 3 cities entirely
    - Log forecasts for ongoing calibration
    """
    forecasts = {}

    for city_key in CITIES:
        tier = CITY_TIER.get(city_key, 3)

        # V2: Skip Tier 3 cities entirely — unreliable, don't waste API calls
        if tier == 3:
            logger.debug(f"⏭️ {city_key}: Tier 3 (unreliable), skipping")
            forecasts[city_key] = None
            continue

        nws_raw = fetch_nws_forecast(city_key)
        om_raw = fetch_openmeteo_forecast(city_key)
        metar_temp = fetch_metar_temp(city_key)

        # V2: Apply bias corrections
        cal = CALIBRATION.get(city_key, {"nws_bias": 0, "om_bias": 0})
        nws_adj = (nws_raw - cal["nws_bias"]) if nws_raw is not None else None
        om_adj = (om_raw - cal["om_bias"]) if om_raw is not None else None

        sources = {}
        raw_sources = {}
        if nws_adj is not None:
            sources["nws"] = nws_adj
            raw_sources["nws_raw"] = nws_raw
            raw_sources["nws_adj"] = nws_adj
        if om_adj is not None:
            sources["openmeteo"] = om_adj
            raw_sources["om_raw"] = om_raw
            raw_sources["om_adj"] = om_adj
        if metar_temp is not None:
            raw_sources["metar_current"] = metar_temp

        if not sources:
            logger.warning(f"⚠️ {city_key}: No forecast data available")
            forecasts[city_key] = None
            continue

        # Calculate ensemble mean
        temps = list(sources.values())
        city = CITIES[city_key]

        if len(temps) == 1:
            mu = temps[0]
        else:
            # Weight by assumed accuracy (NWS slightly better for US)
            nws_w = 1.0 / (2.5 ** 2) if "nws" in sources else 0
            om_w = 1.0 / (3.0 ** 2) if "openmeteo" in sources else 0
            total_w = nws_w + om_w

            mu = 0
            if nws_w > 0:
                mu += (nws_w / total_w) * sources["nws"]
            if om_w > 0:
                mu += (om_w / total_w) * sources["openmeteo"]

        # V2: METAR morning temp constraint
        # If current temp is already high, the afternoon high must be at least that
        if metar_temp is not None:
            now_utc = datetime.now(timezone.utc)
            local_hour = (now_utc + timedelta(hours=city["timezone_offset"])).hour
            # Morning observation (6 AM - 1 PM local): if temp already ≥ X, high must be ≥ X
            if 6 <= local_hour <= 13 and metar_temp > mu:
                logger.info(
                    f"🌡️ {city_key}: METAR constraint! Current={metar_temp:.0f}°F > "
                    f"forecast μ={mu:.1f}°F → adjusting μ up"
                )
                # Blend: afternoon high is typically 5-10°F above morning temp
                # But if forecast μ is below current temp, push μ up
                mu = max(mu, metar_temp + 2)  # high should be at least 2°F above current morning temp

        # V2: Wider sigma with tier-based floors
        source_spread = (max(temps) - min(temps)) if len(temps) > 1 else 0
        sigma_floor = SIGMA_FLOOR.get(tier, 8.0)
        sigma = max(source_spread, sigma_floor)

        forecasts[city_key] = {
            "mu": round(mu, 1),
            "sigma": round(sigma, 1),
            "sources": sources,
            "raw_sources": raw_sources,
            "source_count": len(sources),
            "tier": tier,
            "metar_temp": metar_temp,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # V2: Log forecast for calibration tracking
        save_forecast_entry(city_key, round(mu, 1), round(sigma, 1), raw_sources)

        logger.info(
            f"🌡️ {city_key} [T{tier}]: μ={mu:.1f}°F σ={sigma:.1f}°F "
            f"(NWS={nws_raw}→{nws_adj} OM={om_raw}→{om_adj} METAR={metar_temp})"
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

        parsed = []
        for m in markets:
            ticker = m.get("ticker", "")
            title = m.get("title", "")
            yes_bid = m.get("yes_bid", 0)
            yes_ask = m.get("yes_ask", 0)
            volume = m.get("volume", 0)
            close_time = m.get("close_time", "")

            bracket = parse_bracket(ticker, title)
            if bracket is None:
                continue

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
    """Parse bracket info from ticker and title."""
    title_lower = title.lower()

    parts = ticker.split("-")
    if len(parts) < 3:
        return None

    code = parts[-1]

    if code.startswith("T"):
        try:
            threshold = float(code[1:])
        except ValueError:
            return None

        if "<" in title_lower or "below" in title_lower:
            return {"type": "below", "threshold": threshold}
        else:
            return {"type": "above", "threshold": threshold}

    elif code.startswith("B"):
        try:
            midpoint = float(code[1:])
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

    date_part = parts[1]
    try:
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
    """Calculate fair value for each market bracket using Normal distribution."""
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
            fair_p = norm.cdf(high + 0.5, mu, sigma) - norm.cdf(low - 0.5, mu, sigma)

        elif bt == "above":
            threshold = m["bracket_threshold"]
            fair_p = 1 - norm.cdf(threshold + 0.5, mu, sigma)

        elif bt == "below":
            threshold = m["bracket_threshold"]
            fair_p = norm.cdf(threshold - 0.5, mu, sigma)
        else:
            continue

        fair_cents = round(fair_p * 100, 1)

        yes_edge = fair_cents - m["yes_ask"] if m["yes_ask"] > 0 else -999
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
# V2: KELLY-INSPIRED POSITION SIZING
# ============================================================================

def calculate_position_size(side, entry_price, fair_value, edge, city_key, remaining_budget):
    """Calculate position size using Kelly-inspired sizing.

    V2 sizing tiers:
    - YES bets ≤10¢ (tail bets): up to $40/trade — structural edge from Day 1
    - NO bets ≥80¢ (safety bets): max $15/trade — low leverage
    - Mid-range: standard $20/trade
    - Kelly fraction scales with edge
    """
    tier = CITY_TIER.get(city_key, 3)
    if tier == 3:
        return 0.0

    # Determine base size by bet type
    if side == "YES" and entry_price <= 10:
        # Tail bets — Day 1 showed these drive all profits
        base_size = 40.0
    elif side == "NO" and entry_price >= 80:
        # Safety bets — low leverage, cap smaller
        base_size = 15.0
    elif side == "YES" and entry_price <= 20:
        # Cheap-ish YES bets — still good
        base_size = 30.0
    else:
        # Mid-range bets
        base_size = 20.0

    # Tier 2 gets half the base size
    if tier == 2:
        base_size *= 0.5

    # Kelly fraction: scale by edge relative to potential payout
    if side == "YES":
        potential_payout = 100 - entry_price  # what we gain if we win
    else:
        potential_payout = 100 - entry_price

    if potential_payout > 0:
        kelly_fraction = min((fair_value - entry_price) / potential_payout, 0.25)
        kelly_fraction = max(kelly_fraction, 0.05)  # minimum 5% kelly
    else:
        kelly_fraction = 0.05

    # Scale base by kelly (kelly_fraction is 0.05–0.25)
    # Normalize: at kelly=0.10, use base_size; at 0.25 use 2.5x
    kelly_multiplier = kelly_fraction / 0.10
    kelly_multiplier = min(kelly_multiplier, 2.5)
    kelly_multiplier = max(kelly_multiplier, 0.5)

    position_dollars = base_size * kelly_multiplier
    position_dollars = min(position_dollars, remaining_budget)

    # Hard cap per city/tier
    max_city = MAX_POSITION_PER_CITY.get(tier, 0)
    position_dollars = min(position_dollars, max_city)

    return round(position_dollars, 2)


# ============================================================================
# PAPER TRADING ENGINE
# ============================================================================

def evaluate_trades(state, all_opportunities):
    """Evaluate and execute paper trades based on edge."""
    now = datetime.now(timezone.utc)
    today_str = (now + timedelta(hours=-5)).strftime("%Y-%m-%d")

    trades_made = 0

    for city_key, opps in all_opportunities.items():
        tier = CITY_TIER.get(city_key, 3)

        # V2: Skip Tier 3 cities
        if tier == 3:
            continue

        city_exposure_key = f"{city_key}_{today_str}"
        current_exposure = state.get("daily_exposure", {}).get(city_exposure_key, 0)
        max_exposure = MAX_POSITION_PER_CITY.get(tier, 0)

        for opp in opps:
            # Filter: minimum edge
            if opp["best_edge"] < MIN_EDGE_CENTS:
                continue

            # Filter: spread too wide
            if opp["spread"] > MAX_SPREAD:
                continue

            # Filter: volume too low
            if opp["volume"] < MIN_VOLUME:
                continue

            # Filter: already at max exposure for this city
            if current_exposure >= max_exposure:
                break  # no more trades for this city

            # Filter: already have a position in this market
            existing = [p for p in state["positions"] if p["ticker"] == opp["ticker"]]
            if existing:
                continue

            # Determine trade details
            side = opp["best_side"]
            if side == "YES":
                entry_price = opp["yes_ask"]
                fair_value = opp["fair_value_yes"]
                edge = opp["yes_edge"]
            else:
                entry_price = opp["no_ask"]
                fair_value = opp["fair_value_no"]
                edge = opp["no_edge"]

            if entry_price <= 0 or entry_price >= 100:
                continue

            # Day 1 Fix: Don't trade contracts priced below 10¢ (fees eat the edge)
            if entry_price < 10:
                logger.debug(f"  ⏭️ {city_key} {opp['ticker']}: price {entry_price}¢ < 10¢ min, skipping (fees eat edge)")
                continue

            # Day 1 Fix: Don't trade contracts priced above 90¢ (too expensive, low upside)
            if entry_price > 90:
                logger.debug(f"  ⏭️ {city_key} {opp['ticker']}: price {entry_price}¢ > 90¢ max, skipping (low upside)")
                continue

            # Day 1 Fix: Fee-aware edge calculation
            # Only trade when edge - (2 * fee_per_contract / contract_price) > 8¢
            fee_drag_cents = (2 * FEE_PER_SIDE) / (entry_price / 100) if entry_price > 0 else 999
            net_edge = edge - fee_drag_cents
            if net_edge < 8:
                logger.debug(f"  ⏭️ {city_key}: net edge {net_edge:.1f}¢ < 8¢ after fees (raw={edge:.1f}¢, fee_drag={fee_drag_cents:.1f}¢)")
                continue

            # V2: Kelly-inspired position sizing
            remaining_budget = max_exposure - current_exposure
            position_dollars = calculate_position_size(
                side, entry_price, fair_value, edge, city_key, remaining_budget
            )

            if position_dollars < 1.0:
                continue

            # Calculate contracts
            contracts = int(position_dollars / (entry_price / 100))
            if contracts < 1:
                continue

            # Day 1 Fix: Cap max contracts per trade at 100 (was buying 2000+ penny contracts)
            if contracts > 100:
                logger.info(f"  📉 {city_key} {opp['ticker']}: capped contracts {contracts} → 100")
                contracts = 100

            actual_cost = contracts * (entry_price / 100)
            fee = contracts * FEE_PER_SIDE / 100

            position = {
                "id": f"W2-{state['total_trades'] + 1:04d}",
                "city": city_key,
                "tier": tier,
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

            if "daily_exposure" not in state:
                state["daily_exposure"] = {}
            state["daily_exposure"][city_exposure_key] = round(current_exposure, 2)

            trades_made += 1

            bracket_str = ""
            if opp["bracket_type"] == "between":
                bracket_str = f"{opp['bracket_low']}-{opp['bracket_high']}°F"
            elif opp["bracket_type"] == "above":
                bracket_str = f">{opp['bracket_threshold']}°F"
            elif opp["bracket_type"] == "below":
                bracket_str = f"<{opp['bracket_threshold']}°F"

            logger.info(
                f"📝 PAPER TRADE {position['id']}: {city_key}[T{tier}] {bracket_str} "
                f"{side} @ {entry_price}¢ × {contracts} contracts "
                f"(cost=${actual_cost:.2f}, fair={fair_value:.0f}¢, edge={edge:+.0f}¢, "
                f"μ={opp['forecast_mu']:.0f}°F σ={opp['forecast_sigma']:.1f})"
            )

    return trades_made


# ============================================================================
# V2: ROBUST SETTLEMENT CHECKING
# ============================================================================

def fetch_nws_cli_high(city, market_date):
    """Fetch actual high temperature from NWS CLI product.

    V2: More robust parsing:
    - Look for "YESTERDAY" section header, then "MAXIMUM" line
    - Parse: "MAXIMUM    87R  2:21 PM  84    2001  66     21       64"
    - First number after "MAXIMUM" is the actual high (strip 'R' suffix)
    - Fall back to manual overrides
    """
    city_key_for_override = None
    for ck, cd in CITIES.items():
        if cd.get("cli_station") == city.get("cli_station"):
            city_key_for_override = ck
            break

    # Check manual override first
    if city_key_for_override and market_date in SETTLEMENT_OVERRIDES:
        override = SETTLEMENT_OVERRIDES[market_date].get(city_key_for_override)
        if override is not None:
            logger.info(f"Using manual override for {city_key_for_override} {market_date}: {override}°F")
            return override

    wfo = city["cli_wfo"]
    station = city["cli_station"]

    url = f"https://forecast.weather.gov/product.php?site={wfo}&product=CLI&issuedby={station}"

    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return None

        text = r.text
        lines = text.split("\n")

        # V2: Robust parsing strategy
        # 1. Find "YESTERDAY" or "WEATHER" section
        # 2. Find "MAXIMUM" line after it
        # 3. Extract first number (strip R/r suffix)

        in_temp_section = False
        for i, line in enumerate(lines):
            stripped = line.strip().upper()

            # Enter temperature section
            if "TEMPERATURE" in stripped and ("(F)" in stripped or "(°F)" in stripped or "DEGREES" in stripped):
                in_temp_section = True
                continue

            # Also look for the section after "YESTERDAY" or "WEATHER DATA"
            if "YESTERDAY" in stripped or "WEATHER DATA" in stripped:
                in_temp_section = True
                continue

            if in_temp_section and "MAXIMUM" in stripped and "MINIMUM" not in stripped:
                # Parse: "MAXIMUM    87R  2:21 PM  84    2001  66     21       64"
                # Split and find first number-like token after "MAXIMUM"
                parts = stripped.split()
                for j, p in enumerate(parts):
                    if p == "MAXIMUM" or p == "MAX":
                        # Look at subsequent parts for a number
                        for k in range(j + 1, len(parts)):
                            # Strip trailing R (record indicator), M (missing)
                            cleaned = parts[k].rstrip("R").rstrip("r")
                            # Handle negative temps
                            try:
                                val = int(cleaned)
                                if -60 < val < 150:
                                    return val
                            except ValueError:
                                # Might be time like "2:21", skip
                                continue
                break  # Only try the first MAXIMUM line

        # Fallback: broader search for any line with MAXIMUM and a number
        for line in lines:
            stripped = line.strip().upper()
            if "MAXIMUM" in stripped and "TEMPERATURE" not in stripped:
                parts = stripped.split()
                for j, p in enumerate(parts):
                    if "MAXIMUM" in p or "MAX" == p:
                        for k in range(j + 1, len(parts)):
                            cleaned = parts[k].rstrip("R").rstrip("r")
                            try:
                                val = int(cleaned)
                                if -60 < val < 150:
                                    return val
                            except ValueError:
                                continue

        return None

    except Exception as e:
        logger.warning(f"CLI fetch error for {station}: {e}")
        return None


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
        settle_date = datetime.strptime(market_date, "%Y-%m-%d") + timedelta(days=1)
        settle_time = settle_date.replace(hour=13, minute=0)  # 8 AM ET = 13 UTC
        settle_time = settle_time.replace(tzinfo=timezone.utc)

        if now < settle_time:
            continue

        city = CITIES.get(pos["city"])
        if not city:
            continue

        actual_high = fetch_nws_cli_high(city, market_date)

        if actual_high is None:
            logger.debug(f"CLI not yet available for {pos['city']} {market_date}")
            continue

        # V2: Update forecast history with actual
        update_forecast_actual(pos["city"], market_date, actual_high)

        # Determine win/loss
        won = False
        if pos["bracket_type"] == "between":
            actual_in_bracket = pos["bracket_low"] <= actual_high <= pos["bracket_high"]
            won = actual_in_bracket if pos["side"] == "YES" else not actual_in_bracket
        elif pos["bracket_type"] == "above":
            actual_above = actual_high > pos["bracket_threshold"]
            won = actual_above if pos["side"] == "YES" else not actual_above
        elif pos["bracket_type"] == "below":
            actual_below = actual_high < pos["bracket_threshold"]
            won = actual_below if pos["side"] == "YES" else not actual_below

        # Calculate P&L
        if won:
            payout = pos["contracts"] * 1.00
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

        state["settled_trades"].append(dict(pos))
        settled += 1

        emoji = "✅" if won else "❌"
        logger.info(
            f"{emoji} SETTLED {pos['id']}: {pos['city']}[T{pos.get('tier', '?')}] "
            f"actual={actual_high}°F forecast_μ={pos['forecast_mu']:.0f}°F "
            f"err={abs(actual_high - pos['forecast_mu']):.0f}°F "
            f"{'WON' if won else 'LOST'} P&L=${pnl:+.2f} "
            f"(total: ${state['total_pnl']:+.2f})"
        )

    # Remove settled positions
    state["positions"] = [p for p in state["positions"] if p["status"] == "open"]

    return settled


# ============================================================================
# POSITION MONITORING
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
    logger.info(f"🌡️ WEATHER PAPER TRADER V2 STATUS — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info("=" * 80)

    # Bankroll & P&L
    wr_str = ""
    total = state['wins'] + state['losses']
    if total > 0:
        wr_str = f" WR={state['wins']/total*100:.0f}%"
    logger.info(
        f"💰 Bankroll: ${state['bankroll']:.2f} | "
        f"P&L: ${state['total_pnl']:+.2f} | "
        f"Trades: {state['total_trades']} | "
        f"W/L: {state['wins']}/{state['losses']}{wr_str}"
    )

    # V2: Show tier breakdown
    logger.info(
        f"📋 Trading tiers: T1={','.join(sorted(TIER_1_CITIES))} | "
        f"T2={','.join(sorted(TIER_2_CITIES))} | "
        f"T3(skip)={','.join(sorted(TIER_3_CITIES))}"
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
                f"  {pos['id']} {pos['city']}[T{pos.get('tier', '?')}] {bracket_str} {pos['side']} "
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

            tier = CITY_TIER.get(opp["city_key"], 3)
            tradeable = "✅" if (opp["best_edge"] >= MIN_EDGE_CENTS and
                                opp["spread"] <= MAX_SPREAD and
                                opp["volume"] >= MIN_VOLUME and
                                tier <= 2) else "⬜"

            logger.info(
                f"  {tradeable} {opp['city_key']}[T{tier}] {bracket_str} "
                f"{opp['best_side']} edge={opp['best_edge']:+.0f}¢ "
                f"(fair={opp['fair_value_yes']:.0f}¢ mkt={opp['yes_ask']}¢ "
                f"spread={opp['spread']}¢ vol={opp['volume']:,})"
            )

    logger.info("=" * 80)


# ============================================================================
# MAIN LOOP — V2: Fixed process lifetime
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
    duration_min = int(sys.argv[1]) if len(sys.argv) > 1 else 480
    start_time = time.time()
    end_time = start_time + duration_min * 60

    logger.info("🌡️ ===== WEATHER PAPER TRADER V2 (CALIBRATED) STARTING =====")
    logger.info(f"Duration: {duration_min} minutes ({duration_min/60:.1f} hours)")
    logger.info(f"End time: {datetime.fromtimestamp(end_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"Trading cities: {len(TIER_1_CITIES) + len(TIER_2_CITIES)} "
                f"(T1: {len(TIER_1_CITIES)}, T2: {len(TIER_2_CITIES)}, T3 skipped: {len(TIER_3_CITIES)})")
    logger.info(f"Min edge: {MIN_EDGE_CENTS}¢")
    logger.info(f"Max position/city: T1=${MAX_POSITION_PER_CITY[1]}, T2=${MAX_POSITION_PER_CITY[2]}")
    logger.info(f"Sigma floors: T1={SIGMA_FLOOR[1]}°F, T2={SIGMA_FLOOR[2]}°F")
    logger.info(f"Calibration offsets loaded for {len(CALIBRATION)} cities")
    logger.info(f"Forecast interval: {FORECAST_INTERVAL}s | Kalshi interval: {KALSHI_INTERVAL}s")

    state = load_state()
    logger.info(f"State loaded: bankroll=${state['bankroll']:.2f}, trades={state['total_trades']}")

    last_forecast_time = 0
    last_kalshi_time = 0
    last_status_time = 0
    cycle = 0
    all_opportunities = {}

    forecasts = {}

    while not shutdown:
        # V2: Properly check elapsed time against end_time
        now = time.time()
        remaining = end_time - now
        if remaining <= 0:
            logger.info(f"⏰ Duration of {duration_min} minutes reached, shutting down.")
            break

        cycle += 1

        try:
            # Fetch forecasts periodically
            if now - last_forecast_time >= FORECAST_INTERVAL or cycle == 1:
                logger.info(f"📡 Fetching weather forecasts... (cycle {cycle}, "
                            f"{remaining/60:.0f} min remaining)")
                forecasts = fetch_all_forecasts()
                state["forecasts"] = forecasts
                last_forecast_time = now

            # Fetch Kalshi prices more frequently
            if now - last_kalshi_time >= KALSHI_INTERVAL or cycle == 1:
                logger.info("📊 Fetching Kalshi markets...")
                all_markets = {}
                all_opportunities = {}

                for city_key in CITIES:
                    tier = CITY_TIER.get(city_key, 3)
                    if tier == 3:
                        all_markets[city_key] = []
                        all_opportunities[city_key] = []
                        continue

                    markets = fetch_kalshi_markets(city_key)
                    all_markets[city_key] = markets

                    forecast = forecasts.get(city_key)
                    if forecast and markets:
                        opportunities = calculate_fair_values(forecast, markets)
                        all_opportunities[city_key] = opportunities
                    else:
                        all_opportunities[city_key] = []

                    time.sleep(0.2)

                update_position_values(state, all_markets)

                new_trades = evaluate_trades(state, all_opportunities)
                if new_trades > 0:
                    logger.info(f"📝 Made {new_trades} new paper trades this cycle")

                settled = check_settlements(state)
                if settled > 0:
                    logger.info(f"🏁 Settled {settled} positions")

                last_kalshi_time = now

            # Print status every 15 minutes
            if now - last_status_time >= 900 or cycle == 1:
                print_status(state, all_opportunities)
                last_status_time = now

            save_state(state)

            # V2: Fixed sleep loop — properly checks both shutdown and time
            sleep_target = min(KALSHI_INTERVAL, 60)
            sleep_end = time.time() + sleep_target
            while time.time() < sleep_end:
                if shutdown:
                    break
                if time.time() >= end_time:
                    break
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received")
            break
        except Exception as e:
            logger.error(f"Main loop error (cycle {cycle}): {e}")
            logger.error(traceback.format_exc())
            time.sleep(30)

    # Final save
    save_state(state)

    # Final report
    elapsed = (time.time() - start_time) / 60
    logger.info("\n" + "=" * 80)
    logger.info("🏁 WEATHER PAPER TRADER V2 FINAL REPORT")
    logger.info("=" * 80)
    logger.info(f"Runtime: {elapsed:.0f} minutes (target: {duration_min})")
    logger.info(f"Cycles: {cycle}")
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
