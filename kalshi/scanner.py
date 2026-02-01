exec(open('/tmp/sandbox_bootstrap.py').read())

import requests
import json
import sys
import os
from datetime import datetime, timezone, timedelta

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
SKIP_CATEGORIES = {"Sports", "Entertainment"}
TARGET_CATEGORIES = {"Politics", "Economics", "Elections", "World", "Government"}

def api_get(endpoint, params=None):
    """Simple API call with no artificial delay"""
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=15)
        if resp.status_code == 429:
            import time; time.sleep(5)
            resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ⚠️ API error: {e}")
        return None

def fetch_all_markets(cursor=None, limit=200):
    """Fetch markets in bulk with pagination"""
    all_markets = []
    while True:
        params = {"limit": limit, "status": "open"}
        if cursor:
            params["cursor"] = cursor
        data = api_get("/markets", params)
        if not data:
            break
        markets = data.get("markets", [])
        all_markets.extend(markets)
        cursor = data.get("cursor", "")
        if not cursor or len(markets) < limit:
            break
    return all_markets

def fetch_events_map():
    """Build event_ticker -> category/title map"""
    emap = {}
    cursor = None
    while True:
        params = {"limit": 200, "status": "open"}
        if cursor:
            params["cursor"] = cursor
        data = api_get("/events", params)
        if not data:
            break
        for e in data.get("events", []):
            emap[e["event_ticker"]] = {
                "category": e.get("category", ""),
                "title": e.get("title", ""),
                "sub_title": e.get("sub_title", ""),
            }
        cursor = data.get("cursor", "")
        if not cursor or len(data.get("events", [])) < 200:
            break
    return emap

def analyze_markets(markets, events_map, max_days=60):
    """Analyze markets for junk bond, momentum, and mispricing opportunities"""
    now = datetime.now(timezone.utc)
    
    junk_bonds = []
    hot_movers = []
    mispricings = []
    
    for m in markets:
        ticker = m.get("ticker", "")
        event_ticker = m.get("event_ticker", "")
        
        # Skip sports/entertainment via event category
        ev = events_map.get(event_ticker, {})
        cat = ev.get("category", "")
        if cat in SKIP_CATEGORIES:
            continue
        # Skip multi-game sports parlays
        if "MULTIGAME" in ticker.upper() or "SPORT" in ticker.upper():
            continue
            
        # Parse close time
        close_str = m.get("close_time", "")
        if not close_str:
            continue
        try:
            close = datetime.fromisoformat(close_str.replace("Z", "+00:00"))
        except:
            continue
        
        days = (close - now).days
        if days <= 0 or days > max_days:
            continue
        
        price = m.get("last_price", 50)
        prev_price = m.get("previous_price", price)
        vol24h = m.get("volume_24h", 0)
        vol_total = m.get("volume", 0)
        yes_bid = m.get("yes_bid", 0)
        yes_ask = m.get("yes_ask", 0)
        no_bid = m.get("no_bid", 0) 
        no_ask = m.get("no_ask", 0)
        spread = (yes_ask - yes_bid) if yes_ask and yes_bid else 99
        title = m.get("title", "")
        sub = m.get("yes_sub_title", "") or m.get("no_sub_title", "")
        
        info = {
            "ticker": ticker,
            "event": event_ticker,
            "category": cat,
            "title": title,
            "sub": sub,
            "price": price,
            "prev_price": prev_price,
            "days": days,
            "close": close_str[:10],
            "vol24h": vol24h,
            "vol_total": vol_total,
            "spread": spread,
            "yes_bid": yes_bid,
            "yes_ask": yes_ask,
        }
        
        # 🎯 JUNK BOND: high probability, reasonable spread
        if (price >= 88 or price <= 12) and spread <= 15:
            side = "YES" if price >= 88 else "NO"
            cost = price if price >= 88 else (100 - price)
            profit = 100 - cost
            ret_pct = (profit / cost) * 100 if cost > 0 else 0
            ann_ret = (ret_pct / max(days, 1)) * 365
            info.update({
                "side": side,
                "cost": cost,
                "profit": profit, 
                "ret_pct": ret_pct,
                "ann_ret": ann_ret,
            })
            junk_bonds.append(info)
        
        # 🔥 HOT MOVER: significant price change + volume
        price_change = abs(price - prev_price)
        if price_change >= 5 and vol24h >= 20:
            info["price_change"] = price_change
            info["direction"] = "↑" if price > prev_price else "↓"
            hot_movers.append(info)
        
        # ⚠️ MISPRICING: wide spread with decent volume suggests uncertainty
        if spread >= 5 and spread <= 20 and vol24h >= 10 and 20 <= price <= 80:
            info["spread_pct"] = (spread / price) * 100
            mispricings.append(info)
    
    # Sort
    junk_bonds.sort(key=lambda x: -x.get("ann_ret", 0))
    hot_movers.sort(key=lambda x: (-x.get("price_change", 0), -x.get("vol24h", 0)))
    mispricings.sort(key=lambda x: (-x.get("spread_pct", 0), -x.get("vol24h", 0)))
    
    return junk_bonds, hot_movers, mispricings

def format_report(junk_bonds, hot_movers, mispricings):
    """Format a clean report"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"📊 KALSHI SCANNER REPORT — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 60)
    
    # Junk Bonds
    lines.append(f"\n🎯 JUNK BOND OPPORTUNITIES ({len(junk_bonds)} found)")
    lines.append("-" * 50)
    if not junk_bonds:
        lines.append("  None found matching criteria")
    for jb in junk_bonds[:20]:
        lines.append(f"  {jb['side']}@{jb['cost']}¢ → +{jb['ret_pct']:.1f}% in {jb['days']}d ({jb['ann_ret']:.0f}% ann)")
        lines.append(f"    spread:{jb['spread']} | vol24h:{jb['vol24h']} | {jb['category']}")
        lines.append(f"    {jb['title']} — {jb['sub']}")
        lines.append(f"    [{jb['ticker']}]")
        lines.append("")
    
    # Hot Movers
    lines.append(f"\n🔥 HOT MOVERS ({len(hot_movers)} found)")
    lines.append("-" * 50)
    if not hot_movers:
        lines.append("  No significant movers")
    for hm in hot_movers[:15]:
        lines.append(f"  {hm.get('direction','')} {hm['prev_price']}¢→{hm['price']}¢ (Δ{hm.get('price_change',0)}¢) | vol24h:{hm['vol24h']} | {hm['days']}d")
        lines.append(f"    {hm['title']} — {hm['sub']}")
        lines.append(f"    [{hm['ticker']}]")
        lines.append("")
    
    # Mispricings
    lines.append(f"\n⚠️ POTENTIAL MISPRICINGS ({len(mispricings)} found)")
    lines.append("-" * 50)
    if not mispricings:
        lines.append("  None detected")
    for mp in mispricings[:10]:
        lines.append(f"  {mp['price']}¢ | spread:{mp['spread']} ({mp.get('spread_pct',0):.0f}%) | vol24h:{mp['vol24h']} | {mp['days']}d")
        lines.append(f"    bid:{mp['yes_bid']}¢ ask:{mp['yes_ask']}¢ | {mp['category']}")
        lines.append(f"    {mp['title']} — {mp['sub']}")
        lines.append(f"    [{mp['ticker']}]")
        lines.append("")
    
    return "\n".join(lines)

def main():
    max_days = 60
    if "--max-days" in sys.argv:
        idx = sys.argv.index("--max-days")
        if idx + 1 < len(sys.argv):
            max_days = int(sys.argv[idx + 1])
    
    json_out = "--json" in sys.argv
    
    print("📡 Fetching events...")
    events_map = fetch_events_map()
    print(f"   {len(events_map)} events loaded")
    
    print("📡 Fetching markets (bulk)...")
    all_markets = fetch_all_markets()
    print(f"   {len(all_markets)} markets loaded")
    
    print("🔍 Analyzing...")
    jb, hm, mp = analyze_markets(all_markets, events_map, max_days)
    
    if json_out:
        result = {"junk_bonds": jb, "hot_movers": hm, "mispricings": mp,
                  "timestamp": datetime.now(timezone.utc).isoformat(),
                  "markets_scanned": len(all_markets)}
        print(json.dumps(result, indent=2, default=str))
    else:
        print(format_report(jb, hm, mp))
    
    # Save state
    state = {
        "last_scan": datetime.now(timezone.utc).isoformat(),
        "markets_scanned": len(all_markets),
        "junk_bonds_found": len(jb),
        "hot_movers_found": len(hm),
        "mispricings_found": len(mp),
    }
    state_path = os.path.join(os.path.dirname(__file__) or ".", "state.json")
    try:
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
    except:
        pass

if __name__ == "__main__":
    main()
