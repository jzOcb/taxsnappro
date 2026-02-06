#!/usr/bin/env python3
"""
Cross-Platform Arb Scanner — Polymarket ↔ Kalshi price gap monitor.
Scans matching events, logs price divergences, collects data overnight.

Runs continuously, polls every 60 seconds, saves all data for analysis.
"""

import sys
import json
import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR = BASE_DIR / "research" / "arb_scanner"
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "cross_platform_scanner.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("arb_scanner")

# ============================================================================
# POLYMARKET DATA
# ============================================================================

def fetch_pm_events(tag=None, limit=50):
    """Fetch active Polymarket events."""
    params = {"active": "true", "closed": "false", "limit": limit,
              "order": "volume24hr", "ascending": "false"}
    if tag:
        params["tag"] = tag
    try:
        r = requests.get("https://gamma-api.polymarket.com/events", params=params, timeout=15)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        logger.warning(f"PM events error: {e}")
        return []

def fetch_pm_markets(event_id=None, slug=None):
    """Fetch Polymarket markets for an event."""
    params = {"limit": 50}
    if event_id:
        params["event_id"] = event_id
    if slug:
        params["slug"] = slug
    try:
        r = requests.get("https://gamma-api.polymarket.com/markets", params=params, timeout=15)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        logger.warning(f"PM markets error: {e}")
        return []

# ============================================================================
# KALSHI DATA
# ============================================================================

def fetch_kalshi_markets(series_ticker, status="open", limit=20):
    """Fetch Kalshi markets for a series."""
    try:
        r = requests.get(
            "https://api.elections.kalshi.com/trade-api/v2/markets",
            params={"series_ticker": series_ticker, "status": status, "limit": limit},
            headers={"accept": "application/json"},
            timeout=15,
        )
        return r.json().get("markets", []) if r.status_code == 200 else []
    except Exception as e:
        logger.warning(f"Kalshi {series_ticker} error: {e}")
        return []

# ============================================================================
# MATCHING ENGINE
# ============================================================================

# Known cross-platform matches (Kalshi series → PM search terms)
KNOWN_MATCHES = {
    # Crypto daily
    "BTC_DAILY": {
        "kalshi_series": "KXBTCD",
        "pm_search": "bitcoin",
        "pm_tag": "crypto",
        "match_type": "price_bracket",
        "note": "PM resolves noon ET, Kalshi 5pm ET — NOT same event but correlated",
    },
    "ETH_DAILY": {
        "kalshi_series": "KXETHD",
        "pm_search": "ethereum",
        "pm_tag": "crypto",
        "match_type": "price_bracket",
        "note": "PM resolves noon ET, Kalshi 5pm ET",
    },
    # Fed rate
    "FED_RATE": {
        "kalshi_series": "KXFED",
        "pm_search": "fed",
        "pm_tag": None,
        "match_type": "event",
        "note": "Both resolve on FOMC announcement — TRUE arb candidate",
    },
    # Trump mention
    "TRUMP_SAY": {
        "kalshi_series": None,  # Kalshi mention markets are event-driven
        "pm_search": "trump say",
        "pm_tag": None,
        "match_type": "mention",
        "note": "PM has weekly 'What will Trump say' events",
    },
}


def scan_crypto_prices():
    """Compare BTC/ETH prices between Kalshi and Polymarket."""
    results = []
    
    for asset in ["BTC", "ETH"]:
        series = "KXBTCD" if asset == "BTC" else "KXETHD"
        
        # Kalshi side
        k_markets = fetch_kalshi_markets(series)
        if not k_markets:
            continue
        
        # Find the ATM (closest to 50¢) market
        k_atm = min(k_markets, key=lambda m: abs(m.get("yes_bid", 0) - 50))
        k_price = k_atm.get("yes_bid", 0)
        k_ask = k_atm.get("yes_ask", 0)
        k_ticker = k_atm.get("ticker", "")
        k_title = k_atm.get("title", "")[:60]
        
        # Polymarket side
        pm_events = fetch_pm_events()
        pm_match = None
        for e in pm_events:
            title_lower = e.get("title", "").lower()
            if asset.lower() in title_lower and "daily" in title_lower:
                pm_match = e
                break
            if asset.lower() in title_lower and "above" in title_lower:
                pm_match = e
                break
        
        if pm_match:
            pm_markets = pm_match.get("markets", [])
            if not pm_markets:
                # Try fetching markets separately
                pm_id = pm_match.get("id")
                if pm_id:
                    pm_markets = fetch_pm_markets(event_id=pm_id)
            
            # Find highest volume PM market
            if pm_markets:
                pm_top = max(pm_markets, key=lambda m: float(m.get("volume", 0) or 0))
                pm_prices = json.loads(pm_top.get("outcomePrices", "[]"))
                pm_yes = float(pm_prices[0]) * 100 if pm_prices else 0
                pm_title = pm_top.get("question", pm_top.get("groupItemTitle", ""))[:60]
                pm_vol = float(pm_top.get("volume", 0) or 0)
                
                gap = abs(k_price - pm_yes)
                
                result = {
                    "asset": asset,
                    "kalshi_ticker": k_ticker,
                    "kalshi_title": k_title,
                    "kalshi_bid": k_price,
                    "kalshi_ask": k_ask,
                    "pm_title": pm_title,
                    "pm_yes": round(pm_yes, 1),
                    "pm_volume": round(pm_vol),
                    "price_gap": round(gap, 1),
                    "direction": "K>PM" if k_price > pm_yes else "PM>K",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                results.append(result)
                
                emoji = "🔴" if gap > 5 else ("🟡" if gap > 3 else "🟢")
                logger.info(
                    f"{emoji} {asset}: Kalshi={k_price}¢ PM={pm_yes:.0f}¢ "
                    f"gap={gap:.0f}¢ ({result['direction']}) | "
                    f"K:{k_title} | PM:{pm_title}"
                )
    
    return results


def scan_fed_rate():
    """Compare Fed rate expectations between platforms."""
    results = []
    
    # Kalshi Fed markets
    k_markets = fetch_kalshi_markets("KXFED", limit=30)
    
    # Polymarket Fed
    pm_events = fetch_pm_events()
    pm_fed = [e for e in pm_events if "fed" in e.get("title", "").lower() 
              and ("rate" in e.get("title", "").lower() or "decision" in e.get("title", "").lower())]
    
    if k_markets and pm_fed:
        logger.info(f"Fed: {len(k_markets)} Kalshi markets, {len(pm_fed)} PM events")
        for e in pm_fed[:3]:
            logger.info(f"  PM: {e.get('title', '')[:70]} | vol24=${float(e.get('volume24hr', 0)):,.0f}")
    
    return results


def scan_sports():
    """Compare sports odds between Kalshi and Polymarket."""
    results = []
    
    # PM sports (today's games)
    pm_sports = fetch_pm_events(tag="sports")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Filter to today/tomorrow
    upcoming = []
    for e in pm_sports[:30]:
        end = e.get("endDate", "")[:10]
        vol24 = float(e.get("volume24hr", 0) or 0)
        if vol24 > 10000:  # Only liquid events
            upcoming.append(e)
    
    if upcoming:
        logger.info(f"Sports: {len(upcoming)} liquid PM events")
        for e in upcoming[:5]:
            logger.info(
                f"  {e.get('title', '')[:60]} | "
                f"vol24=${float(e.get('volume24hr', 0)):,.0f}"
            )
    
    # TODO: Match with Kalshi sports markets (KXNBA, etc.)
    
    return results


# ============================================================================
# MAIN LOOP
# ============================================================================

def main():
    duration_min = int(sys.argv[1]) if len(sys.argv) > 1 else 480
    end_time = time.time() + duration_min * 60
    
    logger.info("🔍 ===== CROSS-PLATFORM ARB SCANNER STARTING =====")
    logger.info(f"Duration: {duration_min} min | Poll interval: 60s")
    
    all_snapshots = []
    cycle = 0
    
    while time.time() < end_time:
        cycle += 1
        try:
            logger.info(f"\n--- Scan cycle {cycle} ---")
            
            # Crypto price comparison
            crypto = scan_crypto_prices()
            
            # Fed rate comparison
            fed = scan_fed_rate()
            
            # Sports comparison
            sports = scan_sports()
            
            # Save snapshot
            snapshot = {
                "cycle": cycle,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "crypto": crypto,
                "fed": fed,
                "sports": sports,
            }
            all_snapshots.append(snapshot)
            
            # Save to disk every 10 cycles
            if cycle % 10 == 0:
                outfile = DATA_DIR / f"arb_scan_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
                with open(outfile, "w") as f:
                    json.dump(all_snapshots, f, indent=2, default=str)
                logger.info(f"💾 Saved {len(all_snapshots)} snapshots to {outfile.name}")
            
            # Summary
            if crypto:
                max_gap = max(c["price_gap"] for c in crypto)
                logger.info(f"📊 Max crypto gap: {max_gap:.0f}¢")
            
            time.sleep(60)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Scan error: {e}")
            time.sleep(30)
    
    # Final save
    outfile = DATA_DIR / f"arb_scan_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    with open(outfile, "w") as f:
        json.dump(all_snapshots, f, indent=2, default=str)
    
    logger.info(f"\n🏁 Scanner stopped. {len(all_snapshots)} total snapshots saved.")


if __name__ == "__main__":
    main()
