#!/usr/bin/env python3
"""
NBA Sharp Line Detection — Paper Trading Bot
=============================================
Compares Kalshi NBA moneyline prices against sportsbook consensus (ESPN/DraftKings).
When Kalshi price diverges >5¢ from implied sportsbook probability, paper trade the mispriced side.

Strategy:
  1. Fetch Kalshi NBA moneyline markets (KXNBAGAME-*)
  2. Fetch sportsbook odds from ESPN (DraftKings) for same games
  3. Convert American odds → implied probability, remove vig
  4. Compare Kalshi price vs fair value
  5. If |divergence| > MIN_EDGE → paper trade underpriced side
  6. Size via Kelly criterion, capped at $50/game
  7. Track positions until game settlement

Run loop: Every 30 min during NBA hours (18:00-04:00 UTC), every 2h outside.

Usage:
    python3 -u src/nba_paper_trader.py
"""

import sys
import os
import json
import time
import math
import logging
import signal
import traceback
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

# Minimum edge (cents) to trigger a paper trade
MIN_EDGE_CENTS = 5

# Paper trading bankroll
STARTING_BANKROLL = 1000.0

# Max position per game ($)
MAX_POSITION_PER_GAME = 50.0

# Max total exposure ($)
MAX_TOTAL_EXPOSURE = 500.0

# Scan intervals (seconds)
SCAN_INTERVAL_ACTIVE = 1800     # 30 min during NBA hours
SCAN_INTERVAL_INACTIVE = 7200   # 2 hours outside NBA hours

# NBA active hours (UTC): 18:00 - 04:00 (roughly 1pm-11pm ET)
NBA_START_HOUR_UTC = 17   # Start scanning a bit earlier
NBA_END_HOUR_UTC = 5      # End a bit later

# Fee per contract per side (cents)
FEE_PER_SIDE = 2  # ~2¢ per side, 4¢ round trip

# Minimum volume to consider a market tradeable
MIN_VOLUME = 50

# Maximum spread (cents) to consider a market tradeable  
MAX_SPREAD = 8

# Kelly fraction (quarter-Kelly for safety)
KELLY_FRACTION = 0.25

# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path("/home/clawdbot/clawd/btc-arbitrage")
STATE_FILE = BASE_DIR / "nba_trader_state.json"
LOG_FILE = BASE_DIR / "logs" / "nba_trader_live.log"

# Ensure directories
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger("nba_trader")
logger.setLevel(logging.DEBUG)

# Console handler
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(ch)

# File handler
fh = logging.FileHandler(str(LOG_FILE), mode="a")
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(fh)

# ============================================================================
# SIGNAL HANDLING
# ============================================================================

shutdown_requested = False

def signal_handler(sig, frame):
    global shutdown_requested
    sig_name = signal.Signals(sig).name
    logger.info(f"Received {sig_name} — shutting down gracefully...")
    shutdown_requested = True

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# ============================================================================
# NBA TEAM MAPPING — ESPN abbreviations ↔ Kalshi abbreviations
# ============================================================================

# ESPN uses slightly different abbreviations than Kalshi in some cases
# Map ESPN abbr → Kalshi abbr
ESPN_TO_KALSHI = {
    "ATL": "ATL", "BOS": "BOS", "BKN": "BKN", "CHA": "CHA",
    "CHI": "CHI", "CLE": "CLE", "DAL": "DAL", "DEN": "DEN",
    "DET": "DET", "GS": "GSW", "HOU": "HOU", "IND": "IND",
    "LAC": "LAC", "LAL": "LAL", "MEM": "MEM", "MIA": "MIA",
    "MIL": "MIL", "MIN": "MIN", "NO": "NOP", "NY": "NYK",
    "OKC": "OKC", "ORL": "ORL", "PHI": "PHI", "PHX": "PHX",
    "POR": "POR", "SA": "SAS", "SAC": "SAC", "TOR": "TOR",
    "UTAH": "UTA", "WSH": "WAS",
}

# Reverse mapping
KALSHI_TO_ESPN = {v: k for k, v in ESPN_TO_KALSHI.items()}

# yes_sub_title city/name → Kalshi abbreviation
CITY_TO_KALSHI = {
    "atlanta": "ATL", "boston": "BOS", "brooklyn": "BKN", "charlotte": "CHA",
    "chicago": "CHI", "cleveland": "CLE", "dallas": "DAL", "denver": "DEN",
    "detroit": "DET", "golden state": "GSW", "houston": "HOU", "indiana": "IND",
    "los angeles c": "LAC", "los angeles l": "LAL", "memphis": "MEM", "miami": "MIA",
    "milwaukee": "MIL", "minnesota": "MIN", "new orleans": "NOP", "new york": "NYK",
    "oklahoma city": "OKC", "orlando": "ORL", "philadelphia": "PHI", "phoenix": "PHX",
    "portland": "POR", "san antonio": "SAS", "sacramento": "SAC", "toronto": "TOR",
    "utah": "UTA", "washington": "WAS",
}

# Full team names for display
TEAM_NAMES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "LA Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAS": "San Antonio Spurs", "SAC": "Sacramento Kings",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}

# ============================================================================
# STATE MANAGEMENT
# ============================================================================

def load_state():
    """Load trader state from disk."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Corrupted state file, starting fresh")
    
    return {
        "bankroll": STARTING_BANKROLL,
        "total_pnl": 0.0,
        "positions": [],       # Open positions
        "settled": [],         # Settled trades (history)
        "signals_seen": 0,
        "trades_taken": 0,
        "wins": 0,
        "losses": 0,
        "last_scan": None,
        "daily_stats": {},
    }

def save_state(state):
    """Persist state to disk."""
    try:
        tmp = str(STATE_FILE) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2, default=str)
        os.replace(tmp, str(STATE_FILE))
    except IOError as e:
        logger.error(f"Failed to save state: {e}")

# ============================================================================
# KALSHI API
# ============================================================================

KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"

def fetch_kalshi_nba_markets():
    """Fetch all open NBA moneyline markets from Kalshi."""
    markets = []
    cursor = None
    
    for _ in range(10):  # Max 10 pages
        params = {
            "series_ticker": "KXNBAGAME",
            "limit": 100,
            "status": "open",
        }
        if cursor:
            params["cursor"] = cursor
            
        try:
            r = requests.get(f"{KALSHI_BASE}/markets", params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            page_markets = data.get("markets", [])
            markets.extend(page_markets)
            
            cursor = data.get("cursor")
            if not cursor or len(page_markets) == 0:
                break
                
        except Exception as e:
            logger.error(f"Kalshi API error: {e}")
            break
    
    logger.info(f"Fetched {len(markets)} Kalshi NBA markets")
    return markets

def parse_kalshi_markets(markets):
    """
    Group Kalshi markets by game event and extract relevant info.
    Returns dict: event_ticker -> game_info
    """
    games = {}
    
    for m in markets:
        event = m.get("event_ticker", "")
        ticker = m.get("ticker", "")
        
        if not event.startswith("KXNBAGAME-"):
            continue
            
        # Parse event ticker: KXNBAGAME-26FEB06MEMPOR
        # Team abbreviations are always 3 chars in Kalshi NBA tickers
        event_match = re.match(r"KXNBAGAME-(\d{2})([A-Z]{3})(\d{2})([A-Z]{3})([A-Z]{3})", event)
        if not event_match:
            continue
            
        yy, mon, dd, away_abbr, home_abbr = event_match.groups()
        
        # Parse the market suffix to identify which team this YES contract is for
        # Ticker: KXNBAGAME-26FEB06MEMPOR-POR → suffix = POR
        yes_sub = m.get("yes_sub_title", "")
        
        # Resolve team abbreviation from suffix or yes_sub_title
        suffix = ticker.split("-")[-1] if "-" in ticker else ""
        team_abbr = suffix  # The suffix IS the Kalshi team abbreviation
        
        # Also resolve from city name as backup
        if not team_abbr or len(team_abbr) > 3:
            city_key = yes_sub.strip().lower()
            team_abbr = CITY_TO_KALSHI.get(city_key, suffix)
        
        if event not in games:
            games[event] = {
                "event_ticker": event,
                "away_kalshi": away_abbr,
                "home_kalshi": home_abbr,
                "date_str": f"20{yy}-{_month_to_num(mon)}-{dd}",
                "title": m.get("title", ""),
                "markets": {},
                "expected_expiration": m.get("expected_expiration_time", ""),
            }
        
        # Extract price info
        games[event]["markets"][ticker] = {
            "ticker": ticker,
            "yes_team": yes_sub,
            "team_abbr": team_abbr,  # Resolved Kalshi abbreviation
            "yes_bid": m.get("yes_bid", 0),
            "yes_ask": m.get("yes_ask", 0),
            "no_bid": m.get("no_bid", 0),
            "no_ask": m.get("no_ask", 0),
            "last_price": m.get("last_price", 0),
            "volume": m.get("volume", 0),
            "status": m.get("status", ""),
        }
    
    return games

def _month_to_num(mon):
    """Convert 3-letter month to 2-digit number."""
    months = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
    }
    return months.get(mon, "01")

# ============================================================================
# ESPN / SPORTSBOOK ODDS
# ============================================================================

def fetch_espn_games(date_str):
    """
    Fetch NBA games and DraftKings odds from ESPN for a given date.
    date_str: YYYYMMDD
    Returns list of game dicts with odds.
    """
    try:
        r = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
            params={"dates": date_str},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.error(f"ESPN API error for {date_str}: {e}")
        return []
    
    games = []
    for event in data.get("events", []):
        comp = event["competitions"][0]
        
        # Get teams
        away = home = None
        for c in comp["competitors"]:
            if c["homeAway"] == "away":
                away = c
            else:
                home = c
        
        if not away or not home:
            continue
        
        game_info = {
            "espn_id": event["id"],
            "date": event["date"],
            "status": comp["status"]["type"]["description"],
            "status_id": comp["status"]["type"]["id"],
            "away_espn": away["team"]["abbreviation"],
            "home_espn": home["team"]["abbreviation"],
            "away_name": away["team"]["displayName"],
            "home_name": home["team"]["displayName"],
            "away_score": away.get("score", "0"),
            "home_score": home.get("score", "0"),
            "odds": None,
        }
        
        # Fetch odds from ESPN's detailed odds endpoint
        try:
            odds_r = requests.get(
                f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{event['id']}/competitions/{event['id']}/odds",
                timeout=10,
            )
            if odds_r.status_code == 200:
                odds_data = odds_r.json()
                for item in odds_data.get("items", []):
                    provider = item.get("provider", {}).get("name", "")
                    if "Draft Kings" in provider or "DraftKings" in provider:
                        away_ml = item.get("awayTeamOdds", {}).get("moneyLine")
                        home_ml = item.get("homeTeamOdds", {}).get("moneyLine")
                        spread = item.get("spread")
                        over_under = item.get("overUnder")
                        
                        if away_ml is not None and home_ml is not None:
                            game_info["odds"] = {
                                "provider": provider,
                                "away_ml": int(away_ml),
                                "home_ml": int(home_ml),
                                "spread": spread,
                                "over_under": over_under,
                            }
                        break
        except Exception as e:
            logger.debug(f"Odds fetch failed for event {event['id']}: {e}")
        
        games.append(game_info)
    
    return games

# ============================================================================
# ODDS CONVERSION & FAIR VALUE
# ============================================================================

def american_to_implied_prob(american_odds):
    """Convert American odds to implied probability (includes vig)."""
    if american_odds is None:
        return None
    if american_odds > 0:
        return 100.0 / (american_odds + 100.0)
    elif american_odds < 0:
        return abs(american_odds) / (abs(american_odds) + 100.0)
    else:
        return 0.5

def devig_probabilities(prob_home, prob_away):
    """
    Remove vig from implied probabilities.
    Normalize so probabilities sum to 1.0.
    """
    total = prob_home + prob_away
    if total == 0:
        return 0.5, 0.5
    return prob_home / total, prob_away / total

def calculate_fair_value(espn_game):
    """
    Calculate fair value probabilities from sportsbook odds.
    Returns (home_fair, away_fair) or None if no odds available.
    """
    if not espn_game.get("odds"):
        return None
    
    odds = espn_game["odds"]
    home_implied = american_to_implied_prob(odds["home_ml"])
    away_implied = american_to_implied_prob(odds["away_ml"])
    
    if home_implied is None or away_implied is None:
        return None
    
    home_fair, away_fair = devig_probabilities(home_implied, away_implied)
    return home_fair, away_fair

# ============================================================================
# KELLY CRITERION
# ============================================================================

def kelly_size(fair_prob, market_price_cents, bankroll, fraction=KELLY_FRACTION):
    """
    Calculate Kelly-criterion position size.
    
    fair_prob: our estimated true probability (0-1)
    market_price_cents: Kalshi price in cents (0-100)
    bankroll: current bankroll
    fraction: Kelly fraction (0.25 = quarter Kelly)
    
    Returns position size in dollars.
    """
    market_price = market_price_cents / 100.0
    
    if market_price <= 0 or market_price >= 1:
        return 0
    
    # Odds we get: payout / cost
    # If buying YES at price p, we pay p and win (1-p) if correct
    b = (1.0 - market_price) / market_price  # odds ratio
    p = fair_prob
    q = 1.0 - p
    
    # Kelly formula: f* = (bp - q) / b
    f_star = (b * p - q) / b
    
    if f_star <= 0:
        return 0
    
    # Apply fraction and cap
    position = bankroll * f_star * fraction
    position = min(position, MAX_POSITION_PER_GAME)
    position = max(position, 0)
    
    return round(position, 2)

# ============================================================================
# GAME MATCHING — Match Kalshi events to ESPN games
# ============================================================================

def match_games(kalshi_games, espn_games):
    """
    Match Kalshi game events to ESPN games by team abbreviations.
    Returns list of matched pairs.
    """
    matched = []
    
    for event_ticker, kg in kalshi_games.items():
        away_k = kg["away_kalshi"]
        home_k = kg["home_kalshi"]
        
        for eg in espn_games:
            away_e = ESPN_TO_KALSHI.get(eg["away_espn"], eg["away_espn"])
            home_e = ESPN_TO_KALSHI.get(eg["home_espn"], eg["home_espn"])
            
            # Match: same away team and same home team
            if away_k == away_e and home_k == home_e:
                matched.append({
                    "kalshi": kg,
                    "espn": eg,
                    "event_ticker": event_ticker,
                })
                break
            # Also try reversed (shouldn't happen but just in case)
            elif away_k == home_e and home_k == away_e:
                matched.append({
                    "kalshi": kg,
                    "espn": eg,
                    "event_ticker": event_ticker,
                })
                break
    
    return matched

# ============================================================================
# SIGNAL DETECTION
# ============================================================================

def detect_signals(matched_games, state):
    """
    Detect trading signals: where Kalshi price diverges from fair value.
    Returns list of trade signals.
    """
    signals = []
    
    for match in matched_games:
        kg = match["kalshi"]
        eg = match["espn"]
        
        # Skip settled games
        if eg["status"] == "Final":
            continue
        
        # Get fair value from sportsbook
        fair = calculate_fair_value(eg)
        if not fair:
            continue
        
        home_fair, away_fair = fair
        
        # Find Kalshi markets for each team
        for ticker, mkt in kg["markets"].items():
            if mkt["status"] != "active":
                continue
            
            # Use team_abbr (from market suffix) to identify home/away
            team_abbr = mkt.get("team_abbr", "")
            
            if team_abbr == kg["home_kalshi"]:
                team_fair = home_fair
                team_label = f"{team_abbr} (home)"
            elif team_abbr == kg["away_kalshi"]:
                team_fair = away_fair
                team_label = f"{team_abbr} (away)"
            else:
                # Fallback: try city name matching
                yes_sub = mkt.get("yes_team", "").strip().lower()
                resolved = CITY_TO_KALSHI.get(yes_sub, "")
                if resolved == kg["home_kalshi"]:
                    team_fair = home_fair
                    team_label = f"{resolved} (home)"
                elif resolved == kg["away_kalshi"]:
                    team_fair = away_fair
                    team_label = f"{resolved} (away)"
                else:
                    logger.debug(f"Cannot identify team for {ticker} team_abbr={team_abbr} yes_sub={yes_sub}")
                    continue
            
            # Use midpoint of bid/ask as market price
            yes_bid = mkt["yes_bid"]
            yes_ask = mkt["yes_ask"]
            
            if yes_bid <= 0 or yes_ask <= 0:
                continue
            
            kalshi_mid = (yes_bid + yes_ask) / 2.0
            fair_cents = team_fair * 100.0
            
            # Calculate edge
            edge = fair_cents - kalshi_mid  # Positive = Kalshi is cheap (buy YES)
            
            spread = yes_ask - yes_bid
            volume = mkt["volume"]
            
            # Check if tradeable
            if volume < MIN_VOLUME:
                logger.debug(f"  {ticker}: volume {volume} < {MIN_VOLUME}, skip")
                continue
            if spread > MAX_SPREAD:
                logger.debug(f"  {ticker}: spread {spread}¢ > {MAX_SPREAD}¢, skip")
                continue
            
            if abs(edge) >= MIN_EDGE_CENTS:
                direction = "BUY_YES" if edge > 0 else "BUY_NO"
                entry_price = yes_ask if edge > 0 else (100 - yes_bid)  # Buy at ask
                
                signal = {
                    "ticker": ticker,
                    "event_ticker": match["event_ticker"],
                    "team": team_label,
                    "game": f"{eg['away_name']} @ {eg['home_name']}",
                    "game_time": eg["date"],
                    "game_status": eg["status"],
                    "direction": direction,
                    "kalshi_mid": kalshi_mid,
                    "kalshi_bid": yes_bid,
                    "kalshi_ask": yes_ask,
                    "fair_value": round(fair_cents, 1),
                    "edge_cents": round(abs(edge), 1),
                    "edge_pct": round(abs(edge) / 100.0, 4),
                    "sportsbook_odds": eg["odds"],
                    "entry_price": entry_price,
                    "spread": spread,
                    "volume": volume,
                }
                signals.append(signal)
                state["signals_seen"] += 1
    
    return signals

# ============================================================================
# PAPER TRADING EXECUTION
# ============================================================================

def execute_paper_trades(signals, state):
    """
    Execute paper trades for valid signals.
    Respects position limits and exposure caps.
    """
    new_positions = []
    
    # Calculate current total exposure
    current_exposure = sum(p["cost"] for p in state["positions"])
    
    for sig in signals:
        # Check if we already have a position in this event
        existing = [p for p in state["positions"] if p["event_ticker"] == sig["event_ticker"]]
        if existing:
            logger.info(f"  Already have position in {sig['event_ticker']}, skip")
            continue
        
        # Check exposure limits
        if current_exposure >= MAX_TOTAL_EXPOSURE:
            logger.warning(f"  Max exposure ${MAX_TOTAL_EXPOSURE} reached, skip")
            break
        
        # Calculate position size via Kelly
        fair_prob = sig["fair_value"] / 100.0
        entry = sig["entry_price"]
        
        if sig["direction"] == "BUY_YES":
            size = kelly_size(fair_prob, entry, state["bankroll"])
        else:
            # For BUY_NO: our edge is on the NO side
            no_fair = 1.0 - fair_prob
            size = kelly_size(no_fair, entry, state["bankroll"])
        
        if size < 1.0:
            logger.info(f"  {sig['ticker']}: Kelly size ${size:.2f} too small, skip")
            continue
        
        # Number of contracts (each costs entry_price cents)
        contracts = max(1, int(size / (entry / 100.0)))
        cost = contracts * (entry / 100.0)
        
        # Don't exceed remaining exposure
        remaining = MAX_TOTAL_EXPOSURE - current_exposure
        if cost > remaining:
            contracts = max(1, int(remaining / (entry / 100.0)))
            cost = contracts * (entry / 100.0)
        
        # Cap per game
        if cost > MAX_POSITION_PER_GAME:
            contracts = max(1, int(MAX_POSITION_PER_GAME / (entry / 100.0)))
            cost = contracts * (entry / 100.0)
        
        # Build position record
        now = datetime.now(timezone.utc).isoformat()
        position = {
            "id": f"{sig['ticker']}-{int(time.time())}",
            "ticker": sig["ticker"],
            "event_ticker": sig["event_ticker"],
            "direction": sig["direction"],
            "team": sig["team"],
            "game": sig["game"],
            "game_time": sig["game_time"],
            "contracts": contracts,
            "entry_price": entry,
            "cost": round(cost, 2),
            "fair_value": sig["fair_value"],
            "edge_cents": sig["edge_cents"],
            "edge_pct": sig["edge_pct"],
            "sportsbook_odds": sig["sportsbook_odds"],
            "kalshi_mid_at_entry": sig["kalshi_mid"],
            "opened_at": now,
            "status": "open",
        }
        
        state["positions"].append(position)
        state["trades_taken"] += 1
        current_exposure += cost
        new_positions.append(position)
        
        logger.info(
            f"  📊 PAPER TRADE: {sig['direction']} {contracts}x {sig['ticker']} @ {entry}¢ "
            f"(cost ${cost:.2f}) — edge {sig['edge_cents']:.1f}¢ "
            f"(fair={sig['fair_value']:.1f}¢ vs kalshi={sig['kalshi_mid']:.1f}¢) "
            f"— {sig['game']}"
        )
    
    return new_positions

# ============================================================================
# SETTLEMENT CHECK
# ============================================================================

def check_settlements(state):
    """
    Check if any open positions have settled.
    Uses Kalshi API to check market status.
    """
    settled_count = 0
    
    for pos in state["positions"]:
        if pos["status"] != "open":
            continue
        
        try:
            r = requests.get(
                f"{KALSHI_BASE}/markets/{pos['ticker']}",
                timeout=10,
            )
            if r.status_code != 200:
                continue
                
            market = r.json().get("market", {})
            result = market.get("result", "")
            mkt_status = market.get("status", "")
            
            if result and result in ("yes", "no"):
                # Market settled
                if pos["direction"] == "BUY_YES":
                    won = (result == "yes")
                else:
                    won = (result == "no")
                
                if won:
                    # Payout = contracts * $1 - cost
                    payout = pos["contracts"] * 1.0
                    fee = payout * 0.07  # ~7% fee on winnings
                    profit = payout - pos["cost"] - fee
                    state["wins"] += 1
                else:
                    profit = -pos["cost"]
                    state["losses"] += 1
                
                pos["status"] = "settled"
                pos["result"] = result
                pos["won"] = won
                pos["profit"] = round(profit, 2)
                pos["settled_at"] = datetime.now(timezone.utc).isoformat()
                
                state["bankroll"] += profit
                state["total_pnl"] += profit
                
                # Move to settled history
                state["settled"].append(pos)
                settled_count += 1
                
                emoji = "✅" if won else "❌"
                logger.info(
                    f"  {emoji} SETTLED: {pos['ticker']} — result={result} "
                    f"{'WON' if won else 'LOST'} — P/L: ${profit:+.2f} "
                    f"— Bankroll: ${state['bankroll']:.2f}"
                )
            
            elif mkt_status == "closed" and not result:
                # Market closed but no result yet, keep waiting
                pass
                
        except Exception as e:
            logger.debug(f"Settlement check failed for {pos['ticker']}: {e}")
    
    # Remove settled positions from active list
    state["positions"] = [p for p in state["positions"] if p["status"] == "open"]
    
    if settled_count > 0:
        logger.info(f"Settled {settled_count} positions — Total P/L: ${state['total_pnl']:+.2f}")
    
    return settled_count

# ============================================================================
# DATE HELPERS
# ============================================================================

def get_scan_dates():
    """
    Get the dates we should scan for NBA games.
    Returns list of YYYYMMDD strings.
    ESPN uses ET dates but games are listed by their local start.
    We check today and tomorrow to catch all upcoming games.
    """
    now = datetime.now(timezone.utc)
    dates = set()
    
    # Check today and tomorrow (UTC)
    for delta in range(3):
        d = now + timedelta(days=delta)
        dates.add(d.strftime("%Y%m%d"))
    
    # Also check yesterday for late-night games that might still be running
    yesterday = now - timedelta(days=1)
    dates.add(yesterday.strftime("%Y%m%d"))
    
    return sorted(dates)

def is_nba_hours():
    """Check if current time is during NBA game hours (UTC)."""
    hour = datetime.now(timezone.utc).hour
    # NBA hours: 17:00 - 05:00 UTC (roughly noon-midnight ET)
    if NBA_START_HOUR_UTC <= hour or hour < NBA_END_HOUR_UTC:
        return True
    return False

# ============================================================================
# MAIN SCAN CYCLE
# ============================================================================

def run_scan(state):
    """Execute one full scan cycle."""
    now = datetime.now(timezone.utc)
    logger.info(f"{'='*60}")
    logger.info(f"SCAN CYCLE — {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info(f"Bankroll: ${state['bankroll']:.2f} | P/L: ${state['total_pnl']:+.2f} | "
                f"Open: {len(state['positions'])} | W/L: {state['wins']}/{state['losses']}")
    logger.info(f"{'='*60}")
    
    # 1. Check settlements for existing positions
    if state["positions"]:
        logger.info(f"\n--- Checking {len(state['positions'])} open positions ---")
        check_settlements(state)
    
    # 2. Fetch Kalshi NBA markets
    logger.info("\n--- Fetching Kalshi NBA markets ---")
    kalshi_raw = fetch_kalshi_nba_markets()
    if not kalshi_raw:
        logger.warning("No Kalshi markets found")
        state["last_scan"] = now.isoformat()
        save_state(state)
        return
    
    kalshi_games = parse_kalshi_markets(kalshi_raw)
    logger.info(f"Found {len(kalshi_games)} Kalshi game events")
    
    # 3. Fetch ESPN games for relevant dates
    logger.info("\n--- Fetching ESPN/DraftKings odds ---")
    all_espn_games = []
    for date_str in get_scan_dates():
        espn_games = fetch_espn_games(date_str)
        all_espn_games.extend(espn_games)
        if espn_games:
            logger.info(f"  {date_str}: {len(espn_games)} games ({sum(1 for g in espn_games if g['odds'])} with odds)")
    
    # Deduplicate by espn_id
    seen_ids = set()
    unique_espn = []
    for g in all_espn_games:
        if g["espn_id"] not in seen_ids:
            seen_ids.add(g["espn_id"])
            unique_espn.append(g)
    
    # 4. Match games
    logger.info("\n--- Matching Kalshi ↔ ESPN games ---")
    matched = match_games(kalshi_games, unique_espn)
    logger.info(f"Matched {len(matched)} games")
    
    # 5. Detect signals
    logger.info(f"\n--- Detecting signals (min edge: {MIN_EDGE_CENTS}c) ---")
    signals = detect_signals(matched, state)
    
    if signals:
        logger.info(f"\n🎯 Found {len(signals)} signal(s):")
        for sig in signals:
            logger.info(
                f"  → {sig['direction']} {sig['ticker']} — "
                f"Kalshi: {sig['kalshi_mid']:.1f}¢ (bid {sig['kalshi_bid']}¢ / ask {sig['kalshi_ask']}¢) "
                f"vs Fair: {sig['fair_value']:.1f}¢ — "
                f"Edge: {sig['edge_cents']:.1f}¢ ({sig['edge_pct']*100:.1f}%) — "
                f"{sig['game']} ({sig['game_status']})"
            )
        
        # 6. Execute paper trades
        logger.info("\n--- Executing paper trades ---")
        new_trades = execute_paper_trades(signals, state)
        if new_trades:
            logger.info(f"Opened {len(new_trades)} new position(s)")
        else:
            logger.info("No new positions opened (limits/duplicates)")
    else:
        logger.info("No signals found this cycle")
    
    # Log all matched games for reference
    logger.info("\n--- Game Overview ---")
    for match in matched:
        eg = match["espn"]
        kg = match["kalshi"]
        fair = calculate_fair_value(eg)
        
        if not fair:
            logger.info(f"  {eg['away_name']} @ {eg['home_name']} — NO ODDS")
            continue
        
        home_fair, away_fair = fair
        
        # Find kalshi prices
        kalshi_prices = []
        for ticker, mkt in kg["markets"].items():
            mid = (mkt["yes_bid"] + mkt["yes_ask"]) / 2.0
            kalshi_prices.append(f"{mkt['yes_team']}={mid:.0f}¢")
        
        odds = eg["odds"]
        logger.info(
            f"  {eg['away_name']} @ {eg['home_name']} "
            f"[{eg['status']}] — "
            f"DK: away {odds['away_ml']:+d} home {odds['home_ml']:+d} — "
            f"Fair: away={away_fair*100:.1f}¢ home={home_fair*100:.1f}¢ — "
            f"Kalshi: {', '.join(kalshi_prices)}"
        )
    
    # Update state
    state["last_scan"] = now.isoformat()
    
    # Daily stats tracking
    today = now.strftime("%Y-%m-%d")
    if today not in state["daily_stats"]:
        state["daily_stats"][today] = {
            "scans": 0,
            "signals": 0,
            "trades": 0,
        }
    state["daily_stats"][today]["scans"] += 1
    state["daily_stats"][today]["signals"] += len(signals)
    state["daily_stats"][today]["trades"] += len([s for s in signals if s])  # rough
    
    save_state(state)
    
    logger.info(f"\nScan complete. Next scan in {'30 min' if is_nba_hours() else '2 hours'}")

# ============================================================================
# MAIN LOOP
# ============================================================================

def main():
    logger.info("=" * 60)
    logger.info("NBA Sharp Line Detection — Paper Trader")
    logger.info("=" * 60)
    logger.info(f"Config: min_edge={MIN_EDGE_CENTS}¢, max_per_game=${MAX_POSITION_PER_GAME}, "
                f"max_exposure=${MAX_TOTAL_EXPOSURE}, kelly={KELLY_FRACTION}")
    logger.info(f"State file: {STATE_FILE}")
    logger.info(f"Log file: {LOG_FILE}")
    
    state = load_state()
    logger.info(f"Loaded state: bankroll=${state['bankroll']:.2f}, "
                f"open_positions={len(state['positions'])}, "
                f"total_pnl=${state['total_pnl']:+.2f}")
    
    scan_count = 0
    
    while not shutdown_requested:
        try:
            run_scan(state)
            scan_count += 1
        except Exception as e:
            logger.error(f"Scan error: {e}")
            logger.error(traceback.format_exc())
        
        # Determine sleep interval
        interval = SCAN_INTERVAL_ACTIVE if is_nba_hours() else SCAN_INTERVAL_INACTIVE
        logger.info(f"Sleeping {interval}s until next scan... (NBA hours: {is_nba_hours()})")
        
        # Sleep in small chunks to check for shutdown
        sleep_end = time.time() + interval
        while time.time() < sleep_end and not shutdown_requested:
            time.sleep(min(10, sleep_end - time.time()))
    
    # Graceful shutdown
    logger.info("Shutdown: saving final state...")
    save_state(state)
    logger.info(f"Final state: bankroll=${state['bankroll']:.2f}, pnl=${state['total_pnl']:+.2f}, "
                f"open={len(state['positions'])}, W/L={state['wins']}/{state['losses']}")
    logger.info("NBA Paper Trader stopped.")

if __name__ == "__main__":
    main()
